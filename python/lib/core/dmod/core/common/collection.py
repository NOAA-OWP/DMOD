"""
Defines specialized collections that aren't built into any of the first or third party libraries
"""
import typing

from typing import Iterator

_T = typing.TypeVar("_T")


class Bag(typing.Collection[_T]):
    """
    A wrapper collection that hides functions/elements that treat the contents as anything other than an abstract
    collection

    Example Use Case:

        You need to represent collected data that is meant to be unordered, but not unique/requiring a hash.
        This leaves out list and set types.
    """
    def __init__(self, data: typing.Collection[_T] = None):
        self.__data = [value for value in data] if data is not None else list()

    def to_list(self) -> typing.List[_T]:
        """
        Convert the data into a normal list

        Returns:
            A list of the values within the bag
        """
        return [value for value in self.__data]

    def add(self, value: _T) -> "Bag[_T]":
        """
        Add a value to the bag

        Args:
            value: The item to add

        Returns:
            The updated bag
        """
        self.__data.append(value)
        return self

    def find(self, condition: typing.Callable[[_T], bool]) -> typing.Optional[_T]:
        """
        Find the first item in the bag that matches the given condition

        Args:
            condition: A function defining if the encountered element counts as the one the caller is looking for

        Returns:
            The first item in the collection that matches the condition
        """
        for entry in self.__data:
            if condition(entry):
                return entry

        return None

    def remove(self, element: _T):
        """
        Remove an element from the bag

        Args:
            element: The element to remove
        """
        if element in self.__data:
            self.__data.remove(element)

    def pick(self) -> typing.Optional[_T]:
        """
        Extract an element from the bag

        Returns:
            An element from the bag if one exists
        """
        extracted_value: typing.Optional[_T] = None

        if len(self.__data) > 0:
            extracted_value = self.__data.pop()

        return extracted_value

    def count(self, element: _T) -> int:
        """
        Count the number of times that a particular element is within the bag

        Args:
            element: The item to look for

        Returns:
            The number of times that that element is within the bag
        """
        return sum([entry for entry in self.__data if entry == element])

    def __len__(self) -> int:
        return len(self.__data)

    def __iter__(self) -> Iterator[_T]:
        return iter(self.__data)

    def __contains__(self, obj: object) -> bool:
        return obj in self.__data