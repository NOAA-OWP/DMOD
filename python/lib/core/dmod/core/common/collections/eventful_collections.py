"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import inspect
import typing
import abc

from typing_extensions import Self

from .constants import CollectionEvent
from .constants import MapHandler
from .constants import SequenceHandler

_T = typing.TypeVar("_T")
_KT = typing.TypeVar("_KT", bound=typing.Hashable, covariant=True)
_VT = typing.TypeVar("_VT")


SENTINEL = object()


class BaseEventfulMap(abc.ABC, typing.MutableMapping[_KT, _VT], typing.Generic[_KT, _VT]):
    """
    Base class for a map that has event handlers for basic actions
    """
    @classmethod
    def _create_default_map(cls) -> typing.MutableMapping[_KT, _VT]:
        """
        Create the wrapped structure for this map

        Override for a different backing structure

        Returns:
            The map that will contain the data within this
        """
        return {}

    @abc.abstractmethod
    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        """
        Get all registered event handlers

        Returns:
            A dictionary mapping event types to a list of handlers
        """

    @abc.abstractmethod
    def inner_map(self) -> typing.MutableMapping[_KT, _VT]:
        """
        Get the inner map that this wraps

        Returns:
            The raw data that lies underneath the wrapping for event handling
        """

    @abc.abstractmethod
    def _get_leftover_tasks(self) -> typing.MutableSequence[typing.Awaitable[_KT]]:
        """
        A listing of asynchronous tasks that have yet to be awaited
        """

    async def commit(self):
        """
        Complete all asynchronous tasks that have yet to be awaited
        """

        while self._get_leftover_tasks():
            task = self._get_leftover_tasks().pop()
            result = await task

            if inspect.isawaitable(result):
                self._get_leftover_tasks().append(result)

    def add_handler(self, event_type: typing.Union[CollectionEvent, str], *handlers: typing.Callable):
        """
        Add an event handler to the map

        Args:
            event_type: The type of event that will trigger the handler
            handlers: Functions to call when the event is triggered
        """
        event_type = CollectionEvent.get(event_type) if isinstance(event_type, str) else event_type

        if event_type not in self.get_handlers():
            self.get_handlers()[event_type] = []

        for handler in handlers:
            if handler not in self.get_handlers()[event_type]:
                self.get_handlers()[event_type].append(handler)

    def get(self, __key: _KT, default=None):
        value = self.inner_map().get(__key, SENTINEL)

        if value is not SENTINEL:
            handlers: typing.Iterable[MapHandler.GET] = self.get_handlers().get(CollectionEvent.GET, [])

            for handler in handlers:
                handler(self, __key, value)

            return value

        return default

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

    def pop(self, __key: _KT, default=None) -> typing.Optional[_VT]:
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

    def handle(self, event: typing.Union[str, CollectionEvent], *args, **kwargs):
        handlers: typing.Iterable[typing.Callable] = self.get_handlers().get(event, [])

        for handler in handlers:
            result = handler(*args, **kwargs)

            if inspect.isawaitable(result):
                self._get_leftover_tasks().append(result)

    async def trigger(self, event: typing.Union[str, CollectionEvent], *args, **kwargs):
        handlers: typing.Iterable[typing.Callable] = self.get_handlers().get(event, [])

        handlers_to_wait_for: typing.List[typing.Awaitable] = []

        for handler in handlers:
            result = handler(*args, **kwargs)

            if inspect.isawaitable(result):
                handlers_to_wait_for.append(result)

        while handlers_to_wait_for:
            handler_result = handlers_to_wait_for.pop()

            result = await handler_result

            if inspect.isawaitable(result):
                handlers_to_wait_for.append(result)

    def update(self, __m: typing.Mapping[_KT, _VT], **kwargs: _VT) -> None:
        """
        Merge an enother map into this one

        Args:
            __m: The map to add to this
            **kwargs: Any extra arguments
        """
        self.handle(CollectionEvent.UPDATE, self, __m)
        return self.inner_map().update(__m, **kwargs)

    def __setitem__(self, __k: _KT, __v: _VT) -> None:
        self.handle(CollectionEvent.SET, self, __k, __v)
        self.inner_map()[__k] = __v

    def __delitem__(self, __v: _KT) -> None:
        value = self.inner_map()[__v]
        self.handle(CollectionEvent.DELETE, self, __v, value)
        del self.inner_map()[__v]

    def __getitem__(self, __k: _KT) -> _VT:
        value = self.inner_map()[__k]
        self.handle(CollectionEvent.GET, self, __k, value)
        return value

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, item: _KT) -> bool:
        return item in self.keys()

    def __len__(self) -> int:
        return len(self.inner_map())

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.commit()


class EventfulMap(BaseEventfulMap[_KT, _VT], typing.Generic[_KT, _VT]):
    """
    The most basic implementation of a BaseEventfulMap
    """

    def _get_leftover_tasks(self) -> typing.MutableSequence[typing.Awaitable[_KT]]:
        return self.__leftover_tasks

    def __init__(self, contents: typing.Dict[_KT, _VT] = None, **kwargs):
        """
        Constructor

        Note: Any event handlers passed via kwargs or contents will NOT be added to the set of handlers

        Args:
            contents: A preexisting collection of items to put in the map
            **kwargs: Any key-value pairs that might also fit within the map
        """
        self.__handlers: typing.Dict[CollectionEvent, typing.List[typing.Callable]] = {}
        """The handlers for individual events"""

        self.__contents: typing.Dict[_KT, _VT] = self._create_default_map()
        """The items contained within the map"""

        self.__leftover_tasks: typing.List[typing.Awaitable[_KT]] = []

        self.__contents.update(contents or {})
        self.__contents.update(dict(kwargs))

    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self.__handlers

    def inner_map(self) -> typing.MutableMapping[_KT, _VT]:
        return self.__contents


class BaseEventfulSequence(abc.ABC, typing.MutableSequence[_T], typing.Generic[_T]):
    """
    Base class for a mutable sequence that provides event handling for common operations
    """
    @abc.abstractmethod
    def __init__(self, values: typing.Iterable[_T] = None):
        ...

    @property
    @abc.abstractmethod
    def _inner_sequence(self) -> typing.MutableSequence[_T]:
        """
        The internal collection of items
        """

    @abc.abstractmethod
    def _get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        """
        Get all handlers associated with this collection

        Returns:
            A dictionary of all handlers associated with this collection
        """

    @property
    def values(self) -> typing.Sequence[_T]:
        """
        Get the raw collection of values from this collection
        """
        return self._inner_sequence

    def add_handler(self, event_type: typing.Union[CollectionEvent, str], handler: typing.Callable):
        """
        Add a handler for this type of event

        Args:
            event_type: The type of event to tie a handler to
            handler: A function to call when the event is triggered
        """
        event_type = CollectionEvent.get(event_type) if isinstance(event_type, str) else event_type

        if event_type not in self._get_handlers():
            self._get_handlers()[event_type] = []

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
        if reverse is None:
            reverse = False

        handlers: typing.Sequence[SequenceHandler.SORT] = self._get_handlers().get(CollectionEvent.SORT, [])

        for handler in handlers:
            handler(self, key, reverse)

        return sorted(self._inner_sequence, key=key, reverse=reverse)

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

    def __hash__(self):
        return hash(tuple((
            value if isinstance(value, typing.Hashable) else repr(value)
            for value in self
        )))

    def __len__(self) -> int:
        return len(self._inner_sequence)
