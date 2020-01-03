from abc import ABC, abstractmethod
from typing import Any


class Authenticator(ABC):

    @abstractmethod
    async def authenticate(self, username: str, secret: str) -> bool:
        """
        Asynchronously test if a provided username+secret combination qualifies a user's assertion of identity as
        authentic.

        Parameters
        ----------
        username : str
            the username (or analog) for the asserted identity

        secret : str
            the secret that should be known only to the actual entity represented by the identity (e.g., a password),
            and thus establishes identity

        Returns
        -------
        ``True`` if the username+secret combination demonstrates an authentic claim of identity, or ``False`` if not
        """
        pass


class Authorizer(ABC):

    @abstractmethod
    async def check_authorized(self, username: str, access_type: Any = None) -> bool:
        """
        Asynchronously test that the user identified by the given username is authorized for given access right.

        A default ``access_type`` of ``None`` implies that the access type being checked is for access to all resources
        and actions.

        Parameters
        ----------
        username : str
            the username of the user for which authorization is being checked

        access_type
            a representation of the access for which the test of authorization is being performed, where the default of
            ``None`` implies the tested access type is effectively "everything" or "all"

        Returns
        -------
        ``True`` if the represented user is authorized, or ``False`` if not
        """
        pass

    @abstractmethod
    async def get_authorized_access_types(self, username: str) -> tuple:
        """
        Asynchronously get the access types for which the user with the provided username is authorized.

        If a user is not authorized for any level of access, the method returns a tuple with ``None`` as its only item.
        For convenience (or cases when there are no granular representations of access types available), the method will
        return an empty tuple to represent an implicit default level access.

        Parameters
        ----------
        username : str
            the username representing the identity of the user in question

        Returns
        -------
        list
            a list of the access types for which the user is authorized for access
        """
        pass


class DummyAuthUtil(Authenticator, Authorizer):
    """
    A class mostly for prototyping and development that considers all authentication and authorization requests to be
    good, without doing any checking.

    For the :meth:`get_authorized_types` method, a simple empty list is returned, signifying access of the default level
    only (which for this is still implicitly the equivalent of 'all').
    """

    async def authenticate(self, username: str, secret: str) -> bool:
        return True

    async def check_authorized(self, username: str, access_type: Any = None) -> bool:
        return True

    async def get_authorized_access_types(self, username: str):
        return []
