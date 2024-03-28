"""
Defines the base structure for an object that may load input data
"""
import abc
import typing

from dmod.core.common import InputCatalog

from .. import specification


class Backend(abc.ABC):
    """
    Structure used to load input data
    """
    @classmethod
    @abc.abstractmethod
    def get_backend_type(cls) -> str:
        """
        The type of data that this backend loads
        """

    def __init__(
        self,
        definition: specification.BackendSpecification,
        cache: InputCatalog[bytes]
    ):
        if cache is None:
            raise ValueError("No cache was passed to a backend")

        self.__definition = definition
        self.__cache: InputCatalog[bytes] = cache
        self._sources: typing.Sequence[str] = []

    @property
    def cache(self) -> InputCatalog[bytes]:
        """
        The storage mechanism for any persisted input data
        """
        return self.__cache

    @property
    def sources(self) -> typing.Sequence:
        """
        The raw sources that produce data
        """
        return list(self._sources)

    def _add_to_cache(self, identifier: str, data: bytes):
        """
        Adds data to the cache for later retrieval

        Args:
            identifier: An identifier used to reference the data later
            data: The raw data to be stored
        """
        self.cache[identifier] = data

    @abc.abstractmethod
    def read(self, identifier: str, store_data: bool = None) -> bytes:
        """
        Returns:
            The raw data accessible via the backend
        """

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

    @property
    def type(self) -> str:
        """
        The type of backend that the definition desired
        """
        return self.__definition.backend_type

    @property
    def format(self) -> str:
        """
        The format of the expected input data according to the definition
        """
        return self.__definition.format

    @property
    def address(self) -> str:
        """
        Where to find data for the backend
        """
        return self.__definition.address

    @property
    def definition(self) -> specification.BackendSpecification:
        """
        The definition for how this backend was supposed to be created
        """
        return self.__definition

    def __len__(self):
        return len(self._sources)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._sources

    def __iter__(self):
        return self._sources.__iter__()
