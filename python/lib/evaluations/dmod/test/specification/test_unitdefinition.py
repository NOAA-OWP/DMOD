import os.path
import unittest
import typing

from ...evaluations.specification import model
from ..common import ConstructionTest


class TestUnitDefinitionConstruction(ConstructionTest, unittest.TestCase):
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.UnitDefinition

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "path": "x/y/z"
        }
        self.__param_list: typing.Sequence[typing.Union[typing.Dict[str, typing.Any], str]] = [
            {
                "field": "field"
            },
            {
                "path": "path/to/unit"
            },
            {
                "value": "asdad"
            },
            "value"
        ]

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Union[str, typing.Dict[str, typing.Any]],
            definition: model.UnitDefinition
    ):
        if isinstance(parameters, str):
            test.assertEqual(definition.value, parameters)
        elif isinstance(parameters, model.UnitDefinition):
            test.assertEqual(definition, parameters)
        elif isinstance(parameters, dict):
            test.assertEqual(definition.value, parameters.get("value"))

            if isinstance(parameters.get("path"), str):
                test.assertSequenceEqual(definition.path, parameters.get("path").split("/"))
            elif isinstance(parameters.get("path"), bytes):
                test.assertSequenceEqual(definition.path, parameters.get("path").decode().split("/"))
            elif isinstance(parameters.get("path"), typing.Sequence):
                test.assertSequenceEqual(definition.path, parameters.get("path"))
            else:
                test.assertEqual(definition.path, parameters.get("path"))

            test.assertEqual(definition.field, parameters.get("field"))
        else:
            raise TypeError(f"The given parameters are not a valid definition for a unit")


if __name__ == '__main__':
    unittest.main()
