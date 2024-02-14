#!/usr/bin/env python3
import abc
import typing

from dmod.core.common import AccessCache
from dmod.core.events import EventRouter

from .. import specification


class Backend(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_backend_type(cls) -> str:
        ...

    @classmethod
    def build_event_router(cls) -> EventRouter:
        router = EventRouter(fail_on_missing_event=False)
        return router

    @classmethod
    def create_cache(cls, size: int = None) -> AccessCache:
        router = cls.build_event_router()
        cache = AccessCache(max_size=size, event_router=router)
        return cache

    def __init__(
        self,
        definition: specification.BackendSpecification,
        cache: AccessCache[bytes] = None,
        cache_size: int = None
    ):
        self.__definition = definition
        self.__cache: AccessCache[bytes] = cache or self.create_cache(cache_size)
        self._sources: typing.Sequence[str] = list()

    @property
    def cache(self) -> AccessCache[bytes]:
        return self.__cache

    @property
    def sources(self) -> typing.Sequence:
        """
        The raw sources that produce data
        """
        return [source for source in self._sources]

    def _add_to_cache(self, identifier: str, data: bytes):
        self.cache[identifier] = data

    def _update_access_time(self, identifier: str):
        self.cache.touch(identifier)

    @abc.abstractmethod
    def read(self, identifier: str, store_data: bool = None) -> bytes:
        """
        Returns:
            The raw data accessible via the backend
        """
        pass

    @abc.abstractmethod
    def read_stream(self, identifier: str, store_data: bool = None):
        """
        Get the data in the form of a bytes stream

        Args:
            identifier: The identifier for the data to retrieve a stream for
            store_data: Whether the data retrieved should be stored

        Returns:
            An object with a `read` function that may produce the data
        """
        pass

    @property
    def type(self) -> str:
        return self.__definition.backend_type

    @property
    def format(self) -> str:
        return self.__definition.format

    @property
    def address(self) -> str:
        return self.__definition.address

    @property
    def definition(self) -> specification.BackendSpecification:
        return self.__definition

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        return self.__definition.properties.get(key, default)

    def __getitem__(self, key: str) -> typing.Any:
        return self.__definition.properties[key]

    def __len__(self):
        return len(self._sources)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._sources

    def __iter__(self):
        return self._sources.__iter__()
