import unittest
import typing

from ..evaluations import specification
from .common import ConstructionTest
from .common import create_model_permutation_pairs


class TestLocationSpecificationConstruction(ConstructionTest, unittest.TestCase):
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

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Dict[str, typing.Any],
            definition: specification.LocationSpecification
    ):
        if isinstance(parameters, dict):
            test.assertEqual(definition.identify, parameters.get('identify', False))
            test.assertEqual(definition.from_field, parameters['from_field'])

            if isinstance(parameters.get('pattern'), str):
                test.assertEqual(len(definition.pattern), 1)
                test.assertSequenceEqual(definition.pattern, [parameters['pattern']])
            elif isinstance(parameters.get('pattern'), typing.Sequence):
                test.assertEqual(definition.pattern, parameters['pattern'])
                test.assertSequenceEqual(definition.pattern, parameters['pattern'])
            else:
                test.assertEqual(definition.pattern, parameters.get('pattern'))

            if "ids" in parameters:
                test.assertEqual(len(definition.ids), len(parameters['ids']))

                for id in parameters['ids']:
                    test.assertIn(id, definition.ids)

            for key in parameters['properties']:
                test.assertIn(key, definition)
                test.assertEqual(definition[key], parameters['properties'][key])
                test.assertEqual(definition.properties[key], parameters['properties'][key])
                test.assertEqual(definition.get(key), parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))
        elif isinstance(parameters, specification.LocationSpecification):
            test.assertEqual(definition, parameters)
        else:
            raise TypeError(f"The passed parameters are not valid: {parameters}")

    def setUp(self) -> None:
        self.__params = {
            "identify": True,
            "from_field": "field",
            "pattern": "safsd*",
            "ids": [],
            "properties": {
                "prop5": 8,
                "property45": 16,
                "prope32": "test"
            }
        }

        self.__param_list = [
            {
                "identify": True,
                "from_field": "field",
                "pattern": "safsd*",
                "ids": [],
                "properties": {
                    "prop5": 8,
                    "property45": 16,
                    "prope32": "test"
                }
            },
            {
                "identify": True,
                "from_field": None,
                "pattern": None,
                "ids": [
                    "Fred",
                    "Ed",
                    "Trey",
                    "Mark",
                    "Tom",
                    "Russ",
                    "Darone"
                ],
                "properties": {
                    "prop1": 6,
                    "prop2": "one",
                    "prop3": False
                }
            },
            {
                "identify": False,
                "from_field": None,
                "pattern": None,
                "ids": [],
                "properties": {
                    "prop1": 1,
                    "prop2": 3,
                    "prop3": False
                }
            }
        ]

    @classmethod
    def get_model_to_construct(cls) -> typing.Type[specification.Specification]:
        return specification.LocationSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
