from typing import Any
from ..externalrequests.auth_handler import Authenticator, Authorizer


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
