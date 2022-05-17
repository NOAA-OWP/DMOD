import typing
import abc

import pandas

from .. import specification
from .. import backends


class CrosswalkRetriever(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_format(cls) -> str:
        ...

    @classmethod
    @abc.abstractmethod
    def get_type(cls) -> str:
        ...

    def __init__(self, definition: specification.CrosswalkSpecification):
        self.__definition = definition
        self.__backend = backends.get_backend(definition.backend)

    @property
    def definition(self) -> specification.CrosswalkSpecification:
        return self.__definition

    @property
    def properties(self) -> typing.Dict[str, typing.Any]:
        return self.__definition.properties

    @property
    def backend(self) -> backends.Backend:
        return self.__backend

    @property
    def field(self) -> specification.ValueSelector:
        return self.__definition.field

    @property
    def prediction_field_name(self) -> str:
        return self.__definition.prediction_field_name

    @property
    def observation_field_name(self) -> str:
        return self.__definition.observation_field_name

    def __getitem__(self, key: str) -> typing.Any:
        return self.__definition[key]

    def __contains__(self, key: str) -> bool:
        return key in self.__definition

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        return self.__definition.get(key, default)

    @abc.abstractmethod
    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        pass
