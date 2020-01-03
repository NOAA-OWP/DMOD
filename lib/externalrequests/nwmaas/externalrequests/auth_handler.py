import logging

from nwmaas.access import Authenticator, Authorizer, DummyAuthUtil
from nwmaas.communication import AbstractRequestHandler, FailedSessionInitInfo, Session, SessionInitFailureReason, \
    SessionInitMessage, SessionInitResponse, SessionManager
from typing import Optional

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class InnerSessionAuthUtil:
    """
    "Private" or "inner" utility/helper class for the :class:`AuthHandler` to use for creating and authenticating
    sessions.

    The expectation is that one single instance will be used for each attempt to get a new session; i.e., for every
    invocation of the ``handle_request()`` method.

    Class works largely via a set of private attributes and lazily-instantiating properties.  The logic to instantiate
    ``session``, ``newly_created``, and ``failure_info`` (the three most important) is centralized in one private method
    named :meth:`_auth_session`.
    """

    _DUMMY_AUTH_UTIL = DummyAuthUtil()

    def __init__(self, session_init_message: SessionInitMessage, session_ip_addr: str, session_manager: SessionManager):
        self.username = session_init_message.username
        self.user_secret = session_init_message.user_secret
        self.session_ip_addr = session_ip_addr
        self.session_manager = session_manager

        # FIXME: replace with real implementations of these interfaces
        self._authenticator: Authenticator = self._DUMMY_AUTH_UTIL
        self._authorizer: Authorizer = self._DUMMY_AUTH_UTIL

        self._session = None
        self._newly_created = False
        self._failure_info = None

        self._is_authenticated = None
        self._is_authorized = None
        self._is_needs_new_session = None

    def _auth_session(self):
        """
        Perform the attempt to get an authenticated, authorized session for making requests from an external client.

        Note that this method will only run if the ``_session`` and ``_failure_info`` attributes are None, and the
        method is guaranteed to set exactly one of those two attributes with an object of the appropriate type.
        """
        # Bail here unless running for the first time for this instance
        if self._session is not None or self._failure_info is not None:
            return

        # Set this as the default, and override in logic below for appropriate case
        # Leave as None though when instantiating to avoid case where this is set without auth being tried
        self._newly_created = False

        if self.is_authenticated and self.is_authorized and self.is_needs_new_session:
            self._newly_created = True
            try:
                self._session = self.session_manager.create_session(ip_address=self.session_ip_addr,
                                                                    username=self.username)
            except Exception as e:
                details = 'The session manager encountered a {} when attempting to create a new session: {}'.format(
                    e.__class__.__name__, str(e))
                self._failure_info = FailedSessionInitInfo(user=self.username,
                                                           reason=SessionInitFailureReason.SESSION_MANAGER_FAIL,
                                                           details=details)
        elif self.is_authenticated and self.is_authorized:
            # FIXME: when this is changed, make sure to properly create the init failure object as needed
            # self._session = FIXME: lookup existing somehow
            pass
        elif self.is_authenticated:   # implies user was not authorized
            self._failure_info = FailedSessionInitInfo(user=self.username,
                                                       reason=SessionInitFailureReason.USER_NOT_AUTHORIZED,
                                                       details='Authenticated user not authorized for access')
        else:  # implies user was not authenticated
            self._failure_info = FailedSessionInitInfo(user=self.username,
                                                       reason=SessionInitFailureReason.AUTHENTICATION_DENIED,
                                                       details='User was not authenticated')

    # FIXME: move this to session handler class instead
    async def _check_existing_session(self, username: str) -> bool:
        """
        Check whether a user with the given username already has an active session over which model requests can be
        made, implying (assuming appropriate auth) the user requires a new session.

        Note that this method does not take into account whether such a user is currently authenticated or whether such
        a user is authorized to be granted sessions.  Further, it does not retrieve any existing session.  It only tests
        whether there is an active session for the user.

        Parameters
        ----------
        username : str
            the username of the user for which an existing useable session is being checked

        Returns
        -------
        ``True`` if the represented user already has an existing, active session over which model requests can be made,
        or ``False`` otherwise
        """
        # FIXME: implement check for existing useable session; for now, there never is one
        # FIXME: note that this will require finishing the existing-session-lookup case in AuthHandler._auth_session()
        return False

    @property
    def failure_info(self) -> Optional[FailedSessionInitInfo]:
        if self._failure_info is None and self._session is None:
            self._auth_session()
        return self._failure_info

    @property
    def is_authenticated(self):
        if self._is_authenticated is None:
            self._is_authenticated = await self._authenticator.authenticate(self.username, self.user_secret)
        return self._is_authenticated

    @property
    def is_authorized(self):
        if self._is_authorized is None:
            self._is_authorized = self.is_authenticated and await self._authorizer.check_authorized(self.username)
        return self._is_authorized

    @property
    def is_needs_new_session(self):
        if self._is_needs_new_session is None:
            self._is_needs_new_session = self.is_authorized and not(await self._check_existing_session(self.username))
        return self._is_needs_new_session

    @property
    def newly_created(self) -> bool:
        if self._newly_created is None:
            self._auth_session()
        return self._newly_created

    @property
    def session(self) -> Optional[Session]:
        if self._failure_info is None and self._session is None:
            self._auth_session()
        return self._session


class AuthHandler(AbstractRequestHandler):

    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    async def handle_request(self, request: SessionInitMessage, **kwargs) -> SessionInitResponse:
        """
        Handle the given request for a new session and return the resulting response.

        Parameters
        ----------
        request: SessionInitMessage
            A ``SessionInitMessage`` message instance with the credentials for attempting to create a new session.

        Other Parameters
        ----------
        client_ip: str
            The IP address (or hostname) of the client requesting a new session.

        Returns
        -------
        response: SessionInitResponse
            An appropriate ``SessionInitResponse`` object, containing the created ``Session`` object if successful.
        """
        auth_util = InnerSessionAuthUtil(session_init_message=request,
                                         session_ip_addr=kwargs['client_ip'],
                                         session_manager=self._session_manager)

        if auth_util.session is not None:
            session_txt = 'new session' if auth_util.newly_created else 'session'
            logging.debug('*************** Got {} for auth message: {}'.format(session_txt, str(auth_util.session)))
            # TODO: move this logic (below 2 lines) to whatever uses this and has the session (i.e., some service)
            #result = await self.register_websocket_session(websocket, session)
            #logging.debug('************************* Attempt to register session-websocket result: {}'.format(str(result)))
            return SessionInitResponse(success=True, reason='Successful Auth', data=auth_util.session)
        else:
            msg = 'Unable to create or find authenticated user session from request'
            return SessionInitResponse(success=False, reason='Failed Auth', message=msg, data=auth_util.failure_info)
