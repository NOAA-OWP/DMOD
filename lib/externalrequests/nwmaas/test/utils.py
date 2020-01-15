import datetime
from typing import Any, Optional

from nwmaas.communication import FullAuthSession
from ..externalrequests.auth_handler import Authenticator, Authorizer, SessionManager


class SucceedTestAuthUtil(Authenticator, Authorizer):
    """
    A test class implementing ``Authenticator`` and ``Authorizer`` that always returns a user is authenticated or is
    authorized.

    For the :meth:`get_authorized_types` method, a simple empty list is returned, signifying access of the default level
    only (which for this is still implicitly the equivalent of 'all').
    """

    async def authenticate(self, username: str, secret: str) -> bool:
        return True

    async def check_authorized(self, username: str, access_type: Any = None) -> bool:
        return True

    async def get_authorized_access_types(self, username: str):
        return []


class FailureTestingAuthUtil(Authenticator, Authorizer):
    """
    A test class implementing ``Authenticator`` and ``Authorizer`` that always returns a user is not authenticated or
    is not authorized.
    """

    async def authenticate(self, username: str, secret: str) -> bool:
        return False

    async def check_authorized(self, username: str, access_type: Any = None) -> bool:
        return False

    async def get_authorized_access_types(self, username: str):
        return None


class TestingSession(FullAuthSession):

    def __init__(self, ip_address, session_id, user):
        super().__init__(ip_address=ip_address, session_id=session_id, user=user)


class TestingSessionManager(SessionManager):

    def __init__(self):
        self._next_id = 1
        self._sessions = {}
        self._secrets_to_ids = {}
        self._users_to_ids = {}

    def create_session(self, ip_address: str, username: str) -> TestingSession:
        session_id = self._next_id
        self._next_id += 1
        session = TestingSession(ip_address=ip_address, session_id=session_id, user=username)
        self._sessions[session_id] = session
        self._secrets_to_ids[session.session_secret] = session_id
        self._users_to_ids[session.user] = session_id
        return session

    def lookup_session_by_id(self, session_id: int) -> Optional[TestingSession]:
        if session_id not in self._sessions:
            return None
        return self._sessions[session_id]

    def lookup_session_by_secret(self, session_secret: str) -> Optional[TestingSession]:
        if session_secret is None or session_secret not in self._secrets_to_ids:
            return None
        session_id = self._secrets_to_ids[session_secret]
        return self.lookup_session_by_id(session_id)

    def lookup_session_by_username(self, username: str) -> Optional[TestingSession]:
        if username is None or username not in self._users_to_ids:
            return None
        session_id = self._users_to_ids[username]
        return self.lookup_session_by_id(session_id)

    def refresh_session(self, session: TestingSession) -> bool:
        session._last_accessed = datetime.datetime.now()

    def remove_session(self, session: TestingSession):
        if session.session_id in self._sessions and session.session_secret in self._secrets_to_ids:
            self._sessions.pop(session.session_id)
            self._secrets_to_ids.pop(session.session_secret)
            self._users_to_ids.pop(session.user)
