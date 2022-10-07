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

MESSAGE_TYPES = typing.Set[typing.Type[AbstractInitRequest]]
