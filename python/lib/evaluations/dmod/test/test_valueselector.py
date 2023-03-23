import os.path
import unittest
import typing

from ..evaluations import specification
from .common import ConstructionTest
from .test_indexfield import TestIndexFieldConstruction
from .common import create_model_permutation_pairs


class TestValueSelectorConstruction(ConstructionTest, unittest.TestCase):
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
        return specification.ValueSelector

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
            "associated_fields": [
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
                "associated_fields": [
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
                "associated_fields": [
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
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Union[typing.Dict[str, typing.Any], specification.ValueSelector],
            definition: specification.ValueSelector
    ):
        if isinstance(parameters, dict):
            test.assertEqual(parameters.get('where'), definition.where)
            test.assertEqual(parameters.get("name"), definition.name)

            path = parameters.get("path")

            if path is not None:
                if isinstance(path, bytes):
                    path = path.decode()

                starts_at_root = False

                if isinstance(path, str):
                    starts_at_root = path.startswith("/")
                    path = path.split("/")

                if starts_at_root:
                    path.insert(0, "$")

                path = [
                    part
                    for part in path
                    if bool(part)
                ]

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
                test.assertSequenceEqual(definition.origin, ["$"])

            test.assertEqual(len(definition.associated_fields), len(parameters.get("associated_fields", list())))

            if 'associated_fields' in parameters:
                TestIndexFieldConstruction.make_assertions_for_multiple_definitions(
                        test,
                        definition.associated_fields,
                        parameters['associated_fields']
                )

            properties = parameters.get("properties", dict())

            for key in properties:
                test.assertIn(key, definition)
                test.assertEqual(definition[key], parameters['properties'][key])
                test.assertEqual(definition.properties[key], parameters['properties'][key])
                test.assertEqual(definition.get(key), parameters['properties'][key])

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))
        else:
            test.assertEqual(parameters.name, definition.name)
            test.assertEqual(parameters.origin, definition.origin)
            test.assertEqual(parameters.path, definition.path)
            test.assertEqual(parameters.where, definition.where)


if __name__ == '__main__':
    unittest.main()
