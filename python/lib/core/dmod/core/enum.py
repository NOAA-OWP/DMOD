from enum import Enum
from pydantic.fields import ModelField
from pprint import pformat

from typing import Any, Dict, Union

# inspiration from https://github.com/pydantic/pydantic/issues/598
class PydanticEnum(Enum):
    """
    Subtypes of this enum variant that are embedded in a pydantic model will be:
      - coerced into an enum instance using member name (case insensitive)
      - and expose member names (upper case) in model json schema.


    Example:
    ```python
    class PowerState(PydanticEnum):
        OFF = 0
        ON = 1

    class Appliance(pydantic.BaseModel):
        power_state: PowerState
        ...

    Appliance(power_state=PowerState.ON)
    Appliance(power_state="ON")
    Appliance(power_state="on")

    Appliance(power_state=1) # invalid
    ```

    Note, `PydanticEnum` subtypes with member names that case-intensively match will yield
    undesirable behavior.
    """

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any], field: ModelField) -> None:
        """Method used by pydantic to populate json schema fields and their associated types."""
        # display enum field names as field options
        if "enum" in field_schema:
            field_schema["enum"] = [f.name.upper() for f in field.type_]
            field_schema["type"] = "string"

    @classmethod
    def __get_validators__(cls):
        """Method used by pydantic to retrieve a class's validators."""
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[Enum, str]):
        """
        Method used by pydantic to validate and potentially coerce a `v` into a `cls` enum type.

        Coercion from a `str` into a `cls` enum instance is performed _case-insensitively_ based on
        the `cls` enum's `name` fields. For example, enum Foo with member `bar = 1` is coercible by
        providing `"bar"`, _not_ `1`.

        Example:
        ```python
        class Foo(PydanticEnum):
            bar = 1

        class Model(pydantic.BaseModel):
            foo: Foo

        Model(foo=Foo.bar) # valid
        Model(foo="bar") # valid
        Model(foo="BAR") # valid

        Model(foo=1) # invalid
        ```
        """
        if isinstance(v, cls):
            return v

        v = str(v).upper()

        for name, value in cls.__members__.items():
            if name.upper() == v:
                return value

        error_message = pformat(
            f"Invalid Enum field. Field {v!r} is not a member of {set(cls.__members__)}"
        )
        raise ValueError(error_message)
