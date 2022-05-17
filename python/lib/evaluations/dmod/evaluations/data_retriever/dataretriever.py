#!/usr/bin/env python3
import typing
import abc

import pandas

from .. import specification
from .. import backends


class DataRetriever(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_format_name(cls) -> str:
        """
        Returns:
            The name that the reader should be referred to by outside code
        """

    def __init__(self, data_specification: specification.DataSourceSpecification):
        self.__definition = data_specification
        self.__backend = backends.get_backend(data_specification.backend)

    @property
    def definition(self) -> specification.DataSourceSpecification:
        return self.__definition

    @property
    def backend(self) -> backends.Backend:
        return self.__backend

    @abc.abstractmethod
    def get_data(self) -> pandas.DataFrame:
        ...
