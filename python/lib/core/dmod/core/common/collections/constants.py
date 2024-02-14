"""
Defines constants to be used across this package
"""
from __future__ import annotations

import typing
import enum


EntryType = typing.TypeVar("EntryType")
"""A generic indicator for the type of an entry in a collection"""

KeyType = typing.TypeVar("KeyType", bound=typing.Hashable, covariant=True)
"""A generic indicator for the type of key in a map"""

ValueType = typing.TypeVar("ValueType")
"""A generic indicator for the type of value in a map"""


class CollectionEvent(str, enum.Enum):
    """
    Defines the names of the types of events a collection might encounter
    """
    SET = "SET"
    """The name of the event that would be triggered when setting a value on a collection"""

    GET = "GET"
    """The name of the event that would be triggered when getting a value from a collection"""

    UPDATE = "UPDATE"
    """The name of the event that would be triggered when modifying the value in a collection"""

    EXTEND = "EXTEND"
    """The name of the event that would be triggered when another collection is added to a collection"""

    DELETE = "DELETE"
    """The name of the event that would be triggered when an item is removed from a collection"""

    ADD = "ADD"
    """The name of the event that would be triggered when an item is added to a collection"""

    INSERT = "INSERT"
    """
    The name of the event that would be triggered when an item is inserted into a collection at a specific location
    """

    POP = "POP"
    """
    The name of the event that would be triggered when a value is popped from one end of the collection
    """

    REMOVE = "REMOVE"
    """
    The name of the event that would be triggered when a value is simply removed from a collection 
    (though not necessarily deleted)
    """

    REVERSE = "REVERSE"
    """
    The name of the event that would be triggered when the order of a collection is reversed
    """

    SORT = "SORT"
    """
    The name of the event that would be triggered when the order of items within a collection is modified based on 
    a sorting operation
    """

    CLEAR = "CLEAR"
    """
    The name of the operation that would be triggered when all items are removed from a collection at once
    """

    @classmethod
    def get(cls, name: str) -> CollectionEvent:
        """
        Get the enumerated value based on a similar name

        Args:
            name: The name of the CollectionEvent to find

        Returns:
            The matching CollectionEvent
        """
        lowercase_name = name.lower()
        for entry in cls:
            if entry.lower() == lowercase_name:
                return cls[entry]
        raise KeyError(f"There are no collection events named '{name}'")


class MapHandler(typing.Generic[KeyType, ValueType]):
    """
    A series of definitions of signatures to be used when events are triggered on a map
    """
    SET = typing.Callable[[typing.MutableMapping[KeyType, ValueType], KeyType, ValueType], typing.Any]
    """
    The type of function called when a value is set on a map: (Instance of Map, Map Key, New Value) -> Any
    """

    GET = typing.Callable[[typing.MutableMapping[KeyType, ValueType], KeyType, ValueType], typing.Any]
    """
    The type of function called when a value is retrieved from a map: (Instance of Map, Map Key, Value) -> Any
    """

    UPDATE = typing.Callable[[typing.MutableMapping[KeyType, ValueType], typing.Mapping[KeyType, ValueType]], typing.Any]
    """
    The type of function called when a value of a map is modified: (original map, updated map) -> Any
    """

    DELETE = typing.Callable[[typing.MutableMapping[KeyType, ValueType], KeyType, ValueType], typing.Any]
    """
    The type of function called when a value in a map is deleted: (Instance of map, deleted key, deleted value) -> Any
    """

    POP = typing.Callable[[typing.MutableMapping[KeyType, ValueType], typing.Optional[KeyType]], typing.Any]
    """
    The type of function called before a value is popped from the map: (Instance of Map, key (if given)) -> Any
    """

    REMOVE = typing.Callable[[typing.MutableMapping[KeyType, ValueType], KeyType, ValueType], typing.Any]
    """
    The type of function called when a value from a map is removed: (Instance of Map, Key, Value) -> Any
    """

    CLEAR = typing.Callable[[typing.MutableMapping[KeyType, ValueType]], typing.Any]
    """
    The type of function called before all values from a map are removed: (Original Instance of Map) -> Any
    """


class SequenceHandler(typing.Generic[EntryType]):
    """
    A series of type signatures that are appropriate for when certain events are triggered on a sequence of values
    """
    GET = typing.Callable[
        [
            typing.MutableSequence[EntryType],
            typing.Union[int, slice],
            typing.Union[EntryType, typing.MutableSequence[EntryType]]
        ],
        typing.Any
    ]
    """
    The type of function called when a value or values are retrieved from the collection: 
        (Instance of Collection, Indexer, Value or Sliced Values) -> Any
    """

    SET = typing.Callable[
        [
            typing.MutableSequence[EntryType],
            typing.Union[int, slice],
            typing.Union[EntryType, typing.MutableSequence[EntryType]]
        ],
        typing.Any
    ]
    """
    The type of function called when a value or values are updated in a collection:
        (Instance of Collection, Indexer, new Value or Values) -> Any
    """

    EXTEND = typing.Callable[[typing.MutableSequence[EntryType], typing.Iterable[EntryType]], typing.Any]
    """
    The type of function called when a series of values are added to a collection:
        (Instance of Collection, New Values) -> Any
    """

    ADD = typing.Callable[[typing.MutableSequence[EntryType], EntryType], typing.Any]
    """
    The type of function called when a single value is added to a collection:
        (Instance of Collection, New Value) -> Any
    """

    DELETE = typing.Callable[
        [
            typing.MutableSequence[EntryType],
            typing.Union[int, slice],
            typing.Union[EntryType, typing.MutableSequence[EntryType]]
        ],
        typing.Any
    ]
    """
    The type of function called when a single value is deleted from a collection
        (Instance of collection, indexer, value to be removed) -> Any
    """

    INSERT = typing.Callable[[typing.MutableSequence[EntryType], int, EntryType], typing.Any]
    """
    The type of function called when a single value is inserted at a specific location in a collection
        (Instance of collection, indexor, value to insert) -> Any
    """

    POP = typing.Callable[[typing.MutableSequence[EntryType], typing.Optional[int]], typing.Any]
    """
    The type of function called when a single value is popped from one end of the collection
        (Instance of the collection, indexor if given) -> Any
    """

    REMOVE = typing.Callable[[typing.MutableSequence[EntryType], EntryType], typing.Any]
    """
    The type of function called when a single value is removed from the collection:
        (Instance of the collection, Value being removed) -> Any
    """

    REVERSE = typing.Callable[[typing.MutableSequence[EntryType]], typing.Any]
    """
    The type of function called when the entire collection is reversed:
        (The newly ordered collection) -> Any
    """

    CLEAR = typing.Callable[[typing.MutableSequence[EntryType]], typing.Any]
    """
    The type of function called when all items are removed from the collection:
        (Collection prior to clearing) -> Any
    """

    SORT = typing.Callable[
        [typing.MutableSequence[EntryType], typing.Union[str, typing.Callable[[EntryType], typing.Any]], bool],
        typing.Any
    ]
    """
    The type of function called when the collection is sorted:
    
        (
            The collection being sorted,
            
            either the name of the field or a function used to provide a value to compare against,
            
            whether the order is ascending or descending
        ) -> Any
    """