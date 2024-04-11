"""
Defines the primary duplex for handling requests
"""
import asyncio
import inspect
import logging
import os
import typing
from typing import Any
import json
import pathlib

from datetime import datetime

import websockets

from dmod.communication import AbstractInitRequest
from dmod.communication import InitRequestResponseReason
from dmod.communication.registered import exceptions

from dmod.core import decorators
from dmod.core import common

from .exceptions import *
from .producer import Producer
from .producer import ProducerType
from .types import *
from .base import BaseDuplexHandler

from .response import ResponseData

from .actions import EndOperations
from .actions import ActionGet


# TODO: Refactor this mixin setup since getting it out of order can cause the 'diamond of death' for multi-inheritence
#class DuplexRequestHandler(EndOperations, GetActions, BaseDuplexHandler):
class DuplexRequestHandler(EndOperations, ActionGet, BaseDuplexHandler):
    """
    A request handler that registers one or more consumers and/or producers used to handle websocket requests
    """
    def __init__(
        self,
        target_service: str,
        service_host: str = 'localhost',
        service_port: int = None,
        ssl_directory: typing.Union[str, pathlib.Path] = None,
        websocket_protocol: str = None,
        client_arguments: typing.Dict[str, Any] = None,
        target_message_handlers: typing.Dict[str, MESSAGE_HANDLER] = None,
        source_message_handlers: typing.Dict[str, MESSAGE_HANDLER] = None,
        initial_message_handlers: typing.List[MESSAGE_HANDLER] = None,
        producers: typing.List[ProducerType] = None,
        source_handler_routing: HANDLER_ROUTING_TABLE = None,
        target_handler_routing: HANDLER_ROUTING_TABLE = None,
        *args,
        **kwargs
    ):
        """
        Constructor

        Args:
            target_service: The name of the service to hit
            service_host: Where the target service is
            service_port: The port through which to connect to
            ssl_directory: A directory leading to SSL information
            websocket_protocol: The websocket protocol to use (either 'ws' or 'wss')
            client_arguments: Extra arguments that should be used when connecting to a client
            target_message_handlers: Message handlers for strings that come through the client connection
            source_message_handlers: Message handlers for strings that come through the server connection
            initial_message_handlers: Message handlers that should be used on the first message to establish a connection
            producers: Connection consumers that produce their own messaages without prompting from the server or client
            source_handler_routing: A routing table directing concrete messages to specialized handlers for server messages
            target_handler_routing: A routing table directing concrete messages to specialized handlers for client messages
            *args:
            **kwargs:
        """
        super().__init__()
        self._target_service = target_service
        """
        The name of the service that is the target of this handler
        """

        self._service_host = service_host or 'localhost'
        """
        The host for the target service
        """

        self._service_port = service_port
        """
        The port through which to connect to the target service
        """

        self._path = kwargs.get("path", "/")
        """
        The path to this socket on the server
        
        If this was accessed via ws://localhost:9889/path/to/handler, path will be '/path/to/handler'
        """

        self._websocket_protocol = websocket_protocol or "ws"
        """
        The type of websocket protocol to use (ws or wss)
        """

        self._client_arguments = client_arguments or dict()
        """
        Arguments that should be used when creating new client connections
        """

        self.__ssl_directory = pathlib.Path(ssl_directory) if isinstance(ssl_directory, str) else ssl_directory
        """
        The directory containing SSL information
        """

        if self.__ssl_directory:
            if not isinstance(self.__ssl_directory, pathlib.Path):
                raise exceptions.RegistrationError(
                    f"A path-like object must be passed if an SSL directory is to be used. "
                    f"Received '{str(type(self.__ssl_directory))}' instead"
                )
            elif not self.__ssl_directory.exists():
                raise exceptions.RegistrationError(f"There is no SSL directory at '{str(self.__ssl_directory)}'")

        self._has_initialized = False
        """
        Whether or not the initialization step has been run
        """

        self.__initial_message_handlers = list()
        """
        The list of functions to run on new connections
        """

        # Add all initial connection handlers
        if initial_message_handlers:
            for handler in initial_message_handlers:
                self.add_initial_message_handler(handler)

        self.__target_message_handlers = dict()
        """
        A map of function names to functions made to handle strings that come through the client connection
        """

        if isinstance(target_message_handlers, typing.Mapping):
            for handler_name, handler in target_message_handlers.items():
                self.add_target_message_handler(handler_name, handler)
        elif target_message_handlers is not None:
            raise TypeError(
                f"The collection of target message handlers received was invalid; "
                f"expected a dictionary but received a {target_message_handlers.__class__.__name__} instead."
            )

        self.__source_message_handlers = dict()
        """
        A mapping between the name of a function and its function that handles strings that come through the server 
        connection
        """

        if isinstance(source_message_handlers, typing.Mapping):
            for handler_name, handler in source_message_handlers.items():
                self.add_source_message_handler(handler_name, handler)
        elif source_message_handlers is not None:
            raise TypeError(
                f"The collection of server message handlers received was invalid; "
                f"expected a dictionary but received a {source_message_handlers.__class__.__name__} instead."
            )

        self.__source_handler_routing = dict()
        """
        A mapping between concrete message type to all handlers that may operate on it when they come through the 
        server connection
        """

        if isinstance(source_handler_routing, typing.Mapping):
            for handler_type, handlers in source_handler_routing.items():
                for handler in handlers:
                    self.add_source_handler_route(handler_type, handler)
        elif source_handler_routing is not None:
            raise TypeError(
                f"The collection of server message handlers received was invalid; "
                f"expected a dictionary but received a {source_handler_routing.__class__.__name__} instead."
            )

        self.__target_handler_routing = dict()
        """
        A mapping between concrete message type to all handlers that may operate on it when they come through the 
        server connection
        """

        if isinstance(target_handler_routing, typing.Mapping):
            for handler_type, handlers in target_handler_routing.items():
                for handler in handlers:
                    self.add_target_handler_route(handler_type, handler)
        elif target_handler_routing is not None:
            raise TypeError(
                f"The collection of server message handlers received was invalid; "
                f"expected a dictionary but received a {target_handler_routing.__class__.__name__} instead."
            )

        self.__producers: typing.List[ProducerType] = list()
        """
        A mapping between function names and functions that produce their own messages
        """

        if common.is_sequence_type(producers):
            self.__producers = [producer for producer in producers]
        elif producers is not None:
            raise TypeError(
                f"The collection of producers received was invalid; "
                f"expected a list but received a {producers.__class__.__name__} instead."
            )

        self._initialize(service_host, service_port, websocket_protocol, client_arguments, *args, **kwargs)

    @property
    def target_service(self) -> str:
        """
        The name of the service being targetted by this handler
        """
        return self._target_service

    @property
    def has_initialized(self):
        """
        Whether this handler has been properly initialized
        """
        return self._has_initialized

    def add_producer(self, producer: ProducerType):
        """
        Add a function that produces messages to send through the target and/or server connections without their
        prompting

        Args:
            producer: The function that will produce messages
        """
        if not producer:
            return None

        if not issubclass(producer, Producer):
            raise exceptions.RegistrationError(
                f"'{str(producer)}' cannot be used as a message producer - only classes inheriting from "
                f"`Producer` may be used"
            )

        if producer not in self.__producers:
            self.__producers.append(producer)

    def add_source_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the server connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"{handler_name} ({handler.__name__}) cannot be used as a server message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__source_message_handlers[handler_name] = handler

    def add_source_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the server connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        # The handler must be asynchronous, so through an exception if it isn't
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"'{handler.__name__}' cannot be used as a source message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        if message_type not in self.__source_handler_routing:
            self.__source_handler_routing[message_type] = list()

        if handler not in self.__source_handler_routing[message_type]:
            self.__source_handler_routing[message_type].append(handler)

    def get_source_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for source messages
        """
        return {
            message_type: [handler for handler in handlers]
            for message_type, handlers in self.__source_handler_routing.items()
            if handlers is not None
        }

    def add_target_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the client connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"{handler_name} ({handler.__name__}) cannot be used as a target message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__target_message_handlers[handler_name] = handler

    def add_target_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the client connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        # The handler must be asynchronous, so through an exception if it isn't
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"'{handler.__name__}' cannot be used as a target message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        # Add an entry in the routing table if there isn't one for this message type already
        if message_type not in self.__target_handler_routing:
            self.__target_handler_routing[message_type] = list()

        # Add this handler to the routing table if it isn't already there
        if handler not in self.__target_handler_routing[message_type]:
            self.__target_handler_routing[message_type].append(handler)

    def get_target_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for messages from the target
        """
        return {
            message_type: [handler for handler in handlers]
            for message_type, handlers in self.__target_handler_routing.items()
            if handlers is not None
        }

    def add_initial_message_handler(self, handler: MESSAGE_HANDLER):
        """
        Add a message handler that will attempt to act on a message when this handler first accepts a connection

        Args:
            handler: A function that might handle a message
        """
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"{handler.__name__} cannot be used to interpret initial messages; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__initial_message_handlers.append(handler)

    @property
    def service_url(self):
        """
        Returns:
            The URL of the service that this should connect to
        """
        # Get the most basic version of the URL
        # if `self._service_host` == 'localhost'
        # and `self._service_port` == 9889
        # url will be 'localhost:9889`
        # if `self._service_port` wasn't set, the url will just be `localhost`
        url = f'{self._service_host}{":" + str(self._service_port) if self._service_port else ""}'

        # if `self._service_host` wasn't given a protocol (which is proper use), add the protocol to the
        # beginning of the url. This will result in `ws://localhost:9889` or `wss://localhost:9889`
        if not url.startswith("ws"):
            if self._websocket_protocol.endswith("://"):
                url = f"{self._websocket_protocol}{url}"
            else:
                url = f"{self._websocket_protocol}://{url}"

        # If a path to the target service is given, attach that to the end
        # If the target service has the entry point at `/ws/launch`, for example,
        # this will form `ws://localhost:9889/ws/launch`
        if self._path:
            if self._path.startswith("/"):
                url += self._path
            else:
                url = f'{url}/{self._path}'

        return url

    @property
    def ssl_directory(self) -> typing.Optional[pathlib.Path]:
        """
        The directory that bears SSL credentials for the service this handler connects to
        """
        return self.__ssl_directory

    def _initialize(self, *args, **kwargs):
        """
        Call additional initialization functions passed through by subclasses

        Initialization functions should have *args and **kwargs as arguments in order to pass possible initialization
        arguments through

        Args:
            *args: Positional arguments passed to the 'DuplexRequestHandler' abstract class constructor
            **kwargs: Keyword arguments passed to the 'DuplexRequestHandler' abstract class constructor
        """
        initialization_functions: typing.Sequence[typing.Callable] = decorators.find_functions_by_decorator(
            self,
            decorators.initializer
        )

        # Call all initialization functions, whether they are synchronous or not
        for function in initialization_functions:
            try:
                if inspect.iscoroutinefunction(function):
                    asyncio.get_event_loop().run_until_complete(function(self, *args, **kwargs))
                else:
                    function(self, *args, **kwargs)
            except Exception as error:
                function_name = f"self.{function.__name__}" if hasattr(function, "__name__") else f"'{str(function)}'"
                error_message = f"[{self.__class__.__name__}] could not call {function_name} for initialization"
                raise Exception(error_message) from error

        self._assign_handlers()

        self._has_initialized = True

    def _assign_handlers(self):
        """
        Add handlers for specific types of messages
        """
        # Find and assign all handlers decorated for server handlers that don't operate on concrete messages
        source_handlers = decorators.find_functions_by_attributes(
            source=self,
            decorator_name=decorators.SERVER_MESSAGE_HANDLER_ATTRIBUTE,
            excluded_attributes=[decorators.MESSAGE_TYPE_ATTRIBUTE, decorators.HANDLER_ACTION_ATTRIBUTE]
        )

        for name, function in source_handlers.items():
            self.add_source_message_handler(name, function)

        # Find and assign all handlers decorated for client handlers that don't operate on concrete messages
        target_handlers = decorators.find_functions_by_attributes(
            source=self,
            decorator_name=decorators.CLIENT_MESSAGE_HANDLER_ATTRIBUTE,
            excluded_attributes=[decorators.MESSAGE_TYPE_ATTRIBUTE, decorators.HANDLER_ACTION_ATTRIBUTE]
        )

        for name, function in target_handlers.items():
            self.add_target_message_handler(name, function)

        # Find and assign all handlers decorated for server handlers that require concrete messages
        typed_source_handlers = decorators.find_functions_by_attributes(
            source=self,
            decorator_name=decorators.SERVER_MESSAGE_HANDLER_ATTRIBUTE,
            required_attributes=[decorators.MESSAGE_TYPE_ATTRIBUTE, decorators.HANDLER_ACTION_ATTRIBUTE]
        )

        for name, function in typed_source_handlers.items():
            message_type = getattr(function, decorators.MESSAGE_TYPE_ATTRIBUTE)
            if issubclass(message_type, FieldedMessage):
                self.add_source_handler_route(message_type, function)

        # Find and assign all handlers decorated for client handlers that require concrete messages
        typed_target_handlers = decorators.find_functions_by_attributes(
            source=self,
            decorator_name=decorators.CLIENT_MESSAGE_HANDLER_ATTRIBUTE,
            required_attributes=[decorators.MESSAGE_TYPE_ATTRIBUTE, decorators.HANDLER_ACTION_ATTRIBUTE]
        )

        for name, function in typed_target_handlers.items():
            message_type = getattr(function, decorators.MESSAGE_TYPE_ATTRIBUTE)
            if issubclass(message_type, FieldedMessage):
                self.add_target_handler_route(message_type, function)

    async def _generate_response(self, tasks: typing.Collection[asyncio.Task]) -> Response:
        """
        Creates a service response based on the responses of sub-tasks

        Args:
            tasks: Tasks that were run as sub-tasks of the core socket handler

        Returns:
            An aggregated Response
        """
        if not self._has_initialized:
            raise InitializationError(self)

        # Since the overall operation was considered an 'init' operation, other parts of the code base may expect an
        # `InitRequestResponseReason`. Here we just add whatever reason seems reasonable
        reason = InitRequestResponseReason.ACCEPTED if tasks else InitRequestResponseReason.UNNECESSARY
        message = "Registered tasks completed" if tasks else "There were no tasks to complete"

        data = dict()
        fail_reasons: typing.List[common.Failure] = list()

        # We want to mark each task as completed and record some response detailing its work and any sort of failure
        for task in tasks:
            task_exception: typing.Optional[BaseException] = None
            task_message = None
            result: typing.Optional[Response] = None

            # Maybe the task was successfully completed, maybe not. Here we just give it another chance to finish
            await common.wait_on_task(task)

            try:
                # If the task is done at this point we can attempt to get a result. It is considered a success
                # if the task is done and we get a result
                if task.done():
                    result = task.result()
                    task_success = True
                else:
                    # If the task isn't done we just mark it as having not succeeded and set the result to none
                    task_message = f"The task named '{task.get_name()}' did not properly complete"
                    task_success = False
                    result = None
            except asyncio.CancelledError:
                # It is unlikely, but if there was a cancellation here we can catch it
                task_message = f"Task '{task.get_name()}' was cancelled"

                # A cancellation is considered a success because cancellation came from outside the operation,
                # not within
                task_success = True
            except asyncio.InvalidStateError:
                # The operation may hit a situation where an invalid state was encountered. Record it and move on
                # since this is unrecoverable in this operation
                # TODO: Find out if an Invalid State affects all operations and set this up to exit early if needed
                task_message = f"Task '{task.get_name()}' enountered invalid state"
                task_success = False
            except Exception as exception:
                # Just record the error if it wasn't predicted
                task_message = f"Task '{task.get_name()}': {str(exception)}"
                task_exception = exception
                task_success = False

            # Try to find any instance of an exception
            if not task_exception:
                try:
                    task_exception = task.exception()
                except:
                    # There are a few situations where trying to get the exception doesn't yield the exception or
                    # None as the doc states. Catch it here because we don't need it if it's not there
                    pass

            # If the operation returned a `Response` object (desired behavior) pull its values to inform the upcoming
            # response
            if result and isinstance(result, Response):
                if len(tasks) == 1:
                    reason = result.reason
                    message = result.message

                task_message = result.message
                task_success = result.success
                result = result.data

            if task_exception:
                task_error = str(task_exception)
            elif not task_success:
                task_error = task_message
            else:
                task_error = None

            task_data = {
                "message": task_message,
                "success": task_exception is None and task_success,
                "cancelled": task.done() and task.cancelled(),
                "name": task.get_name(),
                "error": task_error,
                "result": result
            }

            data[task.get_name()] = task_data

            # Create and record a Failure description if it was indeed considered a failure of some sort
            # There are three possible failure states:
            #   1) The `Task` ended operations correctly but the response said it could not fulfill its duties
            #   2) An exception was triggered in the Task, causing it to exit early
            #   3) Something happened (most likely within this loop) that marked the Task as a failure
            if isinstance(result, Response) and not result.success:
                fail_reasons.append(common.Failure(task.get_name(), result.reason, result.message))
            elif task_exception:
                fail_reasons.append(common.Failure(task.get_name(), "error", str(task_exception), task_exception))
            elif not task_success:
                fail_reasons.append(common.Failure(task.get_name(), "error", task_error, task_error))

        # The overall operation is deemed a success if there were no failures
        success = len(fail_reasons) == 0

        # Set the overall message to a description of the failures or just use the generic message from the
        # beginning of the function
        message = common.Failure.explain(fail_reasons) or message

        return self._get_response_class()(
            success=success,
            reason=reason,
            data=data,
            message=message
        )

    @property
    def _recognized_message_types(self) -> typing.Set[typing.Type[FieldedMessage]]:
        """
        A set of all concrete message types utilized by this handler
        """
        recognized_types: typing.Set[typing.Type[FieldedMessage]] = set()

        for message_type in self.__source_handler_routing:
            recognized_types.add(message_type)

        for message_type in self.__target_handler_routing:
            recognized_types.add(message_type)

        return recognized_types

    def parse_socket_input(self, socket_input: typing.Union[str, bytes]) -> typing.Union[str, FieldedMessage, bytes]:
        """
        Convert the passed socket data into either a concrete message or just a string or byte

        Args:
            socket_input: The data that arrived through a socket

        Returns:
            A deserialized version of the socket data
        """
        try:
            parsed_input = None

            if self._recognized_message_types:
                # Try and actually deserialize the input into a dictionary for further identification
                parsed_input = json.loads(socket_input)

            if parsed_input:
                # Try to convert the JSON into a valid message type
                for recognized_type in self._recognized_message_types:
                    message = recognized_type.factory_init_from_deserialized_json(parsed_input)
                    if message:
                        return message
        except:
            # The input could not be parsed into JSON to check for a concrete message
            pass

        if isinstance(socket_input, bytes):
            try:
                socket_input = socket_input.decode()
            except:
                # The data could not be decoded, which is fine - this may happen if pure binary data is passed
                pass

        return socket_input

    async def listen_to_messages(
        self,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        typed_handlers: typing.Mapping[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]],
        untyped_handlers: typing.Iterable[MESSAGE_HANDLER],
        *args,
        **kwargs
    ) -> Response:
        """
        Listen for messages from the server

        Args:
            source: The socket connection that provides messages
            target: The socket connection that does not provide messages
            path: The path to this handler on the server
            typed_handlers: Message handlers for messages that can be deserialized into a FieldedMessage
            untyped_handlers: Message handlers for messages that can't be deserialized into Fielded messages
            *args:
            **kwargs:

        Returns:
            A response reporting on the success of this operation
        """
        # Make sure that the source is a websocket protocol and open so that messages may be correctly listened to
        if not isinstance(source, WebSocketCommonProtocol):
            raise TypeError(
                f"The websocket connection to the server passed to `listen_to_messages` is not unusable; "
                f"a `WebSocketServerProtocol` was expected, but received "
                f"{'Nothing' if source is None else source.__class__.__name__} instead"
            )
        elif source.closed:
            raise ValueError(
                f"The websocket connection to the server passed to `listen_to_messages` is not unusable; "
                f"it is not open."
            )

        # Make sure that the target is a websocket protocol and open so that messages may be correctly transmitted
        if target is None:
            logging.warning(
                f"No target connection was passed to {common.get_current_function_name(parent_name=True)}; "
                f"Any attempt to communicate with another service will fail. "
            )
        elif not isinstance(target, WebSocketCommonProtocol):
            raise TypeError(
                f"The websocket connection to the target passed to `listen_to_messages` is not usable; "
                f"a `WebSocketCommonProtocol` was expected, but received "
                f"{'Nothing' if target is None else target.__class__.__name__} instead"
            )
        elif target.closed:
            raise ValueError(
                f"The websocket connection to the target passed to `listen_to_messages` is not usable; "
                f"it is not open."
            )

        response_data = ResponseData()

        try:
            # Listen and act upon messages that come from the source of the messages
            async for message in source:
                response_data += 1
                parsed_message = self.parse_socket_input(message)

                # Identify what sort of handlers to use
                if type(parsed_message) in typed_handlers:
                    # If a specific type of message is supposed to be used, go ahead and use those due to specificity
                    handlers = typed_handlers[type(parsed_message)]
                    payload = parsed_message
                else:
                    handlers = untyped_handlers
                    payload = message

                for handler in handlers:
                    try:
                        # TODO: Should these be added as tasks to run at the same time?
                        #   If so, place the name and unawaited results into an intermediary dictionary and await the
                        #   group once all have been assigned. Once awaited, attach THOSE to the response data.
                        result = await handler(payload, source, target, path, *args, **kwargs)
                        response_data.add(handler.__name__, result)
                    except UnicodeError:
                        # This will be encountered if bytes are attempted to be decoded.
                        # This is fine for some data, so shouldn't be a complete blocker
                        pass
            raise OperationComplete()
        except OperationComplete as complete:
            message = str(complete) or "Operations are complete"
            success = True
            reason = "Client-server communication is no longer being listened to"
        except websockets.ConnectionClosedOK:
            # This is fine; the connection just closed
            message = f"Websocket connection closed"
            reason = InitRequestResponseReason.ACCEPTED.name
            success = True
        except asyncio.CancelledError:
            # This is fine; the connection just closed
            message = f"Operation cancelled"
            reason = InitRequestResponseReason.ACCEPTED.name
            success = True
        except websockets.ConnectionClosedError as error:
            # This is fine; the connection just closed
            message = f"Websocket connection closed unexpectedly: {str(error)}"
            success = False
            reason = InitRequestResponseReason.REJECTED.name
        except Exception as exception:
            reason = InitRequestResponseReason.UNKNOWN.name
            success = False
            message = f"[{common.get_current_function_name()}] An exception was encountered while running the " \
                      f"request handler: {str(exception)}"
            logging.error(message, exc_info=exception)
        finally:
            response_data.close()

        return self._get_response_class()(
            success=success,
            reason=reason,
            message=message,
            data=response_data
        )

    async def listen_to_server(
        self,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ) -> Response:
        """
        Listen for messages from the server

        Args:
            source: The socket connection from this server
            target: The socket connection to the target that this communicates with
            path: The path to this handler on the server
            *args:
            **kwargs:

        Returns:
            A response reporting on the success of this operation
        """
        return await self.listen_to_messages(
            source=source,
            target=target,
            path=path,
            typed_handlers=self.__source_handler_routing,
            untyped_handlers=self.__source_message_handlers.values(),
            *args,
            **kwargs
        )

    async def listen_to_client(
        self,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ) -> Response:
        """
        Listen for messages from the target

        Args:
            source: The socket connection from this server
            target: The socket connection to the target that this communicates with
            path: The path to this handler on the server
            *args:
            **kwargs:

        Returns:
            A response reporting on the success of this operation
        """
        # This is almost identical to the above `listen_to_server` call. The difference here is that the messages
        # come FROM the target.
        return await self.listen_to_messages(
            source=target,                                                  # Messages come from the target
            target=source,                                                  # Messages may flow back to the source
            path=path,
            typed_handlers=self.__target_handler_routing,
            untyped_handlers=self.__target_message_handlers.values(),
            *args,
            **kwargs
        )

    async def start_producing_messages(
        self,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ) -> typing.List[asyncio.Task]:
        """
        Starts running all functions that will produce their own messages

        Args:
            source: The websocket connection that is being handled
            target: The websocket connection to a server acting as the target of this handler
            path: The path to the source on this server

        Returns:
            All tasks that will be producing their own messages
        """
        # Throw an error if this hasn't been initialized yet
        if not self._has_initialized:
            raise InitializationError(self)

        running_producers: typing.List[asyncio.Task] = list()

        for producer in self.__producers:
            try:
                running_producers.append(producer.start(source, target, path, *args, **kwargs))
            except:
                try:
                    await source.send("Error occurred; Cancelling tasks...")
                except BaseException as notification_exception:
                    logging.error(
                        f"Failed to notify the caller that jobs are being cancelled: {str(notification_exception)}",
                        exc_info=notification_exception
                    )

                await common.cancel_tasks(
                    tasks=running_producers,
                    incomplete_message=lambda t: f"Could not cancel the producer task named '{t.get_name()}' "
                                                 f"after a producer function failed to launch",
                    cancel_message=lambda t: f"Cancelling the producer named {t.get_name()}; the producer named "
                                             f"{producer.get_name()} failed to start.",
                    cancel_failed_message=lambda t, exception: f"An error occurred when trying to cancel the producer "
                                                               f"task '{t.get_name()}' after the launching of the "
                                                               f"producer named '{producer.get_name()}' "
                                                               f"failed: {str(exception)}"
                )
                raise

        # Find all possible handler functions via decorator inspection
        producer_functions: typing.Sequence[MESSAGE_PRODUCER] = decorators.find_functions_by_decorator(
            self,
            decorators.producer_message_handler
        )

        # Make sure all identified functions are awaitable so that they can properly handle their sockets
        for function in producer_functions:
            try:
                function_name = getattr(function, "__name__")

                if function_name is None:
                    raise InitializationError(
                        f"The initialization of an '{str(self.__class__)}' instance created an invalid producer: "
                        f"{str(function)}"
                    )

                if not inspect.iscoroutinefunction(function):
                    raise exceptions.RegistrationError(
                        f"self.{function_name} cannot be used as a producer; "
                        f"only asynchronous functions (marked by `async def`) may be used"
                    )

                running_producers.append(
                    asyncio.create_task(function(source, target, path, *args, **kwargs), name=function_name)
                )
            except BaseException as error:
                logging.error(f"[{self.__class__.__name__}] Failed to launch producers", exc_info=error)
                try:
                    await source.send("Error occurred; Cancelling tasks...")
                except BaseException as notification_exception:
                    logging.error(
                        f"Failed to notify the caller that jobs are being cancelled: {str(notification_exception)}",
                        exc_info=notification_exception
                    )
                failing_function_name = getattr(function, "__name__", str(function))
                await common.cancel_tasks(
                    tasks=running_producers,
                    incomplete_message=lambda t: f"Could not cancel the producer task named '{t.get_name()}' "
                                                 f"after a producer function failed to launch",
                    cancel_message=lambda t: f"Cancelling the producer named {t.get_name()}; the producer named "
                                             f"'{failing_function_name}' failed to start.",
                    cancel_failed_message=lambda t, exception: f"An error occurred when trying to cancel the producer "
                                                               f"task '{t.get_name()}' after the launching of the "
                                                               f"producer named '{failing_function_name}' "
                                                               f"failed: {str(exception)}"
                )
                raise
        return running_producers

    async def _handle_initial_message(
        self,
        request: AbstractInitRequest,
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str = None,
        **kwargs
    ):
        """
        Call all operations that need to be performed on the first message

        Args:
            request: The message to act on
            source: The connection that this message came through
            target: The connection to a targetted service
            path: An optional path to this endpoint on the server
            **kwargs:
        """
        for handler in self.__initial_message_handlers:
            await handler(request, source, target, path, **kwargs)

    async def handle_request(
        self,
        request: AbstractInitRequest,
        source: WebSocketCommonProtocol = None,
        path: str = None,
        **kwargs
    ) -> Response:
        """
        Run all request handlers on the incoming request

        Args:
            request: The request that precipitated the need for a handler
            source: The socket through which the request came through
            path: The path to the socket on the server
            **kwargs:

        Returns:
            A response summarizing the all operations
        """
        if not self._has_initialized:
            raise InitializationError(self)

        response: typing.Optional[Response] = None

        target: typing.Optional[WebSocketCommonProtocol] = None

        try:
            source_address = f"w{'s' if source.secure else ''}s://"
            source_address += source.local_address[0]

            if len(source.local_address) > 1 and source.local_address[1]:
                source_address += ":" + str(source.local_address[1])

            source_address += path

            client_would_be_source = self.service_url == source_address

            if not client_would_be_source:
                target = await websockets.connect(self.service_url, **self._client_arguments)

            connection_data = json.dumps({
                "event": f"A connection to {self.target_service} has been established."
            })
            await source.send(connection_data)
            await self._handle_initial_message(request, source, target, path, **kwargs)

            # Launch all async functions that aren't reactive to a socket or client
            tasks: typing.List[asyncio.Task] = await self.start_producing_messages(source, target, path)

            # Start the task that will listen for messages from the connection linking to the original caller
            tasks.append(asyncio.create_task(self.listen_to_server(source, target, path), name="listen_to_server"))

            if target is not None:
                # Start the task that will listen for messages from the targeted service
                tasks.append(asyncio.create_task(self.listen_to_client(source, target, path), name="listen_to_client"))

            try:
                # If this is supposed to handle concurrent reading and sending, you don't want one running while
                # another has finished, so close them all down
                await asyncio.wait(
                    fs=tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
            except BaseException as exception:
                try:
                    await source.send("Error occurred; Cancelling tasks...")
                except BaseException as notification_exception:
                    logging.error(
                        f"Failed to notify the caller that jobs are being cancelled: {str(notification_exception)}",
                        exc_info=notification_exception
                    )
                await common.cancel_tasks(
                    tasks=tasks,
                    incomplete_message=lambda t: f"Could not cancel the task named '{t.get_name()}' "
                                                 f"after an error occurred",
                    cancel_message=lambda t: f"Cancelling '{t.get_name()}'; an error occurred when waiting for "
                                             f"tasks to run. {str(exception)}"
                )
                raise

            # Cancel all tasks that haven't finished
            try:
                await source.send("Operations complete; cancelling tasks...")
            except BaseException as notification_exception:
                logging.error(
                    f"Failed to notify the caller that jobs are being cancelled: {str(notification_exception)}",
                    exc_info=notification_exception
                )
            await common.cancel_tasks(
                tasks=tasks,
                incomplete_message=lambda t: f"Could not cancel the task named '{t.get_name()}' "
                                             f"after operations have completed",
                cancel_message=lambda t: f"Cancelling '{t.get_name()}'; operations have concluded"
            )

            response = await self._generate_response(tasks)
        except websockets.ConnectionClosedOK:
            # This is fine; the connection just closed
            response = self._get_response_class()(
                success=True,
                reason=InitRequestResponseReason.ACCEPTED.name,
                message=f"Websocket connection closed",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
                }
            )
        except websockets.ConnectionClosedError as error:
            # This is fine; the connection just closed
            response = self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.REJECTED.name,
                message=f"Websocket connection closed unexpectedly: {str(error)}",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "error": str(error)
                }
            )
        except BaseException as exception:
            message = f"An exception was encountered while running the request handler: {str(exception)}"
            logging.error(message, exc_info=exception)
            response = self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.UNKNOWN.name,
                message=message,
                data={
                    "error": str(exception)
                }
            )
        finally:
            if target and not target.closed:
                try:
                    await target.close()
                except Exception as target_close_exception:
                    logging.error(
                        f"Could not properly close the target connection to {self.service_url}: "
                        f"{str(target_close_exception)}"
                    )

        if not response.success:
            message = f"Operation in {self.__class__.__name__} failed:{os.linesep}{response.to_json()}"
            logging.error(message)
            print(message)

        return response

