from enum import Enum
from .mixins import EnumValidateByNameMixIn


class PydanticEnum(EnumValidateByNameMixIn, Enum):
    """
    Subtypes of this type are validated using their field name when embedded in
    `pydantic.BaseModel`'s. Additionally, their field names are exposed in pydantic json schemas.
    """
