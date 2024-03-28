"""
Defines a catalog that may contain and share data between processes while triggering operations upon alteration.
"""
from __future__ import annotations

import typing
import math

from datetime import datetime

from .eventful_collections import EventfulMap


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

HashableTypeT = typing.TypeVar(
    "HashableTypeT",
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
        typing.Hashable,
        None
    ]
)
"""A type of item that may either be hashed or we have a method of hashing (such as `hash_hashable_map_sequence`)"""


def hash_hashable_map_sequence(value: HashableTypeT) -> int:
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

    if not isinstance(value, (str, bytes)) and isinstance(value, typing.Iterable):
        return hash(
            tuple(
                hash_hashable_map_sequence(item) for item in value
            )
        )

    if isinstance(value, ToDictProtocol):
        return hash_hashable_map_sequence(value.to_dict())

    if isinstance(value, ToJsonProtocol):
        return hash_hashable_map_sequence(value.to_json())

    return hash(value)


class CatalogEntry(typing.Generic[HashableTypeT]):
    """
    An item to be stored within an AccessCache
    """
    def __init__(
        self,
        identifier: str,
        data: HashableTypeT,
        last_accessed: datetime = None,
    ):
        """
        Constructor

        Args:
            identifier: An identifiable name for the entry
            data: The data that will be held within the entry
            last_accessed: When the data was last accessed
        """
        self.__identifier = identifier
        self.__data = data.data if isinstance(data, CatalogEntry) else data
        self.__data_hash = hash_hashable_map_sequence(data)
        self.__last_accessed = last_accessed or datetime.utcnow()

    def __reduce__(self):
        return (
            self.__class__,
            (
                self.__identifier,
                self.__data,
                self.__last_accessed
            )
        )

    def _update_time(self, new_time: datetime = None):
        """
        Update the last access time for this entry

        Override for more functionality, such as data transformations or service communication
        """
        self.__last_accessed = new_time or datetime.now()

    def touch(self, new_time: datetime = None):
        """
        Update the last access time for this entry and fire all on_access events
        """
        self._update_time(new_time)

    def _set_data(self, data: HashableTypeT):
        """
        Set the data within the entry

        Override for more functionality, such as data transformations or service communication
        """
        self.__data = data
        self.__data_hash = hash_hashable_map_sequence(data)
        self.touch()

    @property
    def identifier(self) -> str:
        """
        The identifier/key of the entry
        """
        return self.__identifier

    @property
    def data_hash(self) -> int:
        """
        A hash for the data that is contained
        """
        return self.__data_hash

    @property
    def data(self) -> HashableTypeT:
        """
        Get the stored data
        """
        self.touch()
        return self.__data

    @data.setter
    def data(self, new_value: HashableTypeT):
        self._set_data(data=new_value)

    @property
    def last_accessed(self) -> datetime:
        """
        The last time that this entry was accessed
        """
        return self.__last_accessed

    def __eq__(self, other):
        if isinstance(other, type(self.data)):
            return self.data == hash_hashable_map_sequence(other)

        if not isinstance(other, CatalogEntry):
            return False

        return self.data_hash == other.data_hash

    def __hash__(self):
        return self.data_hash

    def __le__(self, other):
        if isinstance(other, type(self.data)):
            return self.data < other or self.data_hash == hash_hashable_map_sequence(other)

        if not isinstance(other, CatalogEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} <= {other.__class__.__name__}")

        return self.last_accessed <= other.last_accessed

    def __lt__(self, other):
        if isinstance(other, type(self.data)):
            return self.data < other

        if not isinstance(other, CatalogEntry):
            raise TypeError(f"Cannot perform {type(self.data)} < {type(other)}")

        return self.last_accessed < other.last_accessed

    def __ge__(self, other):
        if not isinstance(other, CatalogEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} >= {other.__class__.__name__}")

        return self.last_accessed >= other.last_accessed

    def __gt__(self, other):
        if not isinstance(other, CatalogEntry):
            raise TypeError(f"Cannot perform {self.__class__.__name__} < {other.__class__.__name__}")

        return self.last_accessed >= other.last_accessed

    def __str__(self):
        return f"CacheEntry: {self.identifier} @ {self.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}"

    def __repr__(self):
        return "{" + \
            f'"identifier": {self.__data}, ' \
            f'"data_hash": {self.__data_hash}, ' \
            f'"last_accessed": "{self.last_accessed}"' + \
            "}"


