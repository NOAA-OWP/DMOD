import os.path
import unittest
import typing

from ..evaluations.specification import model
from .common import TestConstruction
from .test_indexfield import TestIndexFieldConstruction


class TestValueSelectorConstruction(TestConstruction):
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.ValueSelector

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "where": "value",
            "name": "Value",
            "path": [
                "location",
                "site_no"
            ],
            "origin": [
                "path"
            ],
            "index": [
                {
                    "name": "one",
                    "path": ["path", "to", "one"]
                }
            ],
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "where": "key",
                "name": "Key Value",
                "path": None,
                "index": [
                    {
                        "name": "one",
                        "path": "path/to/one"
                    }
                ],
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                }
            },
            {
                "name": "Site Number",
                "where": "value",
                "path": [
                    "location",
                    "site_no"
                ],
                "properties": {
                    "prop1": 8,
                    "prop2": 9,
                    "prop3": False
                }
            },
            {
                "name": "Site No.",
                "where": "value",
                "path": "location/site_no",
                "origin": "path/to/values",
                "index": [
                    {
                        "name": "two",
                        "datatype": "int"
                    },
                    {
                        "name": "three",
                        "datatype": "datetime",
                        "path": "path",
                        "prop1": 3
                    },
                    {
                        "name": "four",
                        "datatype": "string"
                    }
                ],
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
            test: TestConstruction,
            parameters: typing.Dict[str, typing.Any],
            definition: model.ValueSelector
    ):
        test.assertEqual(definition.where, parameters['where'])
        test.assertEqual(definition.name, parameters['name'])

        path = parameters.get("path")

        if path is not None:
            if isinstance(path, bytes):
                path = path.decode()
            if isinstance(path, str):
                path = path.split("/")

            test.assertEqual(len(definition.path), len(path))

            for value in path:
                test.assertIn(value, definition.path)
        else:
            test.assertIsNone(definition.path)

        origin = parameters.get("origin")

        if origin is not None:
            if isinstance(origin, bytes):
                origin = origin.decode()
            if isinstance(origin, str):
                origin = origin.split("/")

            test.assertEqual(len(definition.origin), len(origin))

            for value in origin:
                test.assertIn(value, definition.origin)
        else:
            test.assertIsNone(definition.origin)

        test.assertEqual(len(definition.index), len(parameters.get("index", list())))

        if 'index' in parameters:
            TestIndexFieldConstruction.make_assertions_for_multiple_definitions(
                    test,
                    definition.index,
                    parameters['index']
            )

        properties = parameters.get("properties", dict())

        for key in properties:
            test.assertIn(key, definition)
            test.assertEqual(definition[key], parameters['properties'][key])
            test.assertEqual(definition.properties[key], parameters['properties'][key])
            test.assertEqual(definition.get(key), parameters['properties'][key])

        test.assertIsNone(definition.get("NonExistentProperty"))
        test.assertTrue(definition.get("NonExistentProperty", True))


if __name__ == '__main__':
    unittest.main()
