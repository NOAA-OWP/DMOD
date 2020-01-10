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
    # FIXME: replace with real implementations of these interfaces
    _DEFAULT_AUTHENTICATOR = _DUMMY_AUTH_UTIL
    _DEFAULT_AUTHORIZER = _DUMMY_AUTH_UTIL

    def __init__(self, session_init_message: SessionInitMessage, session_ip_addr: str, session_manager: SessionManager,
                 authenticator: Authenticator = None, authorizer: Authorizer = None):
        self.username = session_init_message.username
        self.user_secret = session_init_message.user_secret
        self.session_ip_addr = session_ip_addr
        self.session_manager = session_manager

        self._authenticator: Authenticator = authenticator
        self._authorizer: Authorizer = authorizer

        # Initialize with defaults if needed
        if self._authenticator is None:
            self._authenticator: Authenticator = self._DEFAULT_AUTHENTICATOR

        if self._authorizer is None:
            self._authorizer: Authorizer = self._DEFAULT_AUTHORIZER

        self._session = None
        self._newly_created = False
        self._failure_info = None

        self._is_authenticated = None
        self._is_authorized = None
        self._is_needs_new_session = None

    async def _auth_session(self):
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

        if await self.is_authenticated and await self.is_authorized and await self.is_needs_new_session:
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
        elif await self.is_authenticated and await self.is_authorized:
            # FIXME: when this is changed, make sure to properly create the init failure object as needed
            # self._session = FIXME: lookup existing somehow
            pass
        elif await self.is_authenticated:   # implies user was not authorized
            self._failure_info = FailedSessionInitInfo(user=self.username,
                                                       reason=SessionInitFailureReason.USER_NOT_AUTHORIZED,
                                                       details='Authenticated user not authorized for access')
        else:  # implies user was not authenticated
            self._failure_info = FailedSessionInitInfo(user=self.username,
                                                       reason=SessionInitFailureReason.AUTHENTICATION_DENIED,
                                                       details='User was not authenticated')

    @property
    async def failure_info(self) -> Optional[FailedSessionInitInfo]:
        if self._failure_info is None and self._session is None:
            await self._auth_session()
        return self._failure_info

    @property
    async def is_authenticated(self):
        if self._is_authenticated is None:
            self._is_authenticated = await self._authenticator.authenticate(self.username, self.user_secret)
        return self._is_authenticated

    @property
    async def is_authorized(self):
        if self._is_authorized is None:
            self._is_authorized = await self.is_authenticated and await self._authorizer.check_authorized(self.username)
        return self._is_authorized

    @property
    async def is_needs_new_session(self):
        if self._is_needs_new_session is None:
            self._is_needs_new_session = await self.is_authorized and not (
                self.session_manager.lookup_session_by_username(self.username))
        return self._is_needs_new_session

    @property
    async def newly_created(self) -> bool:
        if self._newly_created is None:
            await self._auth_session()
        return self._newly_created

    @property
    async def session(self) -> Optional[Session]:
        if self._failure_info is None and self._session is None:
            await self._auth_session()
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
            return SessionInitResponse(success=True, reason='Successful Auth', data=await auth_util.session)
        else:
            msg = 'Unable to create or find authenticated user session from request'
            return SessionInitResponse(success=False, reason='Failed Auth', message=msg,
                                       data=await auth_util.failure_info)
