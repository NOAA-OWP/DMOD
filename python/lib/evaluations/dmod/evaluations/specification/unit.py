"""
Defines the class used to instruct what unit loaded values are in
"""
import json
import typing

from pydantic import Field
from pydantic import validator

from dmod.core.common import contents_are_equivalent

from .base import TemplateManagerProtocol
from .base import TemplatedSpecification


class UnitDefinition(TemplatedSpecification):
    """
    A definition of what a measurement unit is or where to find it
    """
    value: typing.Optional[str] = Field(default=None, description="A hardcoded definition for what the unit is")
    field: typing.Optional[str] = Field(
        default=None,
        description="A hardcoded name for the field that stores unit data"
    )
    path: typing.Optional[typing.Union[str, typing.List[str]]] = Field(default=None, description="A path to the field containing unit data")

    def __eq__(self, other) -> bool:
        if not super().__eq__(other):
            return False
        elif not hasattr(other, "value") or self.value != other.value:
            return False
        elif not hasattr(other, "path") or not contents_are_equivalent(self.path, other.path):
            return False

        return hasattr(other, "field") and self.field == other.field

    def __init__(self, value: str = None, **kwargs):
        super().__init__(value=value, **kwargs)

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManagerProtocol,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'field' in configuration:
            self.field = configuration['field']

        if 'path' in configuration:
            self.path = configuration['path']

        if 'value' in configuration:
            self.value = configuration['value']

    def validate_self(self) -> typing.Sequence[str]:
        messages = list()

        if not self.value and not self.path and not self.field:
            messages.append("Unit definition is missing a field, a path, and a value; no unit data will be found.")

        fields_and_values = {
            "value": bool(self.value),
            "path": bool(self.path),
            "field": bool(self.field)
        }

        marked_fields = [
            name
            for name, exists in fields_and_values.items()
            if exists
        ]

        if len(marked_fields) > 1:
            messages.append(f"Values for {' and '.join(marked_fields)} have all been set - only one is valid")

        return messages

    @validator("path")
    def _interpret_path(
        cls,
        value: typing.Union[str, bytes, typing.Sequence[str]] = None
    ) -> typing.Optional[typing.Sequence[str]]:
        if isinstance(value, bytes):
            value = value.decode()

        path_starts_at_root = False

        if isinstance(value, str):
            path_starts_at_root = value.startswith("/")
            value = value.split("/")

        if path_starts_at_root:
            value.insert(0, "$")

        return value

    def __str__(self):
        if self.field:
            return self.field

        return ".".join(self.path) if self.path else self.value
