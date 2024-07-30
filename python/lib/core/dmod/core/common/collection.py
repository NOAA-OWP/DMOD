"""
Defines specialized collections that aren't built into any of the first or third party libraries
"""
from __future__ import annotations

import abc
import enum
import inspect
import typing
import uuid
from datetime import datetime
from datetime import timedelta

import pydantic
from pydantic import PrivateAttr
from pydantic.generics import GenericModel

from typing import Iterator

_T = typing.TypeVar("_T")
_KT = typing.TypeVar("_KT", bound=typing.Hashable, covariant=True)
_VT = typing.TypeVar("_VT")


class CollectionEvent(str, enum.Enum):
    SET = "SET"
    GET = "GET"
    UPDATE = "UPDATE"
    EXTEND = "EXTEND"
    DELETE = "DELETE"
    ADD = "ADD"
    INSERT = "INSERT"
    POP = "POP"
    REMOVE = "REMOVE"
    REVERSE = "REVERSE"
    SORT = "SORT"
    CLEAR = "CLEAR"

    @classmethod
    def get(cls, name: str) -> CollectionEvent:
        lowercase_name = name.lower()
        for entry in cls:
            if entry.lower() == lowercase_name:
                return cls[entry]
        raise KeyError(f"There are no collection events named '{name}'")


class FunctionEnum:
    @classmethod
    def entries(cls) -> typing.Iterable[typing.Tuple[str, typing.Callable]]:
        all_members: typing.List[typing.Tuple[str, typing.Any]] = inspect.getmembers(
            cls,
            predicate=lambda member: not inspect.isroutine(member)
        )

        return [
            (name, value)
            for name, value in all_members
            if not name.startswith("__")
               and not name.endswith("__")
        ]

    @classmethod
    def values(cls) -> typing.Iterable[typing.Callable]:
        return [
            value
            for name, value in cls.entries()
        ]

    @classmethod
    def keys(cls) -> typing.Iterable[str]:
        return [
            name
            for name, value in cls.entries()
        ]

    @classmethod
    def from_name(cls, name: str) -> typing.Callable:
        entry = cls.find(name)

        if entry is None:
            raise KeyError(f"There are not entries in the '{cls.__name__}' Enum named '{name}")

        return entry

    @classmethod
    def has(cls, name: str) -> bool:
        return cls.find(name) is not None

    @classmethod
    def find(cls, name: str) -> typing.Optional[typing.Callable]:
        name = name.lower()
        for handler_name, value in cls.entries():
            if handler_name.lower() == name:
                return value
        return None


class MapHandler(typing.Generic[_KT, _VT]):
    SET = typing.Callable[[typing.MutableMapping[_KT, _VT], _KT, _VT], typing.Any]
    GET = typing.Callable[[typing.MutableMapping[_KT, _VT], _KT, _VT], typing.Any]
    UPDATE = typing.Callable[[typing.MutableMapping[_KT, _VT], typing.Mapping[_KT, _VT]], typing.Any]
    DELETE = typing.Callable[[typing.MutableMapping[_KT, _VT], _KT, _VT], typing.Any]
    POP = typing.Callable[[typing.MutableMapping[_KT, _VT], typing.Optional[_KT]], typing.Any]
    REMOVE = typing.Callable[[typing.MutableMapping[_KT, _VT], _KT, _VT], typing.Any]
    CLEAR = typing.Callable[[typing.MutableMapping[_KT, _VT]], typing.Any]


class SequenceHandler(typing.Generic[_T]):
    GET = typing.Callable[
        [
            typing.MutableSequence[_T],
            typing.Union[int, slice],
            typing.Union[_T, typing.MutableSequence[_T]]
        ],
        typing.Any
    ]
    SET = typing.Callable[
        [
            typing.MutableSequence[_T],
            typing.Union[int, slice],
            typing.Union[_T, typing.MutableSequence[_T]]
        ],
        typing.Any
    ]
    EXTEND = typing.Callable[[typing.MutableSequence[_T], typing.Iterable[_T]], typing.Any]
    ADD = typing.Callable[[typing.MutableSequence[_T], _T], typing.Any]
    DELETE = typing.Callable[
        [
            typing.MutableSequence[_T],
            typing.Union[int, slice],
            typing.Union[_T, typing.MutableSequence[_T]]
        ],
        typing.Any
    ]
    INSERT = typing.Callable[[typing.MutableSequence[_T], int, _T], typing.Any]
    POP = typing.Callable[[typing.MutableSequence[_T], typing.Optional[int]], typing.Any]
    REMOVE = typing.Callable[[typing.MutableSequence[_T], _T], typing.Any]
    REVERSE = typing.Callable[[typing.MutableSequence[_T]], typing.Any]
    CLEAR = typing.Callable[[typing.MutableSequence[_T]], typing.Any]
    SORT = typing.Callable[[typing.MutableSequence[_T], typing.Any, bool], typing.Any]


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


