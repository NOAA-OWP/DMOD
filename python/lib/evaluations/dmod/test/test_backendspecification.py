import unittest
import typing

from ..evaluations.specification import model
from .common import ConstructionTest


class TestBackendSpecificationConstruction(ConstructionTest, unittest.TestCase):
    def setUp(self) -> None:
        self.__params = {
            "backend_type": "file",
            "address": "path/to/file",
            "data_format": "json",
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "backend_type": "file",
                "address": "path/to/file",
                "data_format": "json",
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                }
            },
            {
                "backend_type": "service",
                "address": "https://example.com",
                "data_format": "xml",
                "properties": {
                    "prop1": 8,
                    "prop2": 9,
                    "prop3": False
                }
            },
            {
                "backend_type": "pubsub",
                "address": "ws://dangerous.site.ru",
                "data_format": "websocket",
                "properties": {
                    "prop1": 10,
                    "prop2": 11,
                    "prop3": True
                }
            },
        ]


    @classmethod
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.BackendSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Union[typing.Dict[str, typing.Any], model.BackendSpecification],
            definition: model.BackendSpecification
    ):
        if isinstance(parameters, model.BackendSpecification):
            test.assertEqual(definition.type, parameters.type)
            test.assertEqual(definition.address, parameters.address)
            test.assertEqual(definition.format, parameters.format)

            for key in parameters.properties:
                test.assertIn(key, definition.properties)
                test.assertEqual(definition[key], parameters[key])
                test.assertEqual(definition.properties[key], parameters.properties[key])
                test.assertEqual(definition.get(key), parameters.get(key))

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))
        else:
            test.assertEqual(definition.type, parameters['backend_type'])
            test.assertEqual(definition.address, parameters['address'])
            test.assertEqual(definition.format, parameters['data_format'])

            for key in parameters['properties']:
                test.assertIn(key, definition)
                test.assertEqual(definition[key], parameters['properties'][key])
                test.assertEqual(definition.properties[key], parameters['properties'][key])
                test.assertEqual(definition.get(key), parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))


if __name__ == '__main__':
    unittest.main()
