import unittest
import typing

from ..evaluations import specification
from .common import ConstructionTest
from .common import create_model_permutation_pairs


class TestFieldMappingSpecificationConstruction(ConstructionTest, unittest.TestCase):
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
        return specification.FieldMappingSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "field": "Test",
            "map_type": "key",
            "value": "test_field",
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "value": "Test1",
                "map_type": "value",
                "field": "test_field1",
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                }
            },
            {
                "value": "Test2",
                "map_type": "filename",
                "field": "test_field2",
                "properties": {
                    "prop1": 8,
                    "prop2": 9,
                    "prop3": False
                }
            },
            {
                "value": "Test3",
                "map_type": "key",
                "field": "test_field3",
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
            parameters: typing.Union[typing.Dict[str, typing.Any], specification.FieldMappingSpecification],
            definition: specification.FieldMappingSpecification
    ):
        if isinstance(parameters, dict):
            test.assertEqual(definition.field, parameters['field'])
            test.assertEqual(definition.map_type, parameters['map_type'])
            test.assertEqual(definition.value, parameters['value'])

            if 'properties' in parameters:
                for key in parameters['properties']:
                    test.assertIn(key, definition)
                    test.assertEqual(definition.properties[key], parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))
        else:
            test.assertEqual(definition.field, parameters.field)
            test.assertEqual(definition.map_type, parameters.map_type)
            test.assertEqual(definition.value, parameters.value)

            if 'properties' in parameters:
                for key in parameters['properties']:
                    test.assertIn(key, definition)
                    test.assertEqual(definition.properties[key], parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))

if __name__ == '__main__':
    unittest.main()