class _OccurrenceTracker(typing.Generic[_T]):
    """
    Keeps track of occurrences of a type of value that have been encountered within a duration
    """
    def __init__(self, key: _T, duration: timedelta, threshold: int, on_filled: typing.Callable[[_T], typing.Any]):
        self.__key = key
        self.__duration = duration
        self.__threshold = threshold
        self.__occurences: typing.List[datetime] = []
        self.__on_filled = on_filled

    def value_encountered(self):
        """
        Inform the tracker that the value has been encountered again
        """
        self.update_occurrences()
        self.__occurences.append(datetime.now())
        if len(self.__occurences) >= self.__threshold:
            self.__on_filled(self.__key)

    def update_occurrences(self) -> int:
        """
        Update the list of occurrences to include only those within the current duration

        Returns:
            The number of occurrences still being tracked
        """
        cutoff: datetime = datetime.now() - self.__duration
        self.__occurences = [
            occurrence
            for occurrence in self.__occurences
            if occurrence > cutoff
        ]
        return len(self.__occurences)

    @property
    def key(self):
        """
        The identifier that is being tracked
        """
        return self.__key

    def __len__(self):
        return len(self.__occurences)

    def __str__(self):
        if len(self.__occurences) == 0:
            occurrences_details = f"No Occurences within the last {self.__duration.total_seconds()} seconds."
        else:
            occurrences_details = (f"{len(self.__occurences)} occurrences since "
                                   f"{self.__occurences[0].strftime('%Y-%m-%d %H:%M:%S')}")
        return f"{self.key}: {occurrences_details}"


class TimedOccurrenceWatcher:
    """
    Keeps track of the amount of occurrences of items within a range of time
    """
    MINIMUM_TRACKING_SECONDS: typing.Final[float] = 0.1
    """
    The lowest number of seconds to watch for multiple occurrences. Only acting when multiple occurrences are tracked
    in under 100ms would create a scenario where the watcher will most likely never trigger an action, rendering
    this the wrong tool for the job.
    """

    @staticmethod
    def default_key_function(obj: object) -> type:
        """
        The function used to find a common identifier for an object if one is not provided
        """
        return type(obj)

    def __init__(
        self,
        duration: timedelta,
        threshold: int,
        on_filled: typing.Callable[[_T], typing.Any],
        key_function: typing.Callable[[_VT], _KT] = None
    ):
        if not isinstance(duration, timedelta):
            raise ValueError(f"Cannot create a {self.__class__.__name__} - {duration} is not a timedelta object")

        if duration.total_seconds() < self.MINIMUM_TRACKING_SECONDS:
            raise ValueError(
                f"Cannot create a {self.__class__.__name__} - the duration is too short ({duration.total_seconds()}s)"
            )

        self.__duration = duration

        if not isinstance(key_function, typing.Callable):
            key_function = self.default_key_function

        self.__key_function = key_function
        self.__entries: typing.Dict[uuid.UUID, _OccurrenceTracker] = {}
        self.__threshold = threshold
        self.__on_filled = on_filled

    def value_encountered(self, value: _T):
        """
        Add an occurrence of an object to track

        Args:
            value: The item to track
        """
        self.__update_trackers()
        self._get_tracker(value).value_encountered()

    def _get_tracker(self, value: _T) -> _OccurrenceTracker[_T]:
        """
        Get an occurrence tracker for the given value

        Args:
            value: The value to track

        Returns:
            A tracker for the value
        """
        key = self.__key_function(value)

        for tracker in self.__entries.values():
            if tracker.key == key:
                return tracker

        new_tracker = _OccurrenceTracker(
            key=key,
            duration=self.__duration,
            threshold=self.__threshold,
            on_filled=self.__on_filled
        )
        self.__entries[uuid.uuid1()] = new_tracker
        return new_tracker

    def __update_trackers(self):
        """
        Update the amount of items in each tracker

        If a tracker becomes empty it will be removed
        """
        for tracker_id, tracker in self.__entries.items():
            amount_left = tracker.update_occurrences()
            if amount_left == 0:
                del self.__entries[tracker_id]

    @property
    def size(self) -> int:
        """
        The number of items encountered within the duration
        """
        self.__update_trackers()
        return sum(len(tracker) for tracker in self.__entries.values())

    @property
    def duration(self) -> timedelta:
        """
        The amount of time to track items for
        """
        return self.__duration

    def __str__(self):
        return f"{self.__class__.__name__}: {self.size} items within the last {self.duration.total_seconds()} Seconds"

    def __repr__(self):
        return self.__str__()


