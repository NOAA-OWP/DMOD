import abc

import pandas

from . import backends


class Retriever(abc.ABC):
    def __init__(self, definition):
        self._definition = definition
        self._backend = backends.get_backend(definition.backend)

    @classmethod
    @abc.abstractmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """
        ...

    @property
    @abc.abstractmethod
    def definition(self):
        """
        Returns:
            The specification for this retriever
        """
        ...

    @property
    def backend(self) -> backends.Backend:
        """
        Returns:
            The class used to load the data format
        """
        return self._backend

    @abc.abstractmethod
    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        """
        Reads and interprets data based on the configuration

        Returns:
            A dataframe containing all configured information
        """
        ...

    @classmethod
    @abc.abstractmethod
    def get_format(cls) -> str:
        """
        Returns:
            The name of the format that this retriever retrieves
        """
        ...

