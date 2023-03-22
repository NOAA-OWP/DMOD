"""
@TODO: Put a module wide description here
"""
import json
import typing

from . import TemplateManager
from .base import TemplatedSpecification


class UnitDefinition(TemplatedSpecification):
    """
    A definition of what a measurement unit is or where to find it
    """

    def extract_fields(self) -> typing.Dict[str, typing.Any]:
        fields = super().extract_fields()

        if self.__field:
            fields["field"] = self.__field

        if self.__path:
            fields['path'] = self.__path

        if self.__value:
            fields['value'] = self.__value

        return fields

    def apply_configuration(
        self,
        configuration: typing.Dict[str, typing.Any],
        template_manager: TemplateManager,
        decoder_type: typing.Type[json.JSONDecoder] = None
    ):
        if 'field' in configuration:
            self.__field = configuration['field']

        if 'path' in configuration:
            self.__path = configuration['path']

        if 'value' in configuration:
            self.__value = configuration['value']

    def validate(self) -> typing.Sequence[str]:
        messages = list()

        if not self.__value and not self.__path and not self.__field:
            messages.append("Unit definition is missing a field, a path, and a value; no unit data will be found.")

        fields_and_values = {
            "value": bool(self.__value),
            "path": bool(self.__path),
            "field": bool(self.__field)
        }

        marked_fields = [
            name
            for name, exists in fields_and_values.items()
            if exists
        ]

        if len(marked_fields) > 1:
            messages.append(f"Values for {' and '.join(marked_fields)} have all been set - only one is valid")

        return messages

    __slots__ = ["__field", "__path", "__value"]

    def __init__(
        self,
        value: typing.Union[str, bytes] = None,
        field: str = None,
        path: typing.Union[str, typing.Sequence[str]] = None,
        **kwargs
    ):
        super(UnitDefinition, self).__init__(**kwargs)

        self.__field = field

        path_starts_at_root = False

        if isinstance(path, str):
            path_starts_at_root = path.startswith("/")
            self.__path = path.split("/")
        else:
            self.__path = path

        if path_starts_at_root:
            self.__path.insert(0, "$")

        if isinstance(value, bytes):
            value = value.decode()

        self.__value = value

    @property
    def field(self) -> typing.Optional[str]:
        return self.__field

    @property
    def path(self) -> typing.Optional[typing.Sequence[str]]:
        return self.__path

    @property
    def value(self) -> typing.Optional[str]:
        return self.__value

    def __str__(self):
        if self.__field:
            return self.__field

        return ".".join(self.__path)
