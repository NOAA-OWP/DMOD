#!/usr/bin/env python3
import typing
import logging

from datetime import datetime

from .. import session


logging.warning(
    "The example Session and SessionManager module has been loaded; "
    "this should not be used in any capacity other than for source code reference."
)


class ExampleSession(session.Session):
    def __init__(self, ip_address, session_id, user, session_secret=None, created=None, last_accessed=None):
        super().__init__(session_id=session_id, session_secret=session_secret,
                         created=created, last_accessed=last_accessed)
        self.is_address = ip_address
        self.user = user
        raise NotImplementedError(
            f"{self.__class__.__name__} is meant as an example implementation; you may use it as a jumping off "
            f"point or template, but not otherwise."
        )


class ExampleSessionManager(session.SessionManager):
    def __init__(self):
        self._next_id = 1
        self._sessions = {}
        self._secrets_to_ids = {}
        self._users_to_ids = {}
        raise NotImplementedError(
            f"{self.__class__.__name__} is meant as an example implementation; you may use it as a jumping off "
            f"point or template, but not otherwise."
        )

    def create_session(self, ip_address: str, username: str) -> ExampleSession:
        session_id = self._next_id
        self._next_id += 1
        session = ExampleSession(ip_address=ip_address, session_id=session_id, user=username)
        self._sessions[session_id] = session
        self._secrets_to_ids[session.session_secret] = session_id
        self._users_to_ids[session.user] = session_id
        return session

    def lookup_session_by_id(self, session_id: int) -> typing.Optional[ExampleSession]:
        if session_id not in self._sessions:
            return None
        return self._sessions[session_id]

    def lookup_session_by_secret(self, session_secret: str) -> typing.Optional[ExampleSession]:
        if session_secret is None or session_secret not in self._secrets_to_ids:
            return None
        session_id = self._secrets_to_ids[session_secret]
        return self.lookup_session_by_id(session_id)

    def lookup_session_by_username(self, username: str) -> typing.Optional[ExampleSession]:
        if username is None or username not in self._users_to_ids:
            return None
        session_id = self._users_to_ids[username]
        return self.lookup_session_by_id(session_id)

    def refresh_session(self, session: ExampleSession) -> bool:
        session._last_accessed = datetime.now()
        return True

    def remove_session(self, session: ExampleSession):
        if session.session_id in self._sessions and session.session_secret in self._secrets_to_ids:
            self._sessions.pop(session.session_id)
            self._secrets_to_ids.pop(session.session_secret)
            self._users_to_ids.pop(session.user)
