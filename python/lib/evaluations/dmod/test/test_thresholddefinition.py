import unittest
import typing

from ..evaluations.specification import model
from .specification.test_unitdefinition import TestUnitDefinitionConstruction
from .common import ConstructionTest


class TestThresholdDefinitionConstruction(ConstructionTest, unittest.TestCase):
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.ThresholdDefinition

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "name": "Test",
            "weight": 5,
            "field": "test_field",
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            },
            "unit": "foot"
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "name": "Test1",
                "weight": 5,
                "field": "test_field1",
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                },
                "unit": {
                    "field": "stuff"
                }
            },
            {
                "name": "Test2",
                "weight": 6,
                "field": "test_field2",
                "properties": {
                    "prop1": 8,
                    "prop2": 9,
                    "prop3": False
                },
                "unit": {
                    "path": "path/to/value"
                }
            },
            {
                "name": "Test3",
                "weight": 7,
                "field": "test_field3",
                "properties": {
                    "prop1": 10,
                    "prop2": 11,
                    "prop3": True
                },
                "unit": "stuff"
            }
        ]

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Dict[str, typing.Any],
            definition: model.ThresholdDefinition
    ):
        if isinstance(parameters, dict):
            test.assertEqual(definition.name, parameters['name'])
            test.assertEqual(definition.weight, parameters['weight'])

            if isinstance(parameters['field'], str):
                test.assertSequenceEqual(definition.field, parameters['field'].split("/"))
            elif isinstance(parameters['field'], bytes):
                test.assertSequenceEqual(definition.field, parameters['field'].decode().split("/"))
            else:
                test.assertSequenceEqual(definition.field, parameters['field'])

            for key in parameters['properties']:
                test.assertIn(key, definition)
                test.assertEqual(definition[key], parameters['properties'][key])
                test.assertEqual(definition.properties[key], parameters['properties'][key])
                test.assertEqual(definition.get(key), parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))
            TestUnitDefinitionConstruction.make_assertion_for_single_definition(
                    test,
                    parameters['unit'],
                    definition.unit
            )
        elif isinstance(parameters, model.ThresholdDefinition):
            test.assertEqual(definition, parameters)
        else:
            raise TypeError(f"The passed parameters are not valid")



if __name__ == '__main__':
    unittest.main()
