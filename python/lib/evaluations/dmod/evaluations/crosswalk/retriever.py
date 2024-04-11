import typing
import abc

from .. import specification
from .. import backends
from .. import retrieval


class CrosswalkRetriever(retrieval.Retriever, abc.ABC):
    @classmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """
        return "crosswalks"

    @classmethod
    @abc.abstractmethod
    def get_format(cls) -> str:
        ...

    @classmethod
    @abc.abstractmethod
    def get_type(cls) -> str:
        ...

    def __init__(self, definition: specification.CrosswalkSpecification):
        super().__init__(definition)

    @property
    def definition(self) -> specification.CrosswalkSpecification:
        return self._definition

    @property
    def properties(self) -> typing.Dict[str, typing.Any]:
        return self.definition.properties

    @property
    def backend(self) -> backends.Backend:
        return self._backend

    @property
    def field(self) -> specification.ValueSelector:
        return self.definition.field

    @property
    def prediction_field_name(self) -> str:
        return self.definition.prediction_field_name

    @property
    def observation_field_name(self) -> str:
        return self.definition.observation_field_name

    def __getitem__(self, key: str) -> typing.Any:
        return self.definition[key]

    def __contains__(self, key: str) -> bool:
        return key in self.definition

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        return self.definition.get(key, default)
