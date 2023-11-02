"""
Defines specialized collections that aren't built into any of the first or third party libraries
"""
from __future__ import annotations

import asyncio
import math

import abc
import enum
import inspect
import typing

from datetime import datetime

import pydantic
from pydantic import PrivateAttr
from pydantic.generics import GenericModel

from typing_extensions import ParamSpec

from collections.abc import Collection
from typing import Iterator

from ..events import EventRouter
from ..events import Event

_T = typing.TypeVar("_T")
_KT = typing.TypeVar("_KT", bound=typing.Hashable, covariant=True)
_VT = typing.TypeVar("_VT")
_HT = typing.TypeVar("_HT", bound=typing.Union[typing.Hashable, typing.Mapping, typing.Sequence[typing.Hashable]])

_VARIABLE_PARAMETERS = ParamSpec("_VARIABLE_PARAMETERS")
"""Represents *args and **kwargs"""


ON_ADDITION_KEY = "on_addition"
ON_REMOVAL_KEY = "on_removal"
ON_ACCESS_KEY = "on_access"
ON_UPDATE_KEY = "on_update"


def hash_hashable_map_sequence(value: _HT) -> int:
    if not isinstance(value, (str, bytes)) and isinstance(value, typing.Sequence):
        return hash(
            (
                hash_hashable_map_sequence(item) for item in value
            )
        )
    elif isinstance(value, typing.Mapping):
        return hash(
            (
                (
                    key if isinstance(key, typing.Hashable) else hash_hashable_map_sequence(key),
                    value if isinstance(value, typing.Hashable) else hash_hashable_map_sequence(value)
                )
                for key, value in sorted(value.items())
            )
        )
    else:
        return hash(value)


