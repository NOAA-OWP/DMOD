"""
Provides common type aliases
"""
import typing

from websockets import WebSocketCommonProtocol

from dmod.communication import Response
from dmod.communication import FieldedMessage

from .producer import ProducerType

MESSAGE_HANDLER = typing.Callable[
    [
        typing.Union[str, bytes, dict],
        WebSocketCommonProtocol,
        WebSocketCommonProtocol,
        str,
        typing.Tuple[typing.Any],
        typing.Dict
    ],
    typing.Coroutine
]
"""
An asynchronous function that takes a raw socket message, a source socket, a target socket, its path, and along with
any number of extra positional and keyword arguments
"""

TYPED_MESSAGE_HANDLER = typing.Callable[
    [FieldedMessage, WebSocketCommonProtocol, WebSocketCommonProtocol, str, typing.Optional[typing.Any]],
    typing.Coroutine
]
"""
An asynchronous function that takes a class based message, a source socket, a target socket, its path, and along with
any number of extra positional and keyword arguments
"""

MESSAGE_PRODUCER = typing.Callable[
    [WebSocketCommonProtocol, WebSocketCommonProtocol, str, typing.Optional[typing.Any]],
    typing.Coroutine[typing.Any, typing.Any, Response]
]
"""
An asynchronous function that can send messages through both a source and target socket.
"""

HANDLER_ROUTING_TABLE = typing.Dict[typing.Type[FieldedMessage], typing.List[TYPED_MESSAGE_HANDLER]]
"""
A mapping between a type of message and all functions that may operate on it
"""


class HandlerProtocol(typing.Protocol):
    """
    Protocol used to grant access to handler functions in mixins
    """

    def add_producer(self, producer: ProducerType):
        """
        Add a function that produces messages to send through the target and/or server connections without their
        prompting

        Args:
            producer: The function that will produce messages
        """
        ...

    def add_source_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the server connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        ...

    def add_source_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the server connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        ...

    def get_source_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for source messages
        """
        ...

    def add_target_message_handler(self, handler_name: str, handler: MESSAGE_HANDLER):
        """
        Add a basic handler that will act on a string that arrives through the client connection

        Args:
            handler_name: The name of the handler to add
            handler: The handler to add
        """
        ...

    def add_target_handler_route(self, message_type: typing.Type[FieldedMessage], handler: TYPED_MESSAGE_HANDLER):
        """
        Adds a typed message handler that acts on specific messages coming through the client connection

        Args:
            message_type: The type of message that the handler expects
            handler: The function that acts on the given type of message
        """
        ...

    def get_target_handler_routes(self) -> typing.Dict[typing.Type[FieldedMessage], typing.Iterable[TYPED_MESSAGE_HANDLER]]:
        """
        Get all typed handlers for messages from the target
        """
        ...

    def add_initial_message_handler(self, handler: MESSAGE_HANDLER):
        """
        Add a message handler that will attempt to act on a message when this handler first accepts a connection

        Args:
            handler: A function that might handle a message
        """
        ...

    def parse_socket_input(self, socket_input: typing.Union[str, bytes]) -> typing.Union[str, FieldedMessage, bytes]:
        """
        Convert the passed socket data into either a concrete message or just a string or byte

        Args:
            socket_input: The data that arrived through a socket

        Returns:
            A deserialized version of the socket data
        """
        ...
