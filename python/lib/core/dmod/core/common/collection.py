"""
Defines specialized collections that aren't built into any of the first or third party libraries
"""
import typing

from collections.abc import Collection
from typing import Iterator

_T = typing.TypeVar("_T")


class Bag(Collection[_T]):
    """
    A wrapper collection that hides functions/elements that treat the contents as anything other than an abstract
    collection

    Example Use Case:

        You need to represent collected data that is meant to be unordered, but not unique/requiring a hash.
        This leaves out list and set types.
    """
    def __init__(self, data: typing.Collection[_T] = None):
        self.__data = [value for value in data] or list()

    def to_list(self) -> typing.List[_T]:
        return [value for value in self.__data]

    def add(self, value: _T) -> "Bag[_T]":
        self.__data.append(value)
        return self

    def find(self, condition: typing.Callable[[_T], bool]) -> typing.Optional[_T]:
        for entry in self.__data:
            if condition(entry):
                return entry

        return None

    def __len__(self) -> int:
        return len(self.__data)

    def __iter__(self) -> Iterator[_T]:
        return iter(self.__data)

    def __contains__(self, obj: object) -> bool:
        return obj in self.__data