# Part of Issue https://github.com/NOAA-OWP/DMOD/issues/434
#   "Make metric computations asynchronous by location"
class InputCatalog(EventfulMap[str, CatalogEntry[HashableTypeT]], typing.Generic[HashableTypeT]):
    """
    A base class that implements a caching mechanism that organizes entries based on access time and fires events
    when adding, removing, accessing, and updating entries
    """

    def __init__(
        self,
        max_size: int = 100,
        *,
        values: typing.Mapping[str, typing.Union[HashableTypeT, CatalogEntry[HashableTypeT], None]] = None
    ):
        """
        Constructor

        Args:
            max_size: The maximum number of items that this cache may contain. Values other than positive numbers will
                cause the cache to become unbounded
            values: Preexisting data to add to the cache
            kwargs: Additional items to store in the cache
        """
        if values is None:
            values = {}

        super().__init__(contents=values)

        self.__earliest: typing.Optional[CatalogEntry[HashableTypeT]] = None
        self.__max_size = max_size if isinstance(max_size, (int, float)) and max_size > 0 else math.inf

    async def commit(self):
        """
        Complete all asynchronous tasks that have yet to be awaited
        """
        await super().commit()
        self.__update_earliest()

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
                self.inner_map()[identifier].touch(new_time)
            else:
                self[identifier] = None

            self.__update_earliest()
        finally:
            self.release()

    def __setitem__(self, key: str, data: typing.Union[HashableTypeT, None]) -> None:
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
                self[key].data = data.data if isinstance(data, CatalogEntry) else data
            else:
                if not isinstance(data, CatalogEntry):
                    data = CatalogEntry(key, data)

                while self.__max_size <= len(self):
                    self.popitem()

                super().__setitem__(key, data)
            self.__update_earliest()
        finally:
            self.release()

    async def async_set(
        self,
        key: str,
        data: typing.Union[CatalogEntry[HashableTypeT], HashableTypeT],
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
            await self.commit()

        try:
            self[key] = data
        finally:
            await self.commit()

    def __update_earliest(self):
        """
        Determine and store a reference to the earliest entry in the cache.

        The earliest will be the first to be removed if the cache reaches capacity.
        """
        self.__earliest = None
        if len(self) == 0:
            self.__earliest = 0
        else:
            for entry in self.values():
                if self.__earliest is None:
                    self.__earliest = entry
                else:
                    if entry.last_accessed < self.__earliest.last_accessed:
                        self.__earliest = entry

    def pop(self, __key: str, default=None) -> HashableTypeT:
        """
        Remove and retrieve an item based off of its name

        Args:
            __key: The key of the item to remove
            default: The default value to return if the key is not present

        Returns:
            Either the value that was removed or some default
        """
        try:
            self.lock()
            popped_entry = super().pop(__key, default)

            if isinstance(popped_entry, CatalogEntry):
                popped_entry = popped_entry.data

            return popped_entry
        finally:
            self.__update_earliest()
            self.release()

    def popitem(self) -> typing.Optional[typing.Tuple[str, HashableTypeT]]:
        """
        Remove the oldest item in the cache

        Triggered asynchronous tasks will be stored for later completion

        Returns:
            The identifier and data of the data that was removed
        """
        key = self.__earliest.identifier
        return self.pop(key)

    async def async_popitem(self, resolve: bool = None) -> typing.Optional[typing.Tuple[str, HashableTypeT]]:
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
            await self.commit()

        try:
            return self.popitem()
        finally:
            await self.commit()

    async def remove_async(self, key: str, resolve: bool = None) -> typing.Optional[HashableTypeT]:
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
            await self.commit()

        try:
            del self[key]
        finally:
            await self.commit()

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
            super().__delitem__(key)
        finally:
            self.__update_earliest()
            self.release()

    def __getitem__(self, key: str) -> typing.Union[HashableTypeT, None]:
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

            if key not in self:
                raise KeyError(f"Key: '{key}' not found in instance of {self.__class__.__name__}")

            entry = super().get(key)

            if isinstance(entry, CatalogEntry):
                entry.touch()
                entry = entry.data

            return entry
        finally:
            self.__update_earliest()
            self.release()

    def get(self, key: str, default: T = None) -> typing.Union[HashableTypeT, T]:
        """
        Get data from the cache or a default if it is not present

        Triggered asynchronous tasks will be stored for later completion

        Args:
            key: The identifier for the entry to get data from
            default: A value to return if the entry was not present

        Returns:
            The value of the entry or the default
        """
        return self[key] if key in self else default

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
            await self.commit()

        try:
            return self.get(key, default)
        finally:
            await self.commit()

    def lock(self):
        """
        Lock the cache to prevent other threads or processes from editing data

        Does nothing by default. Override in subclass to add locking capability.
        """

    def release(self):
        """
        Unlock the cache to allow other threads or processes to edit data

        Does nothing by default. Override in subclass to add locking capability.
        """

    def is_locked(self) -> bool:
        """
        Whether the cache is currently locked

        Does nothing by default. Override in subclass to add locking capability.
        """
        return False

    def update(
        self,
        other: typing.Union[
            InputCatalog[HashableTypeT],
            typing.Mapping[str, typing.Union[CatalogEntry[HashableTypeT], HashableTypeT, None]]
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
            if isinstance(other, InputCatalog):
                for entry in other.values():
                    self[entry.identifier] = CatalogEntry(entry.identifier, entry)
            elif isinstance(other, typing.Mapping):
                for key, value in other.items():
                    self[key] = CatalogEntry(key, value)
            else:
                raise ValueError(f"Cannot update a {self.__class__.__name__} with a value of type '{type(other)}'")

            for key, value in kwargs.items():
                self[key] = CatalogEntry(key, value)
        finally:
            self.__update_earliest()
            self.release()

    def __order_entries(self, descending: bool = None) -> typing.Sequence[HashableTypeT]:
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

            sorted_wrappers = sorted(self.values(), key=lambda entry: entry.last_accessed, reverse=descending)
            sorted_values = [
                wrapper.data
                for wrapper in sorted_wrappers
            ]
            return sorted_values
        finally:
            self.release()

    def __iter__(self) -> typing.Iterator[CatalogEntry[HashableTypeT]]:
        return iter(self.__order_entries())