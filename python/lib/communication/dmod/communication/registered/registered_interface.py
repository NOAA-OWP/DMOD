import logging
import typing
import abc
import logging
import json
import inspect
import functools
import asyncio

import websockets
from websockets import WebSocketServerProtocol

from dmod.core import decorators

from ..websocket_interface import WebSocketInterface
from ..websocket_interface import AbstractInitRequest
from ..message import Message
from ..message import Response
from ..message import InvalidMessageResponse
from ..message import InvalidMessage
from ..message import ErrorResponse
from ..message import MessageEventType
from ..unsupported_message import UnsupportedMessageTypeResponse

from .dynamic_function import DynamicFunctionMixin
from .exceptions import RegistrationError
from .aliases import *


class RegisteredWebSocketInterface(WebSocketInterface, DynamicFunctionMixin, abc.ABC):
    """
    A websocket interface implementation that routes logic through registered initializers, consumers, and producers

    Initializers, consumers, producers, and handlers are usually defined via decorator
    """
    @classmethod
    def get_parseable_request_types(cls) -> typing.List[typing.Type[AbstractInitRequest]]:
        return list()

    def __init__(
        self,
        listen_host: str = '127.0.0.1',
        port: typing.Union[bytes, str, int] = 3012,
        ssl_dir: str = None,
        cert_pem: str = None,
        priv_key_pem: str = None,
        use_ssl: bool = True,
        message_handlers: typing.Mapping[typing.Type[AbstractInitRequest], AbstractRequestHandler] = None,
        *args,
        **kwargs
    ):
        super().__init__(
            listen_host=listen_host,
            port=port,
            ssl_dir=ssl_dir,
            cert_pem=cert_pem,
            priv_key_pem=priv_key_pem,
            use_ssl=use_ssl,
            *args,
            **kwargs
        )

        self._event_handlers: typing.Dict[typing.Type[AbstractInitRequest], AbstractRequestHandler] = dict()
        """A mapping between a type of message and the function that is supposed to consume it"""

        if message_handlers:
            for message_type, handler in message_handlers:
                self.register_event_handler(message_type, handler)

        # Run all recognized initialization functions
        self._initialize(
            listen_host=listen_host,
            port=port,
            ssl_dir=ssl_dir,
            cert_pem=cert_pem,
            priv_key_pem=priv_key_pem,
            *args,
            **kwargs
        )
        self._assign_handlers()

    def _initialize(self, *args, **kwargs):
        """
        Calls all added initialization functions and attaches all consumers and producers
        """
        for initialization_function in self._get_initialization_functions():
            initialization_function(*args, **kwargs)

    def _get_initialization_functions(self) -> typing.Sequence[VARIABLE_CALLABLE]:
        """
        Generates a list of all member functions that need to be called at the end of the abstract class construction

        Each function must handle `*args, **kwargs`, and the first arguments handled will be the arguments passed into
        `RegistedWebSocketInterface` constructor.

        Returns:
            All member functions that need to be called at the end of the abstract class construction
        """

        initialization_functions = self._get_dynamic_functions(decorators.INITIALIZER_ATTRIBUTE)
        initializers: typing.List[VARIABLE_CALLABLE] = list()

        for initializer_name, initializer in initialization_functions.items():
            if inspect.iscoroutinefunction(initializer):
                raise RegistrationError(
                    f"{initializer_name} cannot be called for initialization; "
                    f"only synchronous functions are allowed here."
                )
            initializers.append(initializer)

        return initializers

    async def _get_additional_arguments(self, socket: WebSocketServerProtocol) -> typing.Dict[str, typing.Any]:
        """
        Generates a dictionary of all items that should be sent to handlers as keyword arguments, such as session

        Returns:
            A dictionary of additional arguments that should be sent to handlers
        """
        additional_parameter_functions: typing.Dict[str, ADDITIONAL_PARAMETER_PROVIDER] = self._get_dynamic_functions(
            decorators.ADDITIONAL_PARAMETER_ATTRIBUTE
        )

        additional_parameters: typing.Dict[str, typing.Any] = dict()

        # Gather all parameters from identified functions
        for provider_name, function in additional_parameter_functions.items():
            # If the calling function returned an awaitable, go ahead and wait on it
            if inspect.iscoroutinefunction(function):
                generated_parameters = await function(self, socket)
            else:
                generated_parameters = function(self, socket)

            if generated_parameters is None:
                continue

            # If the called function does NOT return a mapping, but does return something that may be considered
            # a key-value pair, use that to create the mapping
            if not isinstance(generated_parameters, typing.Mapping) \
                    and isinstance(generated_parameters, (tuple, list)) \
                    and len(generated_parameters) >= 2:
                generated_parameters = {str(generated_parameters[0]): generated_parameters[1]}
            elif not isinstance(generated_parameters, typing.Mapping):
                raise ValueError(
                    f"[{self.__class__.__name__}] The '{provider_name}' function did not return a dictionary or "
                    f"key value pair; generated parameters may not be used for additional parameters for handled events"
                )

            for parameter_name, parameter_value in generated_parameters.items():
                # Just in case a function returns nested awaitables, keep awaiting until the full value has been
                # returned
                while inspect.isawaitable(parameter_value):
                    parameter_value = await parameter_value

                additional_parameters[parameter_name] = parameter_value

        return additional_parameters

    def _get_undecorated_event_handlers(self) -> typing.Dict[typing.Type[AbstractInitRequest], AbstractRequestHandler]:
        """
        Get event handlers not defined via decorators

        Provides nothing if not overridden by a subclass

        Returns:
            A dictionary of message event types to handler functions that aren't provided via decorators
        """
        return dict()

    def register_event_handler(self, message_type: typing.Type[AbstractInitRequest], handler: AbstractRequestHandler):
        """
        Add a type of Message to handle

        Args:
            message_type: The type of message to handle
            handler: The function that will operate on that type of message
        """
        errors: typing.List[str] = list()
        if not message_type:
            errors.append("A valid message type was not supplied")
        elif not isinstance(message_type, type(AbstractInitRequest)):
            errors.append(f"'{message_type}' is not a valid message type.")

        if not handler:
            errors.append("A valid message handler was not provided")
        elif not isinstance(handler, AbstractRequestHandler):
            errors.append(
                f"'{handler.__class__.__name__}' is not a valid type of handler. "
                f"All handlers must inherit from AbstractRequestHandler"
            )

        if errors:
            message = "An event handler could not be registered: "
            message += " and ".join(errors)
            raise RegistrationError(message)

        self._event_handlers[message_type] = handler

    def remove_event_handler(self, message_type: typing.Type[AbstractInitRequest]):
        """
        Remove a handler from the event handlers

        Args:
            message_type: The type of message to no longer handle
        """
        if message_type in self._event_handlers:
            del self._event_handlers[message_type]

    def _assign_handlers(self):
        """
        Assign request handlers to their respective events
        """
        # Get every function that has been flagged as producing a handler
        handlers = self._get_dynamic_functions(decorators.SOCKET_HANDLER_ATTRIBUTE, decorators.MESSAGE_TYPE_ATTRIBUTE)

        for handler_name, handler_generator in handlers.items():
            # Found functions must be asynchronous in order to operate on the required websockets
            if isinstance(handler_generator, AbstractRequestHandler):
                handler = handler_generator
            elif inspect.iscoroutinefunction(handler_generator):
                handler = asyncio.run(handler_generator())
            elif inspect.ismethod(handler_generator):
                handler = handler_generator()
            else:
                raise RegistrationError(
                    f"[{self.__class__.__name__}] Cannot assign handlers; "
                    f"handler type for '{handler_name}' of `{type(handler_generator)}` is not recognized"
                )

            # The assignment for `handlers` ensures that they have an attribute designated by
            # `decorators.EVENT_TYPE_ATTRIBUTE`
            message_type: typing.Type[AbstractInitRequest] = getattr(handler_generator, decorators.MESSAGE_TYPE_ATTRIBUTE)

            # We don't want handlers to accidentily overwrite one another here, so we throw an error if a conflict is
            # detected; these can't override one another since there's no guaranteed order with which functions will be
            # assigned
            if message_type in self._event_handlers:
                raise RegistrationError(
                    f"[{self.__class__.__name__}] The event handler named {handler_name} cannot be added; there is "
                    f"already an event handler for '{message_type.__class__.__name__}' messages"
                )

            self._event_handlers[message_type] = handler

        # Event handlers may override one another here because of how explicit `_get_undecorated_event_handlers` is and
        # since order may be relatively consistent
        self._event_handlers.update(self._get_undecorated_event_handlers())

    async def handle_invalid_message(self, message: Message, socket: WebSocketServerProtocol, **kwargs):
        """
        Handler for Invalid message events

        Args:
            message: The message that was deemed invalid
            socket: The socket through which the message was received
            **kwargs:

        Returns:
            An InvalidMessageResponse informing the caller that the operation was invalid
        """
        response = InvalidMessageResponse(data=message)
        await socket.send(str(response))

    def _get_valid_message_types(self) -> MESSAGE_TYPES:
        """
        Get the types of messages that are handled by this interface

        Returns:
            A set of all handled types of messages
        """
        return set(self._event_handlers.keys()).union(self.get_parseable_request_types())

    async def deserialize_message(self, message_data: dict) -> typing.Optional[AbstractInitRequest]:
        """
        Attempt to deserialize the passed message into a recognized message type

        Args:
            message_data: The data to deserialize

        Returns:
            A Message representing the deserialized message data
        """
        for message_type in self._get_valid_message_types():
            message = message_type.factory_init_from_deserialized_json(message_data)
            if isinstance(message, message_type):
                return message
        return InvalidMessage(content=message_data)

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Listens to the given websocket and routes messages to the desired handlers

        Args:
            websocket: The socket to communicate through
            path: The path to the socket entry point on the server
        """
        client_ip = websocket.remote_address[0]

        # Websockets will return a connection closed exception when their connection has been closed.
        # Wrap the listening in a try block to correctly handle those situations
        try:
            await websocket.send("Connected to service")
            async for message in websocket:
                # A bad handle for a request is not necessarily a situation where everything should come screeching
                # to a halt. Catch the error, inform the caller, and continue to attempt to handle messages
                try:
                    data = json.loads(message)

                    if data is None:
                        continue

                    logging.info(f"Got payload: {data}")
                    request_message = await self.deserialize_message(message_data=data)
                    message_type = type(request_message)
                    handler = self._event_handlers.get(message_type)

                    if request_message.event_type == MessageEventType.INVALID:
                        await self.handle_invalid_message(request_message, websocket)
                        continue
                    if not handler:
                        msg = f'Received valid {request_message.__class__.__name__} request, but this ' \
                              f'{self.__class__.__name__} listener does not currently support it'

                        response = UnsupportedMessageTypeResponse(
                            actual_event_type=message_type,
                            listener_type=self.__class__,
                            data=data
                        )
                        logging.error(msg)
                        logging.error(response.message)
                        await websocket.send(str(response))
                        continue

                    keyword_arguments = {
                        "client_ip": client_ip,
                        "socket": websocket
                    }

                    # Assign parameters that may be found programmatically, possibly through mixins.
                    # Expect to see parameters like session data here.
                    additonal_parameters = await self._get_additional_arguments(websocket)
                    keyword_arguments.update(additonal_parameters)

                    response = await handler.handle_request(request=request_message, **keyword_arguments)
                except BaseException as error:
                    response = ErrorResponse(str(error))
                    logging.error(f"[{self.__class__.__name__}] {str(type(error))} occured ", exc_info=error)

                await websocket.send(str(response))
        except websockets.ConnectionClosedOK:
            # The websocket closed successfully; no action needed
            pass
        except websockets.ConnectionClosedError as connection_error:
            logging.error(f"[{self.__class__.__name__}] A connection unexpectedly closed", exc_info=connection_error)

        if websocket is not None and not websocket.closed:
            try:
                await websocket.send("No longer listening to socket")
            except:
                # THe message is a nicety - it's not a big deal if it doesn't go through
                pass


