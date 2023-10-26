"""
Common type hinting protocols to use throughout the code base
"""
from __future__ import annotations

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


if typing.TYPE_CHECKING:
    from _typeshed.dbapi import DBAPIConnection
    from _typeshed.dbapi import DBAPICursor
    from _typeshed.dbapi import DBAPIColumnDescription
else:
    # The following are copied from `_typeshed.dbapi
    #   That library isn't always available at runtime, so this is here as a guard
    DBAPITypeCode: typing.TypeAlias = typing.Optional[typing.Any]

    # Strictly speaking, this should be a Sequence, but the type system does
    # not support fixed-length sequences.
    DBAPIColumnDescription: typing.TypeAlias = tuple[
        str,
        DBAPITypeCode,
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int]
    ]


    @typing.runtime_checkable
    class DBAPIConnection(typing.Protocol):
        def close(self) -> object: ...
        def commit(self) -> object: ...
        # optional:
        # def rollback(self) -> Any: ...
        def cursor(self) -> DBAPICursor: ...


    @typing.runtime_checkable
    class DBAPICursor(typing.Protocol):
        @property
        def description(self) -> typing.Optional[typing.Sequence[DBAPIColumnDescription]]:
            return None

        @property
        def rowcount(self) -> int:
            return -1

        def close(self) -> object: ...
        def execute(self, __operation: str, __parameters: typing.Sequence[typing.Any] | typing.Mapping[str, typing.Any] = ...) -> object: ...
        def executemany(self, __operation: str, __seq_of_parameters: typing.Sequence[typing.Sequence[typing.Any]]) -> object: ...
        def fetchone(self) -> typing.Sequence[typing.Any] | None: ...
        def fetchmany(self, __size: int = ...) -> typing.Sequence[typing.Sequence[typing.Any]]: ...
        def fetchall(self) -> typing.Sequence[typing.Sequence[typing.Any]]: ...

        arraysize: int
        def setinputsizes(self, __sizes: typing.Sequence[DBAPITypeCode | int | None]) -> object: ...
        def setoutputsize(self, __size: int, __column: int = ...) -> object: ...