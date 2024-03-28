import abc
import typing

import pandas

from dmod.core.common.collections import catalog

from . import specification
from . import backends


LoaderTypeT = typing.TypeVar('LoaderTypeT', bound=specification.LoaderSpecification, covariant=True)


class Retriever(abc.ABC, typing.Generic[LoaderTypeT]):
    """
    Base for classes used to interpret a definition and use a backend to load data
    """
    def __init__(self, definition: LoaderTypeT, input_catalog: catalog.InputCatalog):
        self._definition = definition
        self._backend = backends.get_backend(definition.backend, input_catalog=input_catalog)

    @classmethod
    @abc.abstractmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """

    @property
    def definition(self) -> LoaderTypeT:
        """
        Returns:
            The specification for this retriever
        """
        return self._definition

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

    @classmethod
    @abc.abstractmethod
    def get_format(cls) -> str:
        """
        Returns:
            The name of the format that this retriever retrieves
        """
