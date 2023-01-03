from pydantic.fields import ModelField
from pprint import pformat
from enum import Enum

from .helper_functions import EnumNamesJSONEncoder

from typing import Any, Callable, Dict, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

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
            field_schema["enum"] = [f.name.upper() for f in field.type_]
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


class PydanticSerializeEnum:
    """Serialize `pydantic.BaseModel` subclass enum fields using their `name` attribute."""

    def json(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        models_as_dict: bool = True,
        **dumps_kwargs: Any,
    ) -> str:
        return super().json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            encoder=encoder,
            models_as_dict=models_as_dict,
            cls=EnumNamesJSONEncoder
            if "cls" not in dumps_kwargs
            else dumps_kwargs["cls"],
            **dumps_kwargs,
        )
