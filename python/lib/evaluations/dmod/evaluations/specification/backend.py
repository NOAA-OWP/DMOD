"""
Defines classes used to load and interpret data
"""
import json
import typing
import abc

from . import TemplateManager
from .base import TemplatedSpecification


class BackendSpecification(TemplatedSpecification):
    """
    A specification of how data should be loaded
    """

    def __eq__(self, other) -> bool:
        parents_match = super().__eq__(other=other)
        has_fields = hasattr(other, "type") or hasattr(other, "address") or hasattr(other, "format")

        if not parents_match or not has_fields:
            return False

        return self.type == other.type and self.address == other.address and self.format == other.format

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'backend_type' in configuration:
            self.__backend_type = configuration['backend_type']

        if 'address' in configuration:
            self.__address = configuration['address']

        if 'data_format' in configuration:
            self.__format = configuration['data_format']

    def validate(self) -> typing.Sequence[str]:
        return list()

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields.update({
            "backend_type": self.__backend_type,
            "address": self.__address,
            "data_format": self.__format
        })
        return fields

    __slots__ = ["__backend_type", "__address", "__format"]

    def __init__(
        self,
        backend_type: str,
        data_format: str,
        address: str = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.__backend_type = backend_type
        self.__format = data_format
        self.__address = address

    @property
    def type(self) -> str:
        """
        The type of backend that should be used
        """
        return self.__backend_type

    @property
    def format(self) -> str:
        """
        The type of data to be interpreted

        A single backend type may have more than one format. A `file` may be json, csv, netcdf, etc
        """
        return self.__format

    @property
    def address(self) -> typing.Optional[str]:
        """
        Where the data for the backend to interpret lies
        """
        return self.__address

    def __str__(self) -> str:
        description = self.__backend_type
        if self.__address:
            description += f": {self.__address}"
        else:
            description += f"=> {self.__format}"

        return description


class LoaderSpecification(TemplatedSpecification, abc.ABC):
    """
    Represents a class that uses a backend to load data
    """
    __slots__ = ['_backend']

    def __init__(self, backend: BackendSpecification = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend = backend

    @property
    def backend(self) -> BackendSpecification:
        return self._backend

    @abc.abstractmethod
    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()
        fields['backend'] = self.backend.to_dict()
        return fields

    @abc.abstractmethod
    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'backend' in configuration:
            backend_configuration = configuration['backend']

            if self.backend:
                self.backend.apply_configuration(
                    configuration=backend_configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )
            else:
                self._backend = BackendSpecification.create(
                    data=backend_configuration,
                    template_manager=template_manager,
                    decoder_type=decoder_type
                )

    @abc.abstractmethod
    def __eq__(self, other):
        return super().__eq__(other) and self.backend == other.backend