class EventfulMap(abc.ABC, typing.MutableMapping[_KT, _VT], typing.Generic[_KT, _VT]):
    @abc.abstractmethod
    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        ...

    @abc.abstractmethod
    def inner_map(self) -> typing.MutableMapping[_KT, _VT]:
        pass

    def add_handler(self, event_type: typing.Union[CollectionEvent, str], handler: typing.Callable):
        event_type = CollectionEvent.get(event_type) if isinstance(event_type, str) else event_type

        if event_type not in self.get_handlers():
            self.get_handlers()[event_type] = list()

        if handler not in self.get_handlers()[event_type]:
            self.get_handlers()[event_type].append(handler)

    def get(self, __key: _KT, default = None):
        value = self.inner_map().get(__key, default)

        handlers: typing.Iterable[MapHandler.GET] = self.get_handlers().get(CollectionEvent.GET, [])

        for handler in handlers:
            handler(self, __key, value)

        return value

    def clear(self) -> None:
        handlers: typing.Iterable[MapHandler.CLEAR] = self.get_handlers().get(CollectionEvent.CLEAR, [])
        for handler in handlers:
            handler(self)
        return self.inner_map().clear()

    def items(self) -> typing.ItemsView[str, _VT]:
        return self.inner_map().items()

    def keys(self) -> typing.KeysView[str]:
        return self.inner_map().keys()

    def values(self) -> typing.ValuesView[_VT]:
        return self.inner_map().values()

    def pop(self, __key: _KT, default = None) -> _VT:
        handlers: typing.Iterable[MapHandler.POP] = self.get_handlers().get(CollectionEvent.POP, [])
        for handler in handlers:
            handler(self, __key)
        return self.inner_map().pop(__key, default)

    def popitem(self) -> tuple[_KT, _VT]:
        handlers: typing.Iterable[MapHandler.POP] = self.get_handlers().get(CollectionEvent.POP, [])
        for handler in handlers:
            handler(self, None)
        return self.inner_map().popitem()

    def setdefault(self, __key: _KT, __default: _VT = ...) -> typing.Optional[_VT]:
        return self.inner_map().setdefault(__key, __default)

    def update(self, __m: typing.Mapping[_KT, _VT], **kwargs: _VT) -> None:
        handlers: typing.Iterable[MapHandler.UPDATE] = self.get_handlers().get(CollectionEvent.UPDATE, [])
        for handler in handlers:
            handler(self, __m)
        return self.inner_map().update(__m, **kwargs)

    def __setitem__(self, __k: _KT, __v: _VT) -> None:
        handlers: typing.Iterable[MapHandler.SET] = self.get_handlers().get(CollectionEvent.SET, [])
        for handler in handlers:
            handler(self, __k, __v)

        self.inner_map()[__k] = __v

    def __delitem__(self, __v: _KT) -> None:
        handlers: typing.Iterable[MapHandler.DELETE] = self.get_handlers().get(CollectionEvent.DELETE, [])
        for handler in handlers:
            handler(self, __v, self[__v])
        del self.inner_map()[__v]

    def __getitem__(self, __k: _KT) -> _VT:
        value = self.inner_map()[__k]

        handlers: typing.Iterable[MapHandler.GET] = self.get_handlers().get(CollectionEvent.GET, [])
        for handler in handlers:
            handler(self, __k, value)
        return value

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, item: _KT) -> bool:
        return item in self.keys()

    def __len__(self) -> int:
        return len(self.inner_map())


