import typing
import random
import secrets
import asyncio
import logging

import websockets
from websockets.server import WebSocketServerProtocol

from .. import registered_interface
from .. import message
from .. import session

from . import session_manager


logging.warning(
    "The example RegisteredWebSocket module has been loaded; "
    "this should not be used in any capacity other than for source code reference."
)


class ExampleRegisteredInterface(registered_interface.RegisteredWebSocketInterface):
    """
    An example interface used to demonstrate how to create a handler for a registered interface
    """
    _field1: int
    _field2: int
    _field3: dict

    def __init__(self, listen_host='', port=3012, ssl_dir=None, cert_pem=None, priv_key_pem=None, *args, **kwargs):
        super().__init__(listen_host, port, ssl_dir, cert_pem, priv_key_pem, *args, **kwargs)
        raise NotImplementedError(
            f"{self.__class__.__name__} is for source code example use only; do not use for any other purpose."
        )

    def _get_registered_websocket_functions(self) -> typing.Sequence[registered_interface.WEBSOCKET_HANDLER]:
        return [
            self.echo,
            self.emit_message
        ]

    def _get_initialization_functions(self) -> typing.Sequence[registered_interface.VARIABLE_CALLABLE]:
        functions = list(super()._get_initialization_functions())
        functions.extend([
            self._initialize_fields
        ])
        return functions

    def _initialize_fields(self, listen_host, port, *args, **kwargs):
        self._field1 = listen_host
        self._field2 = port
        self._field3 = {
            "this": "is",
            "an": "example"
        }

    @classmethod
    def get_parseable_request_types(cls) -> typing.List[typing.Type[message.AbstractInitRequest]]:
        return list()

    async def echo(self, websocket: WebSocketServerProtocol, path):
        async for message in websocket:
            print(message)

    async def emit_message(self, websocket: WebSocketServerProtocol, path):
        minimum_wait_seconds = 2
        maximum_wait_seconds = 10

        try:
            while True:
                wait_seconds = random.randint(minimum_wait_seconds, maximum_wait_seconds)
                await asyncio.sleep(wait_seconds)

                message = f"The secret code is: {secrets.token_urlsafe(8)}"
                await websocket.send(message)
        except websockets.ConnectionClosed as connection_closed:
            print(f"The connection has been closed; {str(connection_closed)}")


class ExampleRegisteredSessionInterface(
    registered_interface.RegisteredWebSocketInterface,
    registered_interface.SessionInterfaceMixin
):
    """
    An example interface used to demonstrate how to create a handler for a registered interface
    supported by session data
    """
    __socket_map: typing.Dict[session.Session, WebSocketServerProtocol]
    __session_manager: session.SessionManager

    def __init__(self, listen_host='', port=3012, ssl_dir=None, cert_pem=None, priv_key_pem=None, *args, **kwargs):
        super().__init__(listen_host, port, ssl_dir, cert_pem, priv_key_pem, *args, **kwargs)
        raise NotImplementedError(
            f"{self.__class__.__name__} is for source code example use only; do not use for any other purpose."
        )

    @property
    def _session_socket_map(self) -> typing.Dict[session.Session, WebSocketServerProtocol]:
        return self.__socket_map

    @property
    def session_manager(self):
        return self.__session_manager

    def _get_registered_websocket_functions(self) -> typing.Sequence[registered_interface.WEBSOCKET_HANDLER]:
        return [
            self.echo,
            self.emit_message
        ]

    def _get_initialization_functions(self) -> typing.Sequence[registered_interface.VARIABLE_CALLABLE]:
        return [
            self._initialize_session_handling
        ]

    def _initialize_session_handling(self, *args, **kwargs):
        self.__session_manager = session_manager.ExampleSessionManager()
        self.__socket_map = dict()

    @classmethod
    def get_parseable_request_types(cls) -> typing.List[typing.Type[message.AbstractInitRequest]]:
        return list()

    async def echo(self, websocket: WebSocketServerProtocol, path):
        async for message in websocket:
            print(message)

    async def emit_message(self, websocket: WebSocketServerProtocol, path):
        minimum_wait_seconds = 2
        maximum_wait_seconds = 10

        try:
            while True:
                wait_seconds = random.randint(minimum_wait_seconds, maximum_wait_seconds)
                await asyncio.sleep(wait_seconds)

                message = f"The secret code is: {secrets.token_urlsafe(8)}"
                await websocket.send(message)
        except websockets.ConnectionClosed as connection_closed:
            print(f"The connection has been closed; {str(connection_closed)}")
