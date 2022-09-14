"""
Defines the ConsumerProducer base classes for handling requests
"""
import inspect
import typing
import logging
from typing import Any
import abc
import asyncio
import json
import pathlib
import os

from datetime import datetime

import websocket
import websockets
from websockets import WebSocketServerProtocol
from websockets import WebSocketClientProtocol

from dmod.communication import Message
from dmod.communication import AbstractInitRequest
from dmod.communication import Response
from dmod.communication import InitRequestResponseReason
from dmod.communication import InternalServiceClient
from dmod.communication import DynamicFunctionMixin
from dmod.communication import AbstractRequestHandler
from dmod.communication.registered import aliases
from dmod.communication.registered import exceptions

from dmod.core import decorators

from .state import HandlerState


CLOSE_MESSAGE = "DISCONNECT"


MESSAGE_HANDLER = typing.Callable[
    [typing.Union[str, bytes], WebSocketServerProtocol, WebSocketClientProtocol, str, typing.Optional[typing.Any]],
    typing.Coroutine
]
MESSAGE_PRODUCER = typing.Callable[
    [WebSocketServerProtocol, WebSocketClientProtocol, str, typing.Optional[typing.Any]],
    typing.Coroutine[typing.Any, typing.Any, Response]
]


def get_current_function_name():
    return inspect.stack()[1][3]


def is_collection_type(value) -> bool:
    return value is not None and not isinstance(value, (str, bytes, typing.Mapping)) and isinstance(value, (typing.Sequence, set))


def merge_dictionaries(first: dict, second: dict) -> dict:
    merged_dictionary = dict()

    if first is None and second is None:
        return merged_dictionary
    elif first is None:
        return second
    elif second is None:
        return first

    for key_for_first, value_for_first in first.items():
        if key_for_first not in second:
            merged_dictionary[key_for_first] = value_for_first
        else:
            value_for_second = second[key_for_first]
            combined_value = None

            if value_for_first is None and value_for_second is None:
                combined_value = None
            elif value_for_first is not None and value_for_second is None:
                combined_value = value_for_first
            elif value_for_second is not None and value_for_first is None:
                combined_value = value_for_second
            elif is_collection_type(value_for_first) and is_collection_type(value_for_second):
                combined_value = [value for value in value_for_first] + [value for value in value_for_second]
            elif is_collection_type(value_for_first):
                combined_value = [value for value in value_for_first]
                combined_value.append(value_for_second)
            elif is_collection_type(value_for_second):
                combined_value = [value for value in value_for_second]
                combined_value.append(value_for_first)
            else:
                combined_value = [value_for_first, value_for_second]

            merged_dictionary[key_for_first] = combined_value

    # we don't have to merge conflicts h
    merged_dictionary.update({
        key_for_second: value_for_second
        for key_for_second, value_for_second in second.keys()
        if key_for_second not in merged_dictionary
    })

    return merged_dictionary


class InitializationError(Exception):
    """
    Exception thrown when the initialization of a class was not performed
    """
    def __init__(self, klazz: typing.Any):
        if isinstance(klazz, str):
            name = klazz
        elif isinstance(klazz, type):
            name = klazz.__name__
        else:
            name = klazz.__class__.__name__

        message = f"{name} was not properly initialized. Make sure __init__ was called. __init__ is only called " \
                  f"automatically on the first parent class in the list."

        super().__init__(message)


class OperationComplete(BaseException):
    """
    Indicates that an operation has completed and that a cycle needs to stop
    """


class Failure:
    """
    Metadata about how a task failed
    """
    def __init__(self, task_name: str, reason: str, message: str, exception: BaseException = None):
        self.task_name = task_name
        self.reason = reason
        self.message = message
        self.exception = exception

    def __str__(self):
        message = f"Task '{self.task_name}' failed: {self.message}."

        if self.exception and self.exception != self.message:
            message += f" Error: {str(self.exception)}"

        return message

    def __repr__(self):
        return self.__str__()


