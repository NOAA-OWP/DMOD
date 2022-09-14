#!/usr/bin/env python3
import typing

from websockets import WebSocketServerProtocol
from websockets import WebSocketClientProtocol

from ..websocket_interface import WebSocketInterface
from ..request_handler import AbstractRequestHandler

from ..message import Message
from ..message import Response
from ..message import AbstractInitRequest


VARIABLE_CALLABLE = typing.Callable[[typing.Tuple, typing.Dict[str, typing.Any]], typing.NoReturn]
ADDITIONAL_PARAMETER_PROVIDER = typing.Callable[
    [WebSocketInterface, typing.Optional[WebSocketServerProtocol]],
    typing.Union[typing.Dict[str, typing.Any], typing.Awaitable[typing.Dict[str, typing.Any]]]
]
HANDLER_FUNCTION = typing.Callable[
    [Message, WebSocketServerProtocol, typing.Dict[str, typing.Any]],
    typing.Awaitable[Response]
]
"""
Alias for an async function that takes a DMOD Message, and a websocket server connection and returns a DMOD Response
"""

MESSAGE_HANDLER_FUNCTION = typing.Callable[
    [AbstractRequestHandler, Message, WebSocketServerProtocol, WebSocketClientProtocol, str, typing.Optional[typing.Any]],
    typing.Awaitable[Response]
]

MESSAGE_TYPES = typing.Set[typing.Type[AbstractInitRequest]]
