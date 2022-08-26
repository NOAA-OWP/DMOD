import logging
import random
import typing
import inspect
import abc
import secrets
import asyncio

from argparse import ArgumentParser

import websockets

from websockets.server import WebSocketServerProtocol

from . import AbstractInitRequest
from .websocket_interface import WebSocketInterface
from .session import Session, SessionInitMessage


VARIABLE_CALLABLE = typing.Callable[[typing.Tuple, typing.Dict[str, typing.Any]], typing.NoReturn]
WEBSOCKET_HANDLER = typing.Callable[[WebSocketServerProtocol, str], typing.NoReturn]


class SessionInterfaceMixin(abc.ABC):
    @property
    @abc.abstractmethod
    def _session_socket_map(self) -> typing.Dict[Session, WebSocketServerProtocol]:
        ...

    @property
    @abc.abstractmethod
    def session_manager(self):
        pass

    def _lookup_session_by_secret(self, secret: str) -> typing.Optional[Session]:
        """
        Search for the :obj:`Session` instance with the given session secret value.

        Parameters
        ----------
        secret

        Returns
        -------
        Optional[Session]
            The session from the sessions-to-websockets mapping having the given secret, or None
        """
        return self.session_manager.lookup_session_by_secret(session_secret=secret)

    async def register_websocket_session(self, websocket: WebSocketServerProtocol, session: Session):
        """
        Register the known relationship of a session keyed to a specific websocket.

        Parameters
        ----------
        websocket
        session
        """
        self._session_socket_map[session] = websocket

    async def unregister_websocket_session(self, session: Session):
        """
        Unregister the known relationship of a session keyed to a specific websocket.

        Parameters
        ----------
        websocket
        session
        """
        if session is None or session.session_id is None:
            return
        else:
            logging.debug('************* Session Arg: ({}) {}'.format(session.__class__.__name__, str(session)))
            for session_key in self._session_socket_map:
                logging.debug('************* Knowns Session: ({}) {}'.format(session.__class__.__name__, str(session_key)))
            if session in self._session_socket_map:
                logging.debug('************* Popping websocket for session {}'.format(str(session)))
                self._session_socket_map.pop(session)


class RegisteredWebSocketInterface(WebSocketInterface, abc.ABC):
    """
    A websocket interface implementation that routes logic through designated initializers, consumers, and producers
    """
    def __init__(self, listen_host='', port=3012, ssl_dir=None, cert_pem=None, priv_key_pem=None, *args, **kwargs):
        super().__init__(listen_host, port, ssl_dir, cert_pem, priv_key_pem, *args, **kwargs)
        self._initialize(listen_host, port, ssl_dir, cert_pem, priv_key_pem, *args, **kwargs)

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
        return list()

    @abc.abstractmethod
    def _get_registered_websocket_functions(self) -> typing.Sequence[WEBSOCKET_HANDLER]:
        """
        Returns:
            All functions that have been registered for the use of the dedicated websocket
        """
        ...

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Assigns the websocket to each producer and consumer

        Args:
            websocket: The socket to communicate through
            path:
        """
        registered_executions = [
            registered_function(websocket, path)
            for registered_function in self._get_registered_websocket_functions()
        ]
        registered_functions = [
            asyncio.create_task(execution)
            for execution in registered_executions
            if isinstance(execution, typing.Coroutine)
        ]

        complete_tasks, pending_tasks = await asyncio.wait(
            fs=registered_functions,
            loop=self.loop,
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending_tasks:
            task.cancel()