class BaseEventfulSequence(abc.ABC, typing.MutableSequence[_T], typing.Generic[_T]):
    @property
    @abc.abstractmethod
    def _inner_sequence(self) -> typing.List[_T]:
        pass

    @abc.abstractmethod
    def _get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        pass

    @property
    def values(self) -> typing.Sequence[_T]:
        return self._inner_sequence

    def add_handler(self, event_type: typing.Union[CollectionEvent, str], handler: typing.Callable):
        event_type = CollectionEvent.get(event_type) if isinstance(event_type, str) else event_type

        if event_type not in self._get_handlers():
            self._get_handlers()[event_type] = list()

        if handler not in self._get_handlers()[event_type]:
            self._get_handlers()[event_type].append(handler)

    def insert(self, index: int, value: _T) -> None:
        handlers: typing.Sequence[SequenceHandler.INSERT] = self._get_handlers().get(CollectionEvent.INSERT, [])

        for handler in handlers:
            handler(self, index, value)

        self._inner_sequence.insert(index, value)

    def append(self, value: _T) -> None:
        handlers: typing.Sequence[SequenceHandler.ADD] = self._get_handlers().get(CollectionEvent.ADD, [])

        for handler in handlers:
            handler(self, value)

        self._inner_sequence.append(value)

    def remove(self, value: _T) -> None:
        handlers: typing.Sequence[SequenceHandler.REMOVE] = self._get_handlers().get(CollectionEvent.REMOVE, [])

        for handler in handlers:
            handler(self, value)

        self._inner_sequence.remove(value)

    def pop(self, index: int = ...) -> _T:
        handlers: typing.Sequence[SequenceHandler.POP] = self._get_handlers().get(CollectionEvent.POP, [])

        for handler in handlers:
            handler(self, index)

        return self._inner_sequence.pop(index)

    def reverse(self) -> None:
        handlers: typing.Sequence[SequenceHandler.REVERSE] = self._get_handlers().get(CollectionEvent.REVERSE, [])
        for handler in handlers:
            handler(self)

        self._inner_sequence.reverse()

    def sort(self, *, key: None = ..., reverse: bool = ...):
        handlers: typing.Sequence[SequenceHandler.SORT] = self._get_handlers().get(CollectionEvent.SORT, [])

        for handler in handlers:
            handler(self, key, reverse)

        return self._inner_sequence.sort(key=key, reverse=reverse)

    def index(self, value: typing.Any, start: int = ..., stop: int = ...) -> int:
        return self._inner_sequence.index(value, start, stop)

    def extend(self, values: typing.Iterable[_T]) -> None:
        handlers: typing.Sequence[SequenceHandler.EXTEND] = self._get_handlers().get(CollectionEvent.EXTEND, [])

        for handler in handlers:
            handler(self, values)

        self._inner_sequence.extend(values)

    def count(self, __value: _T) -> int:
        return self._inner_sequence.count(__value)

    def clear(self) -> None:
        handlers: typing.Sequence[SequenceHandler.CLEAR] = self._get_handlers().get(CollectionEvent.CLEAR, [])

        for handler in handlers:
            handler(self)

        return self._inner_sequence.clear()

    def __getitem__(self, index: typing.Union[int, slice]) -> _T:
        value = self._inner_sequence[index]

        handlers: typing.Iterable[SequenceHandler.GET] = self._get_handlers().get(CollectionEvent.GET, [])

        for handler in handlers:
            handler(self, index, value)

        return value

    def __setitem__(self, index: typing.Union[int, slice], value: typing.Union[_T, typing.MutableSequence[_T]]) -> None:
        handlers: typing.Sequence[SequenceHandler.SET] = self._get_handlers().get(CollectionEvent.SET, [])

        for handler in handlers:
            handler(self, index, value)

        self._inner_sequence[index] = value

    def __delitem__(self, index: typing.Union[int, slice]) -> None:
        handlers: typing.Sequence[SequenceHandler.DELETE] = self._get_handlers().get(CollectionEvent.REMOVE, [])

        for handler in handlers:
            handler(self, index, self[index])

        del self._inner_sequence[index]

    def __contains__(self, item: _T) -> bool:
        return item in self._inner_sequence

    def __iter__(self):
        return iter(self._inner_sequence)

    def __eq__(self, other: BaseEventfulSequence[_T]) -> bool:
        if not isinstance(other, self.__class__):
            return False

        if len(self) != len(other):
            return False

        for item_index, item in enumerate(self.values):
            other_item = other[item_index]
            if item != other_item:
                return False

        return True

    def __len__(self) -> int:
        return len(self._inner_sequence)


class MapModel(GenericModel, EventfulMap[_KT, _VT], typing.Generic[_KT, _VT]):
    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    def inner_map(self) -> typing.MutableMapping[_KT, _VT]:
        return self.__root__

    __root__: typing.Dict[_KT, _VT]
    _handlers: typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]] = PrivateAttr(default_factory=dict)


class SequenceModel(GenericModel, BaseEventfulSequence[_T], typing.Generic[_T]):
    @property
    def _inner_sequence(self) -> typing.MutableSequence[_T]:
        return self.__root__

    def _get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    __root__: typing.List[_T] = pydantic.Field(default_factory=list)
    _handlers: typing.Dict[CollectionEvent, typing.List[typing.Callable]] = PrivateAttr(default_factory=dict)
