"""
Define a cache that may contain and share data between processes while triggering operations upon alteration.
"""
from __future__ import annotations

import asyncio
import inspect
import typing
import math

from datetime import datetime

try:
    from typing import ParamSpec
    from typing import Concatenate
except ImportError:
    from typing_extensions import ParamSpec
    from typing_extensions import Concatenate

from .constants import EntryType

from ...events import Event
from ...events import EventRouter

ON_ADDITION_KEY = "on_addition"
ON_REMOVAL_KEY = "on_removal"
ON_ACCESS_KEY = "on_access"
ON_UPDATE_KEY = "on_update"


@typing.runtime_checkable
class ToDictProtocol(typing.Protocol):
    """
    A type of object that has a `to_dict` method that converts itself into a of strings to values
    """
    def to_dict(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        ...


@typing.runtime_checkable
class ToJsonProtocol(typing.Protocol):
    """
    A type of object that has a `to_json` method that converts itself into a a string interpretation of a dictionary
    """
    def to_json(self, *args, **kwargs) -> str:
        ...


T = typing.TypeVar("T")
"""Any sort of class that might indicate consistency"""

HashableType = typing.TypeVar(
    "HashableType",
    bound=typing.Union[
        typing.Mapping[
            str,
            typing.Union[
                typing.Hashable,
                typing.Mapping[str, typing.ForwardRef("HashableType")],
                typing.Iterable[typing.ForwardRef("HashableType")]
            ]
        ],
        typing.Iterable[
            typing.Union[
                typing.Hashable,
                typing.Mapping[
                    str,
                    typing.Union[
                        typing.Hashable,
                        typing.Mapping[str, typing.ForwardRef("HashableType")],
                        typing.Iterable[typing.ForwardRef("HashableType")]
                    ]
                ],
                typing.Iterable[typing.ForwardRef("HashableType")]
            ]
        ],
        ToJsonProtocol,
        ToDictProtocol,
        typing.Hashable
    ]
)
"""A type of item that may either be hashed or we have a method of hashing (such as `hash_hashable_map_sequence`)"""


_VARIABLE_PARAMETERS = ParamSpec("_VARIABLE_PARAMETERS")
"""Represents *args and **kwargs"""


def hash_hashable_map_sequence(value: HashableType) -> int:
    """
    Generate the hash or hash of a collection of objects

    Args:
        value: The value to be hashed

    Returns:
        The result of the hashing operation
    """
    def key_function(element: T) -> int:
        """
        Function used to provided a value used to act as the key value for sorting

        Args:
            element: The value serving as the initial key for sorting

        Returns:
            A representation of that key value that may be used for comparisons
        """
        if isinstance(element, typing.Hashable):
            return hash(element)
        else:
            return hash(str(element))

    if isinstance(value, typing.Mapping):
        return hash(
            tuple(
                (
                    key if isinstance(key, typing.Hashable) else hash_hashable_map_sequence(key),
                    value if isinstance(value, typing.Hashable) else hash_hashable_map_sequence(value)
                )
                for key, value in sorted(value.items(), key=key_function)
            )
        )
    elif not isinstance(value, (str, bytes)) and isinstance(value, typing.Iterable):
        return hash(
            tuple(
                hash_hashable_map_sequence(item) for item in value
            )
        )
    elif isinstance(value, ToDictProtocol):
        return hash_hashable_map_sequence(value.to_dict())
    elif isinstance(value, ToJsonProtocol):
        return hash_hashable_map_sequence(value.to_json())
    else:
        return hash(value)


class CacheEntry(typing.Generic[HashableType]):
    """
    An item to be stored within an AccessCache
    """
    def __init__(
        self,
        owner: AccessCache[HashableType],
        identifier: str,
        data: HashableType,
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

    def _set_data(self, data: HashableType = None, *args, **kwargs):
        """
        Set the data within the entry

        Override for more functionality, such as data transformations or service communication
        """
        self.__data = data

    async def _async_set_data(self, data: HashableType = None, *args, **kwargs):
        """
        Set the data within the entry and allow for any implementable asynchronous functionality

        Override for more functionality, such as data transformations or service communication
        """
        self.__data = data

    def update(self, data: HashableType = None, *args, **kwargs):
        """
        Update the data within this entry and fire the 'on_update' event

        Triggered asynchronous functions will be stored for later resolution
        """
        self._set_data(data)
        self.entry_updated(*args, **kwargs)

    async def async_update(self, data: HashableType = None, *args, resolve: bool = None, **kwargs):
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
    def data(self) -> HashableType:
        self.touch()
        return self.__data

    @property
    async def async_data(self) -> HashableType:
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

        while inspect.isawaitable(firing):
            firing = await firing

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
class AccessCache(typing.Generic[HashableType], typing.MutableMapping[str, CacheEntry[HashableType]]):
    """
    A base class that implements a caching mechanism that organizes entries based on access time and fires events
    when adding, removing, accessing, and updating entries
    """
    def __init__(
        self,
        max_size: int = 100,
        values: typing.Mapping[str, typing.Union[HashableType, CacheEntry[HashableType], None]] = None,
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
            max_size: The maximum number of items that this cache may contain. Values other than positive numbers will
                cause the cache to become unbounded
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

        self.__internal_cache: typing.Dict[str, CacheEntry[HashableType]] = dict()
        self.__earliest: typing.Optional[CacheEntry[HashableType]] = None
        self.__max_size = max_size if isinstance(max_size, (int, float)) and max_size > 0 else math.inf

        for key, value in values.items():
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

    def __setitem__(self, key: str, data: typing.Union[CacheEntry[HashableType], HashableType, None]) -> None:
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

    def construct_entry(self, key: str, data: typing.Union[HashableType, CacheEntry[HashableType]] = None) -> CacheEntry[HashableType]:
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
        data: typing.Union[CacheEntry[HashableType], HashableType, None],
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

    def remove(self, key: str) -> typing.Optional[EntryType]:
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

    async def remove_async(self, key: str, resolve: bool = None) -> typing.Optional[EntryType]:
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

    def __getitem__(self, key: str) -> typing.Union[HashableType, None]:
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

    def get(self, key: str, default: T = None) -> typing.Union[HashableType, T]:
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
        default: T = None,
        resolve: bool = None
    ) -> typing.Union[bytes, T]:
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
        other: typing.Union[
            AccessCache[HashableType],
            typing.Mapping[str, typing.Union[CacheEntry[HashableType], HashableType, None]]
        ],
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

    def popitem(self) -> typing.Optional[typing.Tuple[str, HashableType]]:
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

    async def async_popitem(self, resolve: bool = None) -> typing.Optional[typing.Tuple[str, HashableType]]:
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

    def __order_entries(self, descending: bool = None) -> typing.Sequence[CacheEntry[HashableType]]:
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

    def set_on_addition(
        self,
        handler: typing.Callable[
            Concatenate[Event, CacheEntry[HashableType], AccessCache[HashableType], _VARIABLE_PARAMETERS],
            typing.Any
        ]
    ) -> None:
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

    def set_on_access(
        self,
        handler: typing.Callable[
            [Event, CacheEntry[HashableType], typing.Optional[AccessCache[HashableType]], _VARIABLE_PARAMETERS],
            typing.Any
        ]
    ) -> None:
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

    def __iter__(self) -> typing.Iterator[CacheEntry[HashableType]]:
        return iter(self.__order_entries())


CACHE_HANDLER = typing.Callable[
    Concatenate[
        Event,
        CacheEntry[HashableType],
        _VARIABLE_PARAMETERS
    ],
    typing.Union[typing.Coroutine, typing.Any]
]
"""The signature for a function that may serve as a handler for events within an AccessCache"""