class CacheEntry(typing.Generic[_HT]):
    """
    An item to be stored within an AccessCache
    """
    def __init__(
        self,
        owner: AccessCache[_HT],
        identifier: str,
        data: _HT,
        last_accessed: datetime = None,
        event_router: EventRouter = None
    ):
        """
        Constructor

        Args:
            owner: The cache that will own this entry
            identifier: An identifiable name for the entry
            data: The data that will be held within the entry
            last_accessed: When the data was last accessed
            event_router: A routing mechanism used to identify and fire appropriate event handlers
        """
        self.__owner = owner
        self.__identifier = identifier
        self.__data = data
        self.__data_hash = hash_hashable_map_sequence(data)
        self.__last_accessed = last_accessed or datetime.utcnow()
        self.__event_router = event_router
        self.__leftover_tasks: typing.List[typing.Awaitable] = list()

    async def resolve_leftover_tasks(self):
        """
        Complete all lingering asynchronous tasks
        """
        tasks_to_complete = list()
        while self.__leftover_tasks:
            try:
                task = self.__leftover_tasks.pop()
                if inspect.isawaitable(task):
                    tasks_to_complete.append(task)
            except IndexError:
                # Tried to pop from an empty list - totally fine - another thread may have grabbed this
                break

        if not tasks_to_complete:
            return

        while tasks_to_complete:
            results = await asyncio.gather(*tasks_to_complete)

            tasks_to_complete = [
                result
                for result in results
                if inspect.isawaitable(result)
            ]

    @property
    def leftover_tasks(self) -> typing.List[typing.Awaitable]:
        """
        All asynchronous tasks that were created during synchronous processing
        """
        return self.__leftover_tasks

    def _update_time(self, new_time: datetime = None, *args, **kwargs):
        """
        Update the last access time for this entry

        Override for more functionality, such as data transformations or service communication
        """
        self.__last_accessed = new_time or datetime.now()

    async def _update_time_async(self, new_time: datetime = None, *args, **kwargs):
        """
        Update the last access time for this entry and allow for any implementable asynchronous functionality

        Override for more functionality, such as data transformations or service communication
        """
        self.__last_accessed = new_time or datetime.now()

    def touch(self, new_time: datetime = None, *args, **kwargs):
        """
        Update the last access time for this entry and fire all on_access events
        """
        self._update_time(new_time)
        self.entry_accessed(*args, **kwargs)

    def _set_data(self, data: _HT = None, *args, **kwargs):
        """
        Set the data within the entry

        Override for more functionality, such as data transformations or service communication
        """
        self.__data = data

    async def _async_set_data(self, data: _HT = None, *args, **kwargs):
        """
        Set the data within the entry and allow for any implementable asynchronous functionality

        Override for more functionality, such as data transformations or service communication
        """
        self.__data = data

    def update(self, data: _HT = None, *args, **kwargs):
        """
        Update the data within this entry and fire the 'on_update' event

        Triggered asynchronous functions will be stored for later resolution
        """
        self._set_data(data)
        self.entry_updated(*args, **kwargs)

    async def async_update(self, data: _HT = None, *args, resolve: bool = None, **kwargs):
        """
        Update the data within this entry and fire the 'on_update' event

        Triggered asynchronous functions will run until completion prior to returning

        Args:
            data: The value to set within the entry
            resolve: Whether to complete lingering asynchronous tasks pror to the update
        """
        await self._async_set_data(data)
        await self.entry_updated_async(*args, resolve=resolve, **kwargs)

    async def async_touch(self, new_time: datetime = None, *args, resolve: bool = None, **kwargs):
        """
        Update the access time and fire the 'on_access' event

        Triggered asynchronous functions will run until completion prior to returning

        Args:
            new_time: The time to set on the entry. Default: now
            resolve: Whether to complete lingering asynchronous tasks prior to the update
        """
        await self._update_time_async(new_time)
        await self.entry_accessed_async(*args, resolve=resolve, **kwargs)

    @property
    def identifier(self) -> str:
        return self.__identifier

    @property
    def data_hash(self) -> int:
        return self.__data_hash

    @property
    def data(self) -> _HT:
        self.touch()
        return self.__data

    @property
    async def async_data(self) -> _HT:
        await self.async_touch()
        return self.__data

    @property
    def last_accessed(self) -> datetime:
        return self.__last_accessed

    def trigger_event(self, event_name: str, *args, **kwargs) -> typing.Sequence[typing.Awaitable]:
        """
        Call all functions registered to the given event name

        All triggered asynchronous tasks will be stored and returned for later resolution

        Args:
            event_name: The name of the event whose handlers to call

        Returns:
            All asynchronous tasks that could not be awaited
        """
        if self.__event_router is None:
            return list()

        leftover_tasks: typing.List[typing.Awaitable] = list()

        if args:
            has_args = True
        else:
            has_args = False

        if kwargs:
            has_kwargs = True
        else:
            has_kwargs = False

        if has_args and has_kwargs:
            results = self.__event_router(event_name, self, *args, **kwargs)
        elif has_kwargs:
            results = self.__event_router(event_name, self, **kwargs)
        elif has_args:
            results = self.__event_router(event_name, self, *args)
        else:
            results = self.__event_router(event_name, self)

        for result in results:
            if inspect.isawaitable(result):
                leftover_tasks.append(result)

        self.__leftover_tasks.extend(leftover_tasks)
        return leftover_tasks

    def entry_deleted(self, *args, **kwargs) -> typing.Sequence[typing.Awaitable]:
        """
        Trigger the `on_removal` event

        Returns:
            All asynchronous tasks that could not be awaited
        """
        return self.trigger_event(ON_REMOVAL_KEY, *args, **kwargs)

    def entry_added(self, *args, **kwargs) -> typing.Sequence[typing.Awaitable]:
        """
        Trigger the `on_addition` event

        Returns:
            All asynchronous tasks that could not be awaited
        """
        return self.trigger_event(ON_ADDITION_KEY, *args, **kwargs)

    def entry_updated(self, *args, **kwargs) -> typing.Sequence[typing.Awaitable]:
        """
        Trigger the `on_update` event

        Returns:
            All asynchronous tasks that could not be awaited
        """
        return self.trigger_event(ON_UPDATE_KEY, *args, **kwargs)

    def entry_accessed(self, *args, **kwargs) -> typing.Sequence[typing.Awaitable]:
        """
        Trigger the `on_access` event

        Returns:
            All asynchronous tasks that could not be awaited
        """
        return self.trigger_event(ON_ACCESS_KEY, *args, **kwargs)

    async def fire(self, event_name: str, *args, resolve: bool = None, **kwargs):
        """
        Call all functions registered to the given event name

        All triggered asynchronous tasks will be completed before returning

        Args:
            event_name: The name of the event whose handlers to call
            resolve: Whether to resolve all lingering asynchronous tasks prior to firing events
        """
        if resolve is None:
            resolve = True

        if resolve:
            await self.resolve_leftover_tasks()

        if self.__event_router is None:
            return

        if args:
            has_args = True
        else:
            has_args = False

        if kwargs:
            has_kwargs = True
        else:
            has_kwargs = False

        if has_args and has_kwargs:
            firing = self.__event_router.fire(event_name, self, *args, **kwargs)
        elif has_kwargs:
            firing = self.__event_router.fire(event_name, self, **kwargs)
        elif has_args:
            firing = self.__event_router.fire(event_name, self, *args)
        else:
            firing = self.__event_router.fire(event_name, self)

        if inspect.isawaitable(firing):
            await firing

    async def entry_deleted_async(self, *args, resolve: bool = None, **kwargs):
        """
        Fire the 'on_removal' event

        Args:
            resolve: Whether to resolve all lingering asynchronous tasks before firing off the event handlers
        """
        await self.fire(ON_REMOVAL_KEY, *args, resolve=resolve, **kwargs)

    async def entry_added_async(self, *args, resolve: bool = None, **kwargs):
        """
        Fire the 'on_addition' event

        Args:
            resolve: Whether to resolve all lingering asynchronous tasks before firing off the event handlers
        """
        await self.fire(ON_ADDITION_KEY, *args, resolve=resolve, **kwargs)

    async def entry_updated_async(self, *args, resolve: bool = None, **kwargs):
        """
        Fire the 'on_update' event

        Args:
            resolve: Whether to resolve all lingering asynchronous tasks before firing off the event handlers
        """
        await self.fire(ON_UPDATE_KEY, *args, resolve=resolve, **kwargs)

    async def entry_accessed_async(self, *args, resolve: bool = None, **kwargs):
        """
        Fire the 'on_access' event

        Args:
            resolve: Whether to resolve all lingering asynchronous tasks before firing off the event handlers
        """
        await self.fire(ON_ACCESS_KEY, *args, resolve=resolve, **kwargs)

    def __eq__(self, other):
        if not isinstance(other, CacheEntry):
            return False

        return self.__data_hash == other.__data_hash

    def __le__(self, other):
        if not isinstance(other, CacheEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} <= {other.__class__.__name__}")

        return self.last_accessed <= other.last_accessed

    def __lt__(self, other):
        if not isinstance(other, CacheEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} < {other.__class__.__name__}")

        return self.last_accessed < other.last_accessed

    def __ge__(self, other):
        if not isinstance(other, CacheEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} >= {other.__class__.__name__}")

        return self.last_accessed >= other.last_accessed

    def __gt__(self, other):
        if not isinstance(other, CacheEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} < {other.__class__.__name__}")

        return self.last_accessed >= other.last_accessed

    def __str__(self):
        return f"CacheEntry: {self.identifier}"

    def __repr__(self):
        return "{" + \
            f'"identifier": {self.__data}, ' \
            f'"data_hash": {self.__data_hash}, ' \
            f'"last_accessed": "{self.last_accessed}"' + \
            "}"


