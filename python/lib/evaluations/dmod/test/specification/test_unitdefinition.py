import os.path
import unittest
import typing

from ...evaluations import specification
from ..common import ConstructionTest
from ..common import create_model_permutation_pairs


class TestUnitDefinitionConstruction(ConstructionTest, unittest.TestCase):
    def test_extract_fields(self):
        definition = self.get_model_to_construct().create(self.params)

        extracted_fields = definition.extract_fields()

        new_definition = self.get_model_to_construct().create(extracted_fields)

        self.assertEqual(definition, new_definition)

    def check_equality_among_many(self, models: typing.Sequence[specification.Specification]):
        for model in models:
            self.assertEqual(model, model, f"'{str(model)}' is not considered equal to itself")

        for first_model, second_model in create_model_permutation_pairs(models):
            self.assertNotEqual(
                first_model,
                second_model,
                f"'{str(first_model)}' and '{str(second_model)} were considered the same."
            )

    def check_equality_for_one(self, model: specification.Specification):
        self.assertEqual(model, model, f"'{str(model)}' is not considered equal to itself")

    def get_model_to_construct(cls) -> typing.Type[specification.Specification]:
        return specification.UnitDefinition

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
            }
        ]

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Union[str, typing.Dict[str, typing.Any]],
            definition: specification.UnitDefinition
    ):
        if isinstance(parameters, str):
            test.assertEqual(definition.value, parameters)
        elif isinstance(parameters, specification.UnitDefinition):
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
            raise TypeError("The given parameters are not a valid definition for a unit")


if __name__ == '__main__':
    unittest.main()
