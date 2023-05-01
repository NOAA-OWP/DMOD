"""
Common type hinting protocols to use throughout the code base
"""
import typing


_CLASS_TYPE = typing.TypeVar("_CLASS_TYPE")


@typing.runtime_checkable
class KeyedObjectProtocol(typing.Protocol):
    """
    Represents a class that defines its own key that defines its own uniqueness
    """
    @classmethod
    def get_key_fields(cls) -> typing.List[str]:
        """
        Get the list of all fields on the object that represent the parameters for uniqueness
        """
        ...

    def get_key_values(self) -> typing.Dict[str, typing.Any]:
        """
        Gets all values from the object representing the key
        """
        ...

    def matches(self, other: object) -> bool:
        ...


@typing.runtime_checkable
class CombinableObjectProtocol(typing.Protocol[_CLASS_TYPE]):
    """
    Represents a class that may be explicitly combined with another of its same type either through a class level
    'combine' function or through the '+' operator
    """
    @classmethod
    def combine(cls, first: _CLASS_TYPE, second: _CLASS_TYPE) -> _CLASS_TYPE:
        """
        Combines two instances of this class to form a brand new one
        """
        ...

    def __add__(self, other: _CLASS_TYPE) -> _CLASS_TYPE:
        ...


@typing.runtime_checkable
class DescribableProtocol(typing.Protocol):
    """
    Represents an object that has a 'description' attribute
    """
    description: str