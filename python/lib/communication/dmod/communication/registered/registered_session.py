"""
Provides the base class for Session interface mixins that allow session management to be added to classes via mixin
rather than direct addition
"""
import abc
import typing
import logging

from uuid import uuid1

from websockets import WebSocketServerProtocol

from dmod.core import decorators

from ..session import Session
from ..session import SessionManager
from ..session import SessionInitMessage
from ..session import SessionInitResponse
from ..session import FailedSessionInitInfo


class SessionInterfaceMixin(abc.ABC):
    """
    Base class for mixins that allow Session management to be added functionality
    """
    @decorators.initializer
    def _add_socket_map(self, *args, **kwargs):
        if not hasattr(self, "_socket_map"):
            setattr(self, "_socket_map", dict())

    @property
    def _session_socket_map(self) -> typing.Dict[WebSocketServerProtocol, Session]:
        if self._socket_map is None:
            self._socket_map = dict()

        return self._socket_map

    @property
    @abc.abstractmethod
    def session_manager(self) -> SessionManager:
        pass

    @property
    @abc.abstractmethod
    def authorization_handler(self):
        pass

    @decorators.socket_handler(**{decorators.MESSAGE_TYPE_ATTRIBUTE: SessionInitMessage})
    async def initialize_session(
        self,
        request_message: SessionInitMessage,
        socket: WebSocketServerProtocol,
        **kwargs
    ) -> SessionInitResponse:
        """
        Create a session for a given request and websocket

        Args:
            request_message: The message that asked to create session data
            socket: The socket to create session data for
            **kwargs:

        Returns:
            A response detailing the success or failure of an attempt to initialize a session
        """
        client_ip: str = socket.remote_address[0]

        if self.authorization_handler:
            response = await self.authorization_handler.handle_request(request_message, client_ip)
        else:
            generated_user = str(uuid1())
            session = self.session_manager.create_session(ip_address=client_ip, username=generated_user)
            if session:
                message = f"Authorization is not enabled for this session handler. " \
                          f"Created a session for user named '{generated_user}'"
                response = SessionInitResponse(
                    success=True,
                    reason="Created Unauthorized Session",
                    data=session,
                    message=message
                )
            else:
                message = f"Authorization is not enabled for this session handler. " \
                          f"Could not create a session for user named '{generated_user}'"
                response = SessionInitResponse(
                    success=False,
                    reason="Failed to create an unauthorized Session",
                    data=FailedSessionInitInfo(generated_user),
                    message=message
                )

        if response is not None and response.success:
            session = response.data
            result = await self.register_websocket_session(socket, session)
            logging.debug(f'************************* Attempt to register session-websocket: {str(result)}')

        return response

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
        self._session_socket_map[websocket] = session

    async def unregister_websocket_session(self, socket: WebSocketServerProtocol):
        """
        Unregister the known relationship of a session keyed to a specific websocket.

        Parameters
        ----------
        socket
        """
        session: typing.Optional[Session] = self._session_socket_map.get(socket)
        if session is None or session.session_id is None:
            return
        else:
            logging.debug('************* Session Arg: ({}) {}'.format(session.__class__.__name__, str(session)))
            for session_key in self._session_socket_map:
                logging.debug('************* Knowns Session: ({}) {}'.format(session.__class__.__name__, str(session_key)))
            if session in self._session_socket_map:
                logging.debug('************* Popping websocket for session {}'.format(str(session)))
                self._session_socket_map.pop(socket)
