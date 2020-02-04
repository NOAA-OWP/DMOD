from abc import ABC, abstractmethod


class UserManager(ABC):
    """
    A controller-type abstraction for managing users, pair with some kind of implementation-specific backend for storing
    actual user records.
    """

    @abstractmethod
    async def add_user(self, new_username: str, secret: str):
        """
        Asynchronously add a new user record secured by the given secret.

        Parameters
        ----------
        new_username : str
            the username (or analog) for the new user record to be created

        secret : str
            the "public" (i.e., application-side) secret that should only be available to the actual entity represented
            by the user record (e.g., a password hash), and thus authenticates identity

        Returns
        -------
        A representation (appropriate for the implementation) of the either the created user record or the failure to
        create such a record.
        """
        pass

    @abstractmethod
    async def delete_user(self, user) -> bool:
        """
        Asynchronously delete an existing user record.

        Parameters
        ----------
        user
            a full or implicit representation (depending on the implementation) of the user to be deleted

        Returns
        -------
        ``True`` if the user was successfully deleted, or ``False`` if not.
        """
        pass

    @abstractmethod
    async def lookup_user(self, user_identifier):
        """
        Request the lookup and return of the user record identified by the given identifier argument.

        Parameters
        ----------
        user_identifier
            an identifier that can be used to uniquely identify a specific user record in the given implementation

        Returns
        -------
        A representation (appropriate for the implementation) of the sought user record, if it is possible to return it
        """
        pass


class AuthControlledUserManager(UserManager, ABC):
    """
    Extension of :class:`UserManager` that safeguards its usage by maintaining a "manager user" and only performing
    actions for which this user is authorized.
    """

    @abstractmethod
    def get_manager_user(self):
        """
        Get the full or implicit representation (depending on the implementation) of the "manager user" for this object,
        who must be authorized to perform a triggered action for the object to actually perform it.

        Returns
        -------
        A full or implicit representation (depending on the implementation) of the manager user
        """
        pass
