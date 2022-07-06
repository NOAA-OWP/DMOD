import unittest
import typing

from ..evaluations.specification import model
from .common import ConstructionTest


class TestFieldMappingSpecificationConstruction(ConstructionTest, unittest.TestCase):
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.FieldMappingSpecification

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
            parameters: typing.Union[typing.Dict[str, typing.Any], model.FieldMappingSpecification],
            definition: model.FieldMappingSpecification
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