class DuplexResponse(Response):
    """
    A general response showing the result of all tasks run within the ConsumerProducerRequestHandler
    """
    def __init__(
        self,
        success: bool,
        data: dict,
        reason: InitRequestResponseReason = None,
        message: str = None,
        *args,
        **kwargs
    ):
        reason = reason or InitRequestResponseReason.UNKNOWN.name

        if isinstance(reason, InitRequestResponseReason):
            reason = reason.name
        elif reason is not None:
            reason = str(reason)

        super().__init__(
            success=success,
            data=data,
            reason=reason or InitRequestResponseReason.UNKNOWN.name,
            message=message,
            *args,
            **kwargs
        )
        self.data = data
        self.message = message
        self.reason = reason
        self.success = success


class BaseDuplexHandler(abc.ABC):
    """
    Base class for full handler implementations and mixins that feature bidirectional communication
    """
    @classmethod
    @abc.abstractmethod
    def get_target_service(cls) -> str:
        """
        Returns:
            A human friendly name for what service this handler should be targetting
        """
        ...

    @classmethod
    def _get_response_class(cls) -> typing.Type[Response]:
        """
        Get the type of default response that this class will return from the handler

        Override for custom response types

        Returns:
            The type of default Response that this handler should use
        """
        return DuplexResponse

    @property
    @abc.abstractmethod
    def _state(self) -> HandlerState:
        ...


class MessageHandlerMixin(BaseDuplexHandler, abc.ABC):
    """
    Base class used to indicate that the contents define functions to handle message interpretation
    """