# Part of Issue https://github.com/NOAA-OWP/DMOD/issues/434
#   "Make metric computations asynchronous by location"
class AccessCache(typing.Generic[_HT], typing.MutableMapping[str, CacheEntry[_HT]]):
    """
    A base class that implements a caching mechanism that organizes entries based on access time and fires events
    when adding, removing, accessing, and updating entries
    """
    def __init__(
        self,
        max_size: int = 100,
        values: typing.Mapping[str, typing.Union[_HT, CacheEntry[_HT], None]] = None,
        on_addition: typing.Union[CACHE_HANDLER, typing.Sequence[CACHE_HANDLER]] = None,
        on_removal: typing.Union[CACHE_HANDLER, typing.Sequence[CACHE_HANDLER]] = None,
        on_access: typing.Union[CACHE_HANDLER, typing.Sequence[CACHE_HANDLER]] = None,
        on_update: typing.Union[CACHE_HANDLER, typing.Sequence[CACHE_HANDLER]] = None,
        event_router: EventRouter = None,
        **kwargs
    ):
        """
        Constructor

        Args:
            max_size: The maximum number of items that this cache may contain. Non-positive numbers or None will store all data
            values: Preexisting data to add to the cache
            on_addition: Handlers to call when an item is added to the cache
            on_removal: Handlers to call when an item is removed from the cache
            on_access: Handlers to call when an item in the cache is accessed
            on_update: Handlers to call when an item in the cache is updated
            event_router: An EventRouter that will call appropriate functions when events are triggered
            kwargs: Additional items to store in the cache
        """
        if values is None:
            values = {}

        if on_addition is None:
            on_addition = list()

        if on_removal is None:
            on_removal = list()

        if on_access is None:
            on_access = list()

        if on_update is None:
            on_update = list()

        self.__event_router = event_router or EventRouter()

        self.__event_router.register_handler(ON_ADDITION_KEY, on_addition)
        self.__event_router.register_handler(ON_REMOVAL_KEY, on_removal)
        self.__event_router.register_handler(ON_ACCESS_KEY, on_access)
        self.__event_router.register_handler(ON_UPDATE_KEY, on_update)

        self.__leftover_tasks: typing.List[typing.Awaitable] = list()

        self.__internal_cache: typing.Dict[str, CacheEntry[_HT]] = dict()
        self.__earliest: typing.Optional[CacheEntry[_HT]] = None
        self.__max_size = max_size if isinstance(max_size, (int, float)) and max_size > 0 else math.inf

        for key, value in values:
            self[key] = value

        for key, value in kwargs.items():
            self[key] = value

    async def resolve_leftover_tasks(self):
        """
        Complete any hanging asynchronous tasks
        """
        entry_tasks = list()

        for entry in self.__internal_cache.values():
            if entry.leftover_tasks:
                entry_tasks.append(entry.resolve_leftover_tasks())

        if entry_tasks:
            await asyncio.gather(*entry_tasks)

        tasks_to_complete: typing.List[typing.Awaitable] = list()

        while len(self.__leftover_tasks) > 0:
            try:
                tasks_to_complete.append(self.__leftover_tasks.pop())
            except IndexError:
                # Tried to pop from an empty list - totally fine - another thread may have grabbed this
                break

        if not tasks_to_complete:
            return

        while len(tasks_to_complete) > 0:
            task = tasks_to_complete.pop()

            if not inspect.isawaitable(task):
                continue

            tasks_to_complete.append(await task)

        self.__update_earliest()

    def __setitem__(self, key: str, data: typing.Union[CacheEntry[_HT], _HT, None]) -> None:
        """
        Add or update an item in the cache

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier for the object
            data: The data to set
        """
        try:
            self.lock()

            if key in self:
                entry = self.__internal_cache[key]

                if isinstance(data, CacheEntry):
                    entry.update(data.data)
                else:
                    entry.update(data)
            else:
                if self.__max_size > 0:
                    while len(self.__internal_cache) >= self.__max_size:
                        self.popitem()

                entry = self.construct_entry(key, data)

                self.__internal_cache[key] = entry

                entry.entry_added()

            self.__update_earliest()
        finally:
            self.release()

    def construct_entry(self, key: str, data: typing.Union[_HT, CacheEntry[_HT]] = None) -> CacheEntry[_HT]:
        """
        Create a new entry that will fit into the cache

        Args:
            key: The identifier for the new item
            data: The data to put inside the entry

        Returns:
            A new entry bearing everything needed to function within this cache
        """
        if isinstance(data, CacheEntry):
            data = data.data

        return CacheEntry(owner=self, identifier=key, data=data, event_router=self.__event_router)

    def touch(self, identifier: str, new_time: datetime = None):
        """
        Update cache entry access time

        Updating the access time will prevent the entry from being removed upon addition if items need to be removed.

        Triggered asynchronous tasks will be stored for later completion

        Args:
            identifier: The identifier for the entry to update
            new_time: The time to set the access time to. Defaults to now
        """
        try:
            self.lock()
            if identifier in self:
                self.__internal_cache[identifier].touch(new_time)
            else:
                self[identifier] = None

            self.__update_earliest()
        finally:
            self.release()

    async def async_set(
        self,
        key: str,
        data: typing.Union[CacheEntry[_HT], _HT, None],
        resolve: bool = None
    ) -> None:
        """
        Set or update an entry. Completes all asynchronous triggered events before returning

        Args:
            key: The identifier for the entry to add or update
            data: The new data that should be present
            resolve: Complete all present asynchronous tasks prior to operating
        """
        if resolve is None:
            resolve = True

        if resolve:
            await self.resolve_leftover_tasks()

        try:
            self.lock()

            if key in self:
                await self.__internal_cache[key].async_update(data)
            else:
                if self.__max_size > 0:
                    while len(self.__internal_cache) >= self.__max_size:
                        await self.async_popitem()

                entry = self.construct_entry(key, data)

                self.__internal_cache[key] = entry

                await entry.entry_added_async(self)

            self.__update_earliest()
        finally:
            self.release()

    def __update_earliest(self):
        """
        Determine and store a reference to the earliest entry in the cache.

        The earliest will be the first to be removed if the cache reaches capacity.
        """
        self.__earliest = None
        if len(self.__internal_cache) == 0:
            self.__earliest = 0
        else:
            for entry in self.__internal_cache.values():
                if self.__earliest is None:
                    self.__earliest = entry
                else:
                    if entry.last_accessed < self.__earliest.last_accessed:
                        self.__earliest = entry

    def remove(self, key: str) -> typing.Optional[_T]:
        """
        Remove an item based on its identifier

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier of the entry to remove

        Returns:
            The value that was stored at the key
        """
        try:
            self.lock()
            if key in self:
                data = self.get(key)
                del self[key]
                return data
        finally:
            self.release()
        return None

    async def remove_async(self, key: str, resolve: bool = None) -> typing.Optional[_T]:
        """
        Remove an item based on its identifier

        Completes all triggered asynchronous tasks prior to returning

        Args:
            key: The identifier for the entry to remove
            resolve: Whether to complete all hanging asynchronous tasks before removal

        Returns:
            The data from the removed entry
        """
        if resolve is None:
            resolve = True

        if resolve:
            await self.resolve_leftover_tasks()

        try:
            self.lock()

            if key in self:
                entry = self.__internal_cache.pop(key)
                await entry.entry_deleted_async()
                return entry.data
        finally:
            self.release()
            self.__update_earliest()

        return None

    def __delitem__(self, key: str) -> None:
        """
        Remove an entry from the cache

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier for the item to remove
        """
        try:
            self.lock()

            if key in self:
                entry = self.__internal_cache[key]
                del self.__internal_cache[key]

                entry.entry_deleted()

                # Add the resolution function to the collection of leftover tasks to ensure its resolution
                # is called since its leftover tasks cannot be found once it has been removed
                self.__leftover_tasks.append(entry.resolve_leftover_tasks())
        finally:
            self.release()
            self.__update_earliest()

    def __getitem__(self, key: str) -> typing.Union[_HT, None]:
        """
        Get data from the Cache

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier for the entry to get data from

        Returns:
            The data from within the entry if it was present
        """
        try:
            self.lock()
            if key in self:
                entry = self.__internal_cache.get(key)
                return entry.data
            else:
                return None
        finally:
            self.release()
            self.__update_earliest()

    def get(self, key: str, default: typing.Any = None) -> typing.Union[_HT, None]:
        """
        Get data from the cache or a default if it is not present

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier for the entry to get data from
            default: A value to return if the entry was not present

        Returns:
            The value of the entry or the default
        """
        return self[key] or default

    async def get_async(
        self,
        key: str,
        default: typing.Any = None,
        resolve: bool = None
    ) -> typing.Union[bytes, typing.Any]:
        """
        Get data from the cache or a default if it is not present

        All triggered asynchronous tasks will be completed prior to return

        Args:
            key: The identifier for the entry to get data from
            default: A value to return if the entry was not present
            resolve: Whether to complete all leftover tasks prior to retrieving data

        Returns:
            The value of the entry or the default
        """
        if resolve is None:
            resolve = True

        if resolve:
            await self.resolve_leftover_tasks()

        try:
            self.lock()
            if key in self:
                return await self.__internal_cache.get(key).async_data
            else:
                return default
        finally:
            self.release()
            self.__update_earliest()

    def lock(self):
        """
        Lock the cache to prevent other threads or processes from editing data

        Does nothing by default. Override in subclass to add locking capability.
        """
        pass

    def release(self):
        """
        Unlock the cache to allow other threads or processes to edit data

        Does nothing by default. Override in subclass to add locking capability.
        """
        pass

    def is_locked(self) -> bool:
        """
        Whether the cache is currently locked

        Does nothing by default. Override in subclass to add locking capability.
        """
        return False

    def update(
        self,
        other: typing.Union[AccessCache[_HT], typing.Mapping[str, typing.Union[CacheEntry[_HT], _HT, None]]],
        **kwargs
    ) -> None:
        """
        Merge data into this cache

        Triggered asynchronous tasks will be stored for later completion

        Args:
            other: Another cache or mapping of data to merge into this cache
            kwargs: Keyvalue pairs of data to add to this cache
        """
        try:
            self.lock()
            if isinstance(other, AccessCache):
                for entry in other:
                    self[entry.identifier] = self.construct_entry(entry.identifier, entry)
            elif isinstance(other, typing.Mapping):
                for key, value in other.items():
                    self[key] = self.construct_entry(key, value)
            else:
                raise ValueError(f"Cannot update a AccessCache with a value of type '{type(other)}'")

            for key, value in kwargs.items():
                self[key] = self.construct_entry(key, value)
        finally:
            self.release()
            self.__update_earliest()

    def popitem(self) -> typing.Optional[typing.Tuple[str, _HT]]:
        """
        Remove the oldest item in the cache

        Triggered asynchronous tasks will be stored for later completion

        Returns:
            The identifier and data of the data that was removed
        """
        try:
            self.lock()
            if len(self) == 0:
                return None

            key = self.__earliest.identifier
            data = self.__earliest.data

            del self[key]

            return key, data
        finally:
            self.release()
            self.__update_earliest()

    async def async_popitem(self, resolve: bool = None) -> typing.Optional[typing.Tuple[str, _HT]]:
        """
        Remove the oldest item in the cache

        Triggered asynchronous tasks will be finished prior to returning

        Args:
            resolve: Whether to complete all stored tasks prior to removing the item

        Returns:
            The identifier and data of the data that was removed
        """
        if resolve is None:
            resolve = True

        if resolve:
            await self.resolve_leftover_tasks()

        try:
            self.lock()

            if len(self) == 0:
                return None

            key = self.__earliest.identifier
            data = self.__earliest.data

            await self.remove_async(key)

            return key, data
        finally:
            self.release()
            self.__update_earliest()

    def __order_entries(self, descending: bool = None) -> typing.Sequence[CacheEntry[_HT]]:
        """
        Create a collection of all cached data in access time order

        Args:
            descending: Whether to order entries with the most recently accessed items first

        Returns:
            A sequence of all entries in access time order
        """
        try:
            self.lock()
            if descending is None:
                descending = True

            sorted_values = sorted(self.values(), key=lambda entry: entry.last_accessed)

            if descending:
                sorted_values = reversed(sorted_values)

            return sorted_values
        finally:
            self.release()

    def set_on_addition(self, handler: typing.Callable[
        [Event, CacheEntry[_HT], AccessCache[_HT], typing.Tuple[typing.Any, ...], typing.Dict[str, typing.Any]],
        typing.Any
    ]):
        """
        Add an event handler for the 'on_addition' event. This event will fire when an item is added

        Args:
            handler: The handler function to add
        """
        if isinstance(handler, typing.Callable):
            self.__event_router.register_handler(ON_ADDITION_KEY, handler)
        elif handler is not None:
            raise TypeError(f"Only functions and methods may be set as event handlers. Received '{type(handler)}'")

    def set_on_removal(self, handler: CACHE_HANDLER):
        """
        Add an event handler for the 'on_removal' event. This will fire when an item is removed.

        Args:
            handler: The handler function to add
        """
        if isinstance(handler, typing.Callable):
            self.__event_router.register_handler(ON_REMOVAL_KEY, handler)
        elif handler is not None:
            raise TypeError(f"Only functions and methods may be set as event handlers. Received '{type(handler)}'")

    def set_on_access(self, handler: typing.Callable[
        [Event, CacheEntry[_HT], typing.Optional[AccessCache[_HT]], _VARIABLE_PARAMETERS],
        typing.Any
    ]):
        """
        Add an event handler for the 'on_access' event. This will fire when an item is accessed

        Args:
            handler: The handler function to add
        """
        if isinstance(handler, typing.Callable):
            self.__event_router.register_handler(ON_ACCESS_KEY, handler)
        elif handler is not None:
            raise TypeError(f"Only functions and methods may be set as event handlers. Received '{type(handler)}'")

    def set_on_update(self, handler: CACHE_HANDLER):
        """
        Add an event handler for the `on_update` event. This will fire when a preexisting item is updated

        Args:
            handler: The handler function to add
        """
        if isinstance(handler, typing.Callable):
            self.__event_router.register_handler(ON_UPDATE_KEY, handler)
        elif handler is not None:
            raise TypeError(f"Only functions and methods may be set as event handlers. Received '{type(handler)}'")

    def __len__(self) -> int:
        return len(self.__internal_cache)

    def __contains__(self, key: str) -> bool:
        return key in self.__internal_cache

    def __iter__(self) -> Iterator[CacheEntry[_HT]]:
        return iter(self.__order_entries())


CACHE_HANDLER = typing.Callable[
    [
        Event,
        CacheEntry[_HT],
        _VARIABLE_PARAMETERS
    ],
    typing.Union[typing.Coroutine, typing.Any]
]
"""The signature for a function that may serve as a handler for events within an AccessCache"""


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

    Elements do not have to be hashable nor unique

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