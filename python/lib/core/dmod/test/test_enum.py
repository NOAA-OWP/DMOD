import unittest
import enum
from pydantic import BaseModel

from ..core.enum import PydanticEnum


class SomeEnum(PydanticEnum):
    foo = 1
    bar = 2
    baz = 3


class SomeModel(BaseModel):
    some_enum: SomeEnum


class TestEnumValidateByNameMixIn(unittest.TestCase):
    def test_instantiate_model_with_enum_field_name(self):
        model = SomeModel(some_enum="foo")
        self.assertEqual(model.some_enum, SomeEnum.foo)

    def test_instantiate_model_with_enum_instance(self):
        model = SomeModel(some_enum=SomeEnum.foo)
        self.assertEqual(model.some_enum, SomeEnum.foo)

    def test_raises_ValueError_instantiate_model_with_bad_enum_field_name(self):
        with self.assertRaises(ValueError):
            SomeModel(some_enum="missing_field")

    def test_raises_ValueError_instantiate_model_with_bad_enum_instance(self):
        class BadEnum(enum.Enum):
            bad = 1

        with self.assertRaises(ValueError):
            SomeModel(some_enum=BadEnum.bad)

    def test_enum_names_in_json_schema(self):
        schema = SomeModel.schema()
        some_enum_schema = schema["definitions"]["SomeEnum"]
        self.assertEqual(some_enum_schema["type"], "string")

        enum_field_names = [member.name.upper() for member in SomeEnum]
        self.assertListEqual(enum_field_names, some_enum_schema["enum"])
