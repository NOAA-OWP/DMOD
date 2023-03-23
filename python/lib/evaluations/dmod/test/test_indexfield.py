import os.path
import unittest
import typing

from ..evaluations import specification
from .common import ConstructionTest
from .common import create_model_permutation_pairs


class TestIndexFieldConstruction(ConstructionTest, unittest.TestCase):
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
        return specification.AssociatedField

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list

    def setUp(self) -> None:
        self.__params = {
            "name": "one",
            "path": "path"
        }
        self.__param_list: typing.Sequence[typing.Dict[str, typing.Any]] = [
            {
                "name": "two",
                "path": "path/to/two",
                "datatype": "int"
            },
            {
                "name": "three",
                "datatype": "datetime",
                "path": [
                    "path",
                    "to",
                    "three"
                ],
                "prop1": 3
            },
            {
                "name": "four",
                "datatype": "string"
            }
        ]

    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Union[typing.Dict[str, typing.Any], specification.AssociatedField],
            definition: specification.AssociatedField
    ):
        if isinstance(parameters, specification.AssociatedField):
            test.assertEqual(definition.name, parameters.name)
            test.assertEqual(definition.datatype, parameters.datatype)

            test.assertEqual(parameters.path, definition.path)
        else:
            test.assertEqual(definition.name, parameters['name'])
            test.assertEqual(definition.datatype, parameters.get('datatype'))

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
                test.assertEqual(definition.path[0], parameters['name'])

            if 'properties' in parameters:
                for key in parameters['properties']:
                    test.assertIn(key, definition)
                    test.assertEqual(definition[key], parameters['properties'][key])
                    test.assertEqual(definition.properties[key], parameters['properties'][key])
                    test.assertEqual(definition.get(key), parameters['properties'][key])

            extra_properties = {
                key: value
                for key, value in parameters.items()
                if "__" + key not in definition.__slots__
            }

            for key, value in extra_properties.items():
                test.assertIn(key, definition)
                test.assertEqual(definition[key], value)
                test.assertEqual(definition.properties[key], value)
                test.assertEqual(definition.get(key), value)

            test.assertIsNone(definition.get("NonExistentProperty"))
            test.assertTrue(definition.get("NonExistentProperty", True))


if __name__ == '__main__':
    unittest.main()
