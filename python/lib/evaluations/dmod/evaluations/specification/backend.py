"""
Defines classes used to load and interpret data
"""
import json
import typing
import abc

import pydantic

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

        return self.backend_type == other.backend_type and self.address == other.address and self.format == other.format

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'backend_type' in configuration:
            self.backend_type = configuration['backend_type']

        if 'address' in configuration:
            self.address = configuration['address']

        if 'data_format' in configuration:
            self.format = configuration['data_format']
        elif "format" in configuration:
            self.format = configuration['format']

    def validate_self(self) -> typing.Sequence[str]:
        return list()

    backend_type: str = pydantic.Field(description="What sort of backend to use to load the data")
    address: typing.Optional[str] = pydantic.Field(description="Where the data for the backend to the interpreter lies")
    format: str = pydantic.Field(description="What format the data is in")

    def __str__(self) -> str:
        description = self.backend_type
        if self.address:
            description += f": {self.address}"
        else:
            description += f"=> {self.format}"

        return description


class LoaderSpecification(TemplatedSpecification, abc.ABC):
    """
    Represents a class that uses a backend to load data
    """
    backend: BackendSpecification = pydantic.Field(description="Instructions on how to load data")

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
