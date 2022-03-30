#!/usr/bin/env python3
import typing
import abc

import pandas

from .. import specification
from .. import backends


class ThresholdRetriever(abc.ABC):
    def __init__(self, threshold_specification: specification.ThresholdSpecification):
        self.__definition = threshold_specification
        self.__backend = backends.get_backend(threshold_specification.backend)

    @property
    def definition(self) -> specification.ThresholdSpecification:
        return self.__definition

    @property
    def backend(self) -> backends.Backend:
        return self.__backend

    @abc.abstractmethod
    def get_data(self) -> pandas.DataFrame:
        ...
