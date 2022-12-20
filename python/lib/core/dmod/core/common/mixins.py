from pydantic.fields import ModelField
from pprint import pformat
from enum import Enum

from typing import Any, Dict

# inspiration / code from https://github.com/pydantic/pydantic/issues/598
class EnumValidateByNameMixIn:
    """
    Mixin methods that enable `pydantic` to validate an `enum.Enum` variant using field names.

    `pydantic.BaseModel`'s that embed a subtype of this mixin will expose the subtype's field
    _names_ as enum members in their json schema. This strays from the default behavior, where enum
    _values_ are used instead.
    """

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any], field: ModelField) -> None:
        # display enum field names as field options
        if "enum" in field_schema:
            field_schema["enum"] = [f.name for f in field.type_]
            field_schema["type"] = "string"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        enum_names = {k.upper(): item for k, item in cls.__members__.items()}

        name = v.name.upper() if isinstance(v, Enum) else str(v).upper()
        needle = enum_names.get(name)

        if needle is None:
            error_message = pformat(
                f"Invalid Enum field. Field {needle!r} is not a member of {set(enum_names)}"
            )
            raise ValueError(error_message)

        return needle
