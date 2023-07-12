#!/usr/bin/env python3
import abc
import numbers
import typing

from datetime import datetime

from .. import specification


class Backend(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_backend_type(cls) -> str:
        ...

    def __init__(self, definition: specification.BackendSpecification, cache_limit: int = None):
        self.__definition = definition
        self._raw_data: typing.Dict[str, typing.Tuple[datetime, bytes]] = dict()
        self.__cache_limit = cache_limit if cache_limit else -1
        self._sources: typing.Sequence[str] = list()

    @property
    def sources(self) -> typing.Sequence:
        """
        The raw sources that produce data
        """
        return [source for source in self._sources]

    def _add_to_cache(self, identifier: str, data: bytes):
        if identifier in self._raw_data:
            return

        if 0 < self.__cache_limit < len(self._sources):
            ordered_sources = [
                {
                    "identifier": identifier,
                    "added_date": date_and_data[0]
                }
                for identifier, date_and_data in self._raw_data.items()
            ]
            ordered_sources = sorted(ordered_sources, key=lambda source: source['added_date'])
            del self._raw_data[ordered_sources[0]['identifier']]

        self._raw_data[identifier] = (datetime.utcnow(), data)

    def _update_access_time(self, identifier: str):
        self._raw_data[identifier] = datetime.utcnow(), self._raw_data[identifier][1]

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
    def cache_limit(self) -> numbers.Number:
        return self.__cache_limit

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
