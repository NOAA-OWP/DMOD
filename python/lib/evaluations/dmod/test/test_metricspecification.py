import os.path
import unittest
import typing

from ..evaluations import specification
from .common import ConstructionTest
from .common import create_model_permutation_pairs


class TestMetricSpecificationConstruction(ConstructionTest, unittest.TestCase):
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
        return specification.MetricSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "name": "metric1",
            "weight": 1,
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "name": "metric1",
                "weight": 1,
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                }
            },
            {
                "name": "metric2",
                "weight": 7,
                "properties": {
                    "prop1": 8,
                    "prop2": 9,
                    "prop3": False
                }
            },
            {
                "name": "metric3",
                "weight": 3,
                "properties": {
                    "prop1": 10,
                    "prop2": 11,
                    "prop3": True
                }
            }
        ]

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Dict[str, typing.Any],
            definition: specification.MetricSpecification
    ):
        test.assertEqual(definition.name, parameters['name'])
        test.assertEqual(definition.weight, parameters['weight'])

        for key in parameters['properties']:
            test.assertIn(key, definition)
            test.assertEqual(definition[key], parameters['properties'][key])
            test.assertEqual(definition.properties[key], parameters['properties'][key])
            test.assertEqual(definition.get(key), parameters['properties'][key])

        test.assertIsNone(definition.get("NonExistentProperty"))
        test.assertTrue(definition.get("NonExistentProperty", True))


if __name__ == '__main__':
    unittest.main()
