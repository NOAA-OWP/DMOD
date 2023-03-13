"""
Defines a base class to use for websocket consumers that provide more concrete and defined access to scope as well
as an identifier for operations
"""
import typing
import abc
import inspect

from asgiref.sync import async_to_sync, AsyncToSync
from django.urls import re_path

from channels.generic.websocket import AsyncWebsocketConsumer

from dmod.core import common

from maas_experiment import logging as common_logging

from .scope import ConcreteScope
from .common import make_websocket_message


CONSUMER_HANDLER = typing.Callable[["SocketConsumer"], typing.Optional[typing.Coroutine]]


class HandlerAndArgs(typing.TypedDict):
    kwargs: typing.Dict[str, typing.Any]
    handler: CONSUMER_HANDLER


def should_include_self(func: typing.Callable) -> bool:
    parameters = inspect.signature(func).parameters

    if len(parameters) == 0:
        return False

    required_parameters = [
        parameter
        for parameter in parameters.values()
        if parameter.kind not in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL)
           and parameter.default == parameter.empty
    ]

    if len(required_parameters) == 0:
        return False

    if len(required_parameters) > 1:
        raise Exception("Event handlers may only take one required parameter")

    parameter = required_parameters[0]

    if parameter.annotation == parameter.empty:
        raise Exception("The required parameter for event handlers must be annotated")

    if isinstance(parameter.annotation, str):
        if parameter.annotation not in globals():
            raise Exception(
                f"Cannot check if the parameter for this handler is valid; the type '{parameter.annotation}' "
                f"is not in the current context."
            )

        parameter_class = globals()[parameter.annotation]
        try:
            class_chain = inspect.getmro(parameter_class)
            if AsyncWebsocketConsumer in class_chain:
                return True
            else:
                raise Exception(f"The parameter for this handler was a  '{type(parameter_class)}'")
        except Exception as e:
            raise Exception("The parameter of this handler must be a subclass of AsyncWebsocketConsumer") from e
    else:
        try:
            class_chain = inspect.getmro(parameter.annotation)
            if AsyncWebsocketConsumer in class_chain:
                return True
            else:
                raise Exception(f"The parameter for this handler was a  '{type(parameter.annotation)}'")
        except Exception as e:
            raise Exception("The parameter of this handler must be a subclass of AsyncWebsocketConsumer") from e


class SocketConsumer(AsyncWebsocketConsumer, abc.ABC):
    """
    A base websocket consumer
    """
    @classmethod
    def make_path(cls, pattern: str, name: str = None, **kwargs):
        return re_path(
            route=pattern,
            view=cls.as_asgi(**kwargs),
            name=name
        )

    def __init__(
        self,
        connect_handlers: typing.Iterable[CONSUMER_HANDLER] = None,
        disconnect_handlers: typing.Iterable[CONSUMER_HANDLER] = None,
        *args,
        **kwargs
    ):
        """
        Constructor
        """
        super().__init__(*args, **kwargs)
        self.__identifier = kwargs.get("identifier", common.generate_identifier())
        self.__scope: typing.Optional[ConcreteScope] = None
        self.__members: typing.Optional[typing.Dict[str, typing.Any]] = None
        self._attributes: typing.Dict[str, typing.Any] = kwargs.copy()
        self._tell_client: AsyncToSync = async_to_sync(self.send)

        self.__connect_handlers: typing.List[HandlerAndArgs] = list()

        for handler in connect_handlers or list():
            self.add_connect_handler(handler)

        self.__disconnect_handlers: typing.List[HandlerAndArgs] = list()

        for handler in disconnect_handlers or list():
            self.add_disconnect_handler(handler)

    def add_connect_handler(self, handler: CONSUMER_HANDLER):
        self.__add_handler(handler, self.__connect_handlers)

    def add_disconnect_handler(self, handler: CONSUMER_HANDLER):
        self.__add_handler(handler, self.__disconnect_handlers)

    def __add_handler(self, handler: CONSUMER_HANDLER, handler_collection: typing.MutableSequence[HandlerAndArgs]):
        if handler is None:
            return
        if not (inspect.ismethod(handler) or inspect.isfunction(handler) or inspect.iscoroutinefunction(handler)):
            raise Exception(f"A {type(handler)} object cannot be used as a connection handler.")

        include_self = should_include_self(handler)

        kwargs = dict()

        if include_self:
            parameters = inspect.signature(handler).parameters
            parameter_name = [
                parameter_name
                for parameter_name, parameter in parameters.items()
                if parameter.kind not in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL)
            ][0]
            kwargs[parameter_name] = self

        handler_collection.append(
            {
                "kwargs": kwargs,
                "handler": handler
            }
        )

    @property
    def connect_handlers(self) -> typing.Iterable[HandlerAndArgs]:
        return self.__connect_handlers.copy()

    @property
    def disconnect_handlers(self) -> typing.Iterable[HandlerAndArgs]:
        return self.__disconnect_handlers.copy()

    @property
    def identifier(self) -> str:
        """
        A highly likely identifier for this particular instance of the proxy
        """
        return self.__identifier

    @property
    def scope_data(self) -> typing.Optional[ConcreteScope]:
        """
        Returns:
            A scope object representing the consumer's internal scope dictionary
        """
        if self.__scope is None and not hasattr(self, "scope"):
            return None

        if self.__scope is None:
            self.__scope = ConcreteScope(self.scope)

        return self.__scope

    @property
    def _members(self) -> typing.Dict[str, typing.Any]:
        if self.__members is None:
            def member_is_valid(member: typing.Any):
                if inspect.isfunction(member) or inspect.ismethod(member) or inspect.iscoroutinefunction(member):
                    return False

                if inspect.isawaitable(member):
                    return False

                if hasattr(member, "__name__") and member.__name__.startswith("_"):
                    return False

                return True

            self.__members = {
                name: value
                for name, value in inspect.getmembers(self, member_is_valid)
            }

        return self.__members

    @abc.abstractmethod
    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs):
        """
        Processes messages received via the socket.

        Called when the other end of the socket sends a message

        Args:
            text_data: Text data sent over the socket
            bytes_data: Bytes data sent over the socket
            **kwargs:
        """
        ...

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        if key in self._attributes:
            return self._attributes.get(key)

        if key in self._members:
            return self._members.get(key)

        if key in self.__scope:
            return self.__scope.get(key)

        return default

    def set(self, key: str, value: typing.Any) -> "SocketConsumer":
        self._attributes[key] = value
        return self

    async def connect(self):
        await self.__call_handlers(self.__connect_handlers)
        await self.accept()

    async def disconnect(self, close_code):
        await self.__call_handlers(self.__disconnect_handlers)

    async def __call_handlers(self, handler_collection: typing.Iterable[HandlerAndArgs]):
        for handler_and_args in handler_collection:
            try:
                result = handler_and_args.get("handler")(**handler_and_args.get("kwargs"))

                while result is not None and inspect.isawaitable(result):
                    result = await result
            except Exception as e:
                common_logging.error(
                    f"Could not complete execution of disconnect handler '{str(handler_and_args.get('handler'))}'"
                )

    async def send_message(self, result, **kwargs):
        """
        Formats a message in such a way that it is ready to send through a socket to a client

        Args:
            result: The data to send to a client
            **kwargs:
        """
        if isinstance(result, bytes):
            result = result.decode()

        message = make_websocket_message(
            event=kwargs.get("event"),
            response_type=kwargs.get("response_type"),
            data=result
        )
        await self.channel_layer.group_send(message)

    def __str__(self):
        return f"{self.__class__.__name__} {self.identifier}"

    def __repr__(self):
        return self.__str__()
