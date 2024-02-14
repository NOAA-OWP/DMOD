"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing
import abc

from .constants import CollectionEvent
from .constants import MapHandler
from .constants import SequenceHandler

_T = typing.TypeVar("_T")
_KT = typing.TypeVar("_KT", bound=typing.Hashable, covariant=True)
_VT = typing.TypeVar("_VT")
_HT = typing.TypeVar("_HT", bound=typing.Union[typing.Hashable, typing.Mapping, typing.Sequence[typing.Hashable]])


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

    def get(self, __key: _KT, default=None):
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

    def pop(self, __key: _KT, default=None) -> _VT:
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