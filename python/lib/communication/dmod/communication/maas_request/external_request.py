from abc import ABC, abstractmethod

from ..message import AbstractInitRequest


class ExternalRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of externally-initiated (and, therefore, authenticated) MaaS system requests.
    """
    # NOTE: in some places this is serialized as `session-secret`
    session_secret: str

    class Config:
        fields = {"session_secret": {"alias": "session-secret"}}

    @classmethod
    @abstractmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict):
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        pass

    def _check_class_compatible_for_equality(self, other: object) -> bool:
        """
        Check and return whether another object is of some class that is compatible for equality checking with the class
        of this instance, such that the class difference does not independently imply the other object and this instance
        are not equal.

        In the base implementation, the method returns True if and only if the class of the parameter object is equal to
        the class of the receiver object.

        Overriding implementations must always ensure the method returns True when the parameter has the same class
        value as the receiver object.

        Further, overriding implementations should ensure the method remains symmetric across implementations; i.e., for
        any objects x and y where both object have an implementation of this method as a member, then the following
        should always be True:

            x._check_class_compatible_for_equality(y) == y._check_class_compatible_for_equality(x)

        Parameters
        ----------
        other

        Returns
        -------
        type_compatible_for_equality : bool
            whether the class of the other object is not independently sufficient for a '==' check between this and the
            other object to return False
        """
        try:
            return other is not None and self.__class__ == other.__class__
        except:
            return False