class DuplexRequestHandler(DynamicFunctionMixin, BaseDuplexHandler, AbstractRequestHandler, abc.ABC):
    """
    A request handler that registers one or more consumers and/or producers used to handle websocket requests
    """
    def __init__(
        self,
        service_host: str,
        service_port: int = None,
        ssl_directory: typing.Union[str, pathlib.Path] = None,
        websocket_protocol: str = None,
        client_arguments: typing.Dict[str, Any] = None,
        client_message_handlers: typing.Dict[str, MESSAGE_HANDLER] = None,
        server_message_handlers: typing.Dict[str, MESSAGE_HANDLER] = None,
        producers: typing.Dict[str, MESSAGE_PRODUCER] = None,
        *args,
        **kwargs
    ):
        self._default_required_access_type = None
        self._service_host = service_host
        self._service_port = service_port
        self._service_client = None
        self._path = kwargs.get("path", "/")
        self._websocket_protocol = websocket_protocol or "ws"
        self._client_arguments = client_arguments or dict()
        self.__state: typing.Optional[HandlerState] = None
        self.__ssl_directory = pathlib.Path(ssl_directory) if isinstance(ssl_directory, str) else ssl_directory
        self._has_initialized = False

        self.__client_message_handlers = dict()

        if isinstance(client_message_handlers, typing.Mapping):
            for handler_name, handler in client_message_handlers.items():
                self.add_client_message_handler(handler_name, handler)
        elif client_message_handlers is not None:
            raise ValueError(
                f"The collection of client message handlers received was invalid; "
                f"expected a dictionary but received a {client_message_handlers.__class__.__name__} instead."
            )

        self.__server_message_handlers = dict()

        if isinstance(server_message_handlers, typing.Mapping):
            for handler_name, handler in server_message_handlers.items():
                self.add_server_message_handler(handler_name, handler)
        elif server_message_handlers is not None:
            raise ValueError(
                f"The collection of server message handlers received was invalid; "
                f"expected a dictionary but received a {server_message_handlers.__class__.__name__} instead."
            )

        self.__producers = dict()

        if isinstance(producers, typing.Mapping):
            for handler_name, handler in producers.items():
                self.add_producer(handler_name, handler)
        elif producers is not None:
            raise ValueError(
                f"The collection of producers received was invalid; "
                f"expected a dictionary but received a {producers.__class__.__name__} instead."
            )

        self._initialize(service_host, service_port, websocket_protocol, client_arguments, *args, **kwargs)

    def add_producer(self, producer_name: str, producer: MESSAGE_PRODUCER):
        if not inspect.iscoroutinefunction(producer):
            raise exceptions.RegistrationError(
                f"{producer_name} ({producer.__name__}) cannot be used as a server message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__server_message_handlers[producer_name] = producer

    def add_server_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"{handler_name} ({handler.__name__}) cannot be used as a server message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__server_message_handlers[handler_name] = handler

    def add_client_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        if not inspect.iscoroutinefunction(handler):
            raise exceptions.RegistrationError(
                f"{handler_name} ({handler.__name__}) cannot be used as a client message handler; "
                f"only asynchronous functions (marked by `async def`) may be used"
            )

        self.__client_message_handlers[handler_name] = handler

    @property
    def _state(self) -> HandlerState:
        if not self._has_initialized:
            raise InitializationError(self)
        return self.__state

    @property
    def service_url(self):
        """
        Returns:
            The URL of the service that this should connect to
        """
        if not self._has_initialized:
            raise InitializationError(self)

        url = f'{self._service_host}{":" + str(self._service_port) if self._service_port else ""}'

        if not url.startswith("ws"):

            if self._websocket_protocol.endswith("://"):
                url = f"{self._websocket_protocol}{url}"
            else:
                url = f"{self._websocket_protocol}://{url}"

        if self._path:
            if self._path.startswith("/"):
                url += self._path
            else:
                url = f'{url}/{self._path}'

        return url

    @property
    def ssl_directory(self) -> typing.Optional[pathlib.Path]:
        return self.__ssl_directory

    def _construct_client(self) -> typing.Optional[InternalServiceClient]:
        """
        Returns:
            Creates the client used to connect to a service
        """
        return None

    def _get_client_message_handlers(self) -> typing.Iterable[typing.Tuple[str, MESSAGE_HANDLER]]:
        """
        Returns:
            All functions that need to act on incoming client messages
        """
        if not self._has_initialized:
            raise InitializationError(self)

        # Find all possible handler functions via decorator inspection
        handler_functions: typing.Dict[str, MESSAGE_HANDLER] = self._get_dynamic_functions(
            decorators.CLIENT_MESSAGE_HANDLER_ATTRIBUTE
        )

        handlers: typing.Dict[str, MESSAGE_HANDLER] = dict()

        # Make sure all identified functions are awaitable so that they can properly handle their sockets
        for name, function in handler_functions.items():
            if not inspect.iscoroutinefunction(function):
                raise exceptions.RegistrationError(
                    f"self.{name} cannot be used as a registered client handler; "
                    f"only asynchronous functions (marked by `async def`) may be used"
                )
            handlers[name] = function

        for name, function in self.__client_message_handlers.items():
            if not inspect.iscoroutinefunction(function):
                raise exceptions.RegistrationError(
                    f"An invalid message handler meant to read messages from the client is present."
                    f"'{name}' ({function.__name__}) cannot be used as a registered server handler; "
                    f"only asynchronous functions (marked by `async def`) may be used"
                )
            handlers[name] = function

        names_and_handlers = [(name, function) for name, function in handlers.items()]

        if 'end_operations' not in handlers:
            names_and_handlers.insert(0, ('end_operations', self.end_operations))

        return names_and_handlers

    def _get_server_message_handlers(self) -> typing.Iterable[typing.Tuple[str, MESSAGE_HANDLER]]:
        """
        Returns:
            All functions that need to act on incoming client messages
        """
        if not self._has_initialized:
            raise InitializationError(self)

        # Find all possible handler functions via decorator inspection
        handler_functions: typing.Dict[str, MESSAGE_HANDLER] = self._get_dynamic_functions(
            decorators.SERVER_MESSAGE_HANDLER_ATTRIBUTE
        )

        handlers: typing.Dict[str, MESSAGE_HANDLER] = dict()

        # Make sure all identified functions are awaitable so that they can properly handle their sockets
        for name, function in handler_functions.items():
            if not inspect.iscoroutinefunction(function):
                raise exceptions.RegistrationError(
                    f"self.{name} cannot be used as a registered server handler; "
                    f"only asynchronous functions (marked by `async def`) may be used"
                )
            handlers[name] = function

        for name, function in self.__server_message_handlers.items():
            if not inspect.iscoroutinefunction(function):
                raise exceptions.RegistrationError(
                    f"An invalid message handler meant to read messages from the server is present."
                    f"'{name}' ({function.__name__}) cannot be used as a registered server handler; "
                    f"only asynchronous functions (marked by `async def`) may be used"
                )
            handlers[name] = function

        names_and_handlers = [(name, handler) for name, handler in handlers.items()]

        if 'end_operations' not in handlers:
            names_and_handlers.insert(0, ('end_operations', self.end_operations))

        return names_and_handlers

    def _initialize(self, *args, **kwargs):
        """
        Call additional initialization functions passed through by subclasses

        Initialization functions should have *args and **kwargs as arguments in order to pass possible initialization
        arguments through

        Args:
            *args: Positional arguments passed to the 'ConsumerProducerRequestHandler' abstract class constructor
            **kwargs: Keyword arguments passed to the 'ConsumerProducerRequestHandler' abstract class constructor
        """

        self._has_initialized = True
        self.__state = HandlerState(**kwargs)

        initialization_functions: typing.Dict[str, typing.Callable] = self._get_dynamic_functions(
            decorators.INITIALIZER_ATTRIBUTE
        )

        for name, function in initialization_functions.items():
            try:
                if inspect.isawaitable(function):
                    asyncio.get_event_loop().run_until_complete(function(self, *args, **kwargs))
                else:
                    function(self, *args, **kwargs)
            except Exception as error:
                error_message = f"[{self.__class__.__name__}] could not call self.{name} for initialization"
                raise Exception(error_message) from error

    @property
    def service_client(self) -> typing.Optional[InternalServiceClient]:
        """
        Provides a simple client for communication with the target service

        The provided communication functions will open a connection, send a message to the service, await for a
        response, and close the connection. This should not be used for services that should maintain a long-running
        connection or for connections that need to be shared across functions

        Returns:
            An interface for short term http-like websocket communication
        """
        if not self._has_initialized:
            raise InitializationError(self)

        if self._service_client is None:
            self._service_client = self._construct_client()
        return self._service_client

    async def determine_required_access_types(self, request: Message, user) -> tuple:
        """
        Determine what access is required for this request from this user to be accepted.

        Determine the necessary access types for which the given user needs to be authorized in order for the user to
        be allow to submit this request, in the context of the current state of the system.

        Parameters
        ----------
        request
        user

        Returns
        -------
        A tuple of required access types required for authorization for the given request at this time.
        """
        if not self._has_initialized:
            raise InitializationError(self)

        # TODO: implement; in particular, consider things like current job count for user, and whether different access
        #   types are required at different counts.
        # FIXME: for now, just use the default type (which happens to be "everything")
        return self._default_required_access_type,

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

        success = True
        reason = InitRequestResponseReason.ACCEPTED if tasks else InitRequestResponseReason.UNNECESSARY
        message = "Tasks completed successfully" if tasks else "There were no tasks to complete"

        max_wait_count = 5
        data = dict()
        fail_reasons: typing.List[Failure] = list()

        for task in tasks:
            task_exception: typing.Optional[BaseException] = None
            task_message = None
            result: typing.Optional[Response] = None

            wait_count = 0
            while not task.done() and wait_count < max_wait_count:
                # Wait for the task to finish just in case it has its own asyncio sleep within (possible for producers)
                await asyncio.sleep(3)
                wait_count += 1

            cancelled = not task.done() or task.cancelled()

            try:
                if task.done():
                    result = task.result()
                    task_success = True
                else:
                    task_message = f"The task named '{task.get_name()}' did not properly complete"
                    task_success = False
                    result = None
            except asyncio.CancelledError:
                task_message = f"Task '{task.get_name()}' was cancelled"
                task_success = True
            except asyncio.InvalidStateError:
                task_message = f"Task '{task.get_name()}' enountered invalid state"
                task_success = False
            except Exception as exception:
                task_message = f"Task '{task.get_name()}': {str(exception)}"
                task_exception = exception
                task_success = False

            if not task_exception:
                try:
                    task_exception = task.exception()
                except:
                    pass

            if result and isinstance(result, Response):
                if len(tasks) == 1:
                    reason = result.reason
                    message = result.message
                    success = result.success

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
                "cancelled": cancelled,
                "name": task.get_name(),
                "error": task_error,
                "result": result
            }

            data[task.get_name()] = task_data

            if isinstance(result, Response) and not result.success:
                fail_reasons.append(Failure(task.get_name(), result.reason, result.message))
            elif task_exception:
                fail_reasons.append(Failure(task.get_name(), "error", str(task_exception), task_exception))
            elif not task_success:
                fail_reasons.append(Failure(task.get_name(), "error", task_error, task_error))

        success = len(fail_reasons) == 0
        message = explain_failures(fail_reasons) or message

        return self._get_response_class()(
            success=success,
            reason=reason,
            data=data,
            message=message
        )

    async def listen_to_server(
        self,
        socket: WebSocketServerProtocol,
        client: WebSocketClientProtocol,
        path: str,
        *args,
        **kwargs
    ) -> Response:
        """
        Listen for messages from the server

        Args:
            socket: The socket connection from this server
            client: The socket connection to the client that this communicates with
            path: The path to this handler on the server
            *args:
            **kwargs:

        Returns:
            A response reporting on the success of this operation
        """
        if not isinstance(socket, WebSocketServerProtocol):
            raise ValueError(
                f"The websocket connection to the server passed to `listen_to_server` is not unusable; "
                f"a `WebSocketServerProtocol` was expected, but received "
                f"{'Nothing' if socket is None else socket.__class__.__name__} instead"
            )
        elif socket.closed:
            raise ValueError(
                f"The websocket connection to the server passed to `listen_to_server` is not unusable; "
                f"it is not open."
            )

        if not isinstance(client, WebSocketClientProtocol):
            raise ValueError(
                f"The websocket connection to the client passed to `listen_to_server` is not unusable; "
                f"a `WebSocketClientProtocol` was expected, but received "
                f"{'Nothing' if socket is None else socket.__class__.__name__} instead"
            )
        elif client.closed:
            raise ValueError(
                f"The websocket connection to the client passed to `listen_to_server` is not unusable; "
                f"it is not open."
            )

        message_handlers: typing.Iterable[typing.Tuple[str, MESSAGE_HANDLER]] = self._get_server_message_handlers()
        operation_results: typing.Dict[str, typing.Any] = {
            name: None
            for name, handler in message_handlers
        }
        started_at: typing.Final[str] = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
        last_update: typing.Optional[str] = None
        last_handler: typing.Optional[str] = None
        message_count = 0
        try:
            async for message in socket:
                message_count += 1
                for name, handler in message_handlers:
                    result = await handler(message, socket, client, path, *args, **kwargs)
                    if result and isinstance(result, dict):
                        if operation_results.get(name) is None:
                            operation_results[name] = result
                        elif isinstance(operation_results[name], dict):
                            operation_results[name] = merge_dictionaries(operation_results[name], result)
                        elif is_collection_type(operation_results[name]):
                            operation_results[name] = [value for value in operation_results[name]] + [result]
                        else:
                            operation_results[name] = [operation_results[name], result]
                    elif result and operation_results[name] is not None:
                        if is_collection_type(operation_results[name]):
                            operation_results[name] = [value for value in operation_results[name]] + [result]
                        else:
                            operation_results[name] = [operation_results[name], result]
                    elif result:
                        operation_results[name] = result

                    last_update = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
                    last_handler = name
        except OperationComplete as complete:
            message = str(complete) or "The Server is no longer being listened to"
            return self._get_response_class()(
                success=True,
                reason="Server is no longer being listened to",
                message=message,
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except websockets.ConnectionClosedOK:
            # This is fine; the connection just closed
            return self._get_response_class()(
                success=True,
                reason=InitRequestResponseReason.ACCEPTED.name,
                message=f"Websocket connection closed",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except websockets.ConnectionClosedError as error:
            # This is fine; the connection just closed
            return self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.REJECTED.name,
                message=f"Websocket connection closed unexpectedly: {str(error)}",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "error": str(error),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except Exception as exception:
            message = f"[{get_current_function_name()}] An exception was encountered while running the request handler: " \
                      f"{str(exception)}"
            logging.error(message, exc_info=exception)
            return self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.UNKNOWN.name,
                message=message,
                data={
                    "error": str(exception),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )

    async def listen_to_client(
        self,
        socket: WebSocketServerProtocol,
        client: WebSocketClientProtocol,
        path: str,
        *args,
        **kwargs
    ) -> Response:
        """
        Listen for messages from the client

        Args:
            socket: The socket connection from this server
            client: The socket connection to the client that this communicates with
            path: The path to this handler on the server
            *args:
            **kwargs:

        Returns:
            A response reporting on the success of this operation
        """
        if not isinstance(socket, WebSocketServerProtocol):
            raise ValueError(
                f"The websocket connection to the server passed to `listen_to_client` is not unusable; "
                f"a `WebSocketServerProtocol` was expected, but received "
                f"{'Nothing' if socket is None else socket.__class__.__name__} instead"
            )
        elif socket.closed:
            raise ValueError(
                f"The websocket connection to the server passed to `listen_to_client` is not unusable; "
                f"it is not open."
            )

        if not isinstance(client, WebSocketClientProtocol):
            raise ValueError(
                f"The websocket connection to the client passed to `listen_to_client` is not unusable; "
                f"a `WebSocketClientProtocol` was expected, but received "
                f"{'Nothing' if socket is None else socket.__class__.__name__} instead"
            )
        elif client.closed:
            raise ValueError(
                f"The websocket connection to the client passed to `listen_to_client` is not unusable; "
                f"it is not open."
            )

        message_handlers: typing.Iterable[typing.Tuple[str, MESSAGE_HANDLER]] = self._get_client_message_handlers()
        operation_results: typing.Dict[str, list] = {
            name: list()
            for name, handler in message_handlers
        }
        last_update: typing.Optional[str] = None
        last_handler: typing.Optional[str] = None
        started_at = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
        message_count = 0
        try:
            async for message in client:
                message_count += 1
                for name, handler in message_handlers:
                    result = handler(message, socket, client, path, *args, **kwargs)
                    operation_results[name].append(result)
                    last_update = datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
                    last_handler = name
            return self._get_response_class()(
                success=True,
                reason="Client is no longer being listened to",
                message="Client is no longer being listened to",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except websockets.ConnectionClosedOK:
            # This is fine; the connection just closed
            return self._get_response_class()(
                success=True,
                reason=InitRequestResponseReason.ACCEPTED.name,
                message=f"Websocket connection closed",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except websockets.ConnectionClosedError as error:
            # This is fine; the connection just closed
            return self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.REJECTED.name,
                message=f"Websocket connection closed unexpectedly: {str(error)}",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z"),
                    "error": str(error),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )
        except Exception as exception:
            return self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.UNKNOWN.name,
                message=f"An exception was encountered while running the request handler: {str(exception)}",
                data={
                    "error": str(exception),
                    "results": operation_results,
                    "last_update": last_update,
                    "last_handler": last_handler,
                    "started_at": started_at,
                    "message_count": message_count
                }
            )

    def start_producing_messages(self, socket, client, path, *args, **kwargs) -> typing.List[asyncio.Task[Response]]:
        """
        Returns:
            All functions that need to act on incoming client messages
        """
        if not self._has_initialized:
            raise InitializationError(self)

        running_producers: typing.List[asyncio.Task] = list()

        for name, function in self.__producers.items():
            try:
                if not inspect.iscoroutinefunction(function):
                    raise exceptions.RegistrationError(
                        f"An invalid message handler meant to read messages from the server is present."
                        f"'{name}' ({function.__name__}) cannot be used as a registered server handler; "
                        f"only asynchronous functions (marked by `async def`) may be used"
                    )
                running_producers[name] = function(socket, client, path, *args, **kwargs)
            except:
                for task in running_producers:
                    try:
                        task.cancel(
                            f"Cancelling the producer named {task.get_name()}; "
                            f"the producer named {name} failed to start."
                        )
                    except BaseException as cancel_exception:
                        logging.error(
                            f"Could not cancel a producer task after a launch failed: {str(cancel_exception)}"
                        )
                raise

        # Find all possible handler functions via decorator inspection
        producer_functions: typing.Dict[str, MESSAGE_PRODUCER] = self._get_dynamic_functions(
            decorators.PRODUCER_MESSAGE_HANDLER_ATTRIBUTE
        )

        # Make sure all identified functions are awaitable so that they can properly handle their sockets
        for name, function in producer_functions.items():
            try:
                if name in running_producers:
                    raise Exception(
                        f"Cannot start a new coroutine to produce messages; there is already one named {name}"
                    )

                if not inspect.iscoroutinefunction(function):
                    raise exceptions.RegistrationError(
                        f"self.{name} cannot be used as a producer; "
                        f"only asynchronous functions (marked by `async def`) may be used"
                    )

                running_producers.append(
                    asyncio.create_task(function(socket, client, path, *args, **kwargs), name=name)
                )
            except:
                for task in running_producers:
                    try:
                        task.cancel(
                            f"Cancelling the producer named {task.get_name()}; "
                            f"the producer named {name} failed to start."
                        )
                    except BaseException as cancel_exception:
                        logging.error(
                            f"Could not cancel a producer task after a launch failed: {str(cancel_exception)}"
                        )
                raise
        return running_producers

    async def handle_request(
        self,
        request: AbstractInitRequest,
        socket: WebSocketServerProtocol = None,
        path: str = None,
        **kwargs
    ) -> Response:
        """
        Run all request handlers on the incoming request

        Args:
            request: The request that precipitated the need for a handler
            socket: The socket through which the request came through
            path: The path to the socket on the server
            **kwargs:

        Returns:
            A response summarizing the all operations
        """
        if not self._has_initialized:
            raise InitializationError(self)

        try:
            async with websockets.connect(self.service_url, **self._client_arguments) as client:
                connection_data = json.dumps({
                    "event": f"A connection to {self.get_target_service()} has been established."
                })
                await socket.send(connection_data)

                # Start async functions that will listen to the server and client
                tasks: typing.List[asyncio.Task] = self.start_producing_messages(socket, client, path)
                tasks.extend([
                    asyncio.create_task(self.listen_to_server(socket, client, path), name="listen_to_server"),
                    asyncio.create_task(self.listen_to_client(socket, client, path), name="listen_to_client")
                ])

                try:
                    # If this is supposed to handle concurrent reading and sending, you don't want one running while
                    # another has finished, so close them all down
                    await asyncio.wait(
                        fs=tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                except BaseException as exception:
                    for task in tasks:
                        if not (task.done() or task.cancelled()):
                            try:
                                message = f"Cancelling '{task.get_name()}'; an error occurred when waiting for tasks " \
                                          f"to run. {str(exception)}"
                                task.cancel(message)
                            except BaseException as cancel_exception:
                                logging.error(
                                    f"Failed to cancel an incomplete task: {task.get_name()}; {str(cancel_exception)}"
                                )
                    raise

                # Cancel all tasks that haven't finished
                for task in tasks:
                    try:
                        if not (task.done() or task.cancelled()):
                            task.cancel(f"Cancelling '{task.get_name()}'; operations have concluded")
                    except BaseException as exception:
                        logging.error(
                            f"Failed to cancel an incomplete task: {task.get_name()}; {str(exception)}"
                        )

                return await self._generate_response(tasks)
        except websockets.ConnectionClosedOK:
            # This is fine; the connection just closed
            return self._get_response_class()(
                success=True,
                reason=InitRequestResponseReason.ACCEPTED.name,
                message=f"Websocket connection closed",
                data={
                    "closed_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")
                }
            )
        except websockets.ConnectionClosedError as error:
            # This is fine; the connection just closed
            return self._get_response_class()(
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
            return self._get_response_class()(
                success=False,
                reason=InitRequestResponseReason.UNKNOWN.name,
                message=message,
                data={
                    "error": str(exception)
                }
            )

    async def end_operations(
        self,
        message: typing.Union[str, bytes],
        socket: WebSocketServerProtocol,
        client: WebSocketClientProtocol,
        *args,
        **kwargs
    ):
        """
        Ends all current handling of messages coming through the socket

        The overall loop ends when one function returns, so breaking the loop here will close all handling.

        Args:
            message: The message that came triggered the function
            socket: The socket that messages come through
            client:
            *args:
            **kwargs:
        """
        try:
            payload = json.loads(message)
            payload = payload.get("event", "")
        except:
            payload = message

        if isinstance(payload, str) and payload.upper() == CLOSE_MESSAGE:
            raise OperationComplete("Request received to disconnect.")


def explain_failures(failures: typing.List[Failure]) -> str:
    """
    Generates an explanation as to why tasks may have failed

    Args:
        failures: Metadata from failed tasks

    Returns:
        A description of why a series of tasks failed
    """
    explanation = ""
    number_of_failures = len(failures)
    individual_failure_messages = [str(failure) for failure in failures]

    if number_of_failures == 1:
        explanation = individual_failure_messages[0]
    elif number_of_failures == 2:
        explanation = f"{individual_failure_messages[0]} and {individual_failure_messages[1]}"
    elif number_of_failures >= 3:
        explanation = ", ".join(individual_failure_messages[:-1]) + f", and {individual_failure_messages[-1]}"

    return explanation

