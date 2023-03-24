import typing
import unittest

from ...evaluations import specification
from ..common import ConstructionTest
from ..common import OuterConstructionTest
from ..common import create_model_permutation_pairs

from ..test_backendspecification import TestBackendSpecificationConstruction


class TestCrosswalkSpecificationConstruction(OuterConstructionTest, unittest.TestCase):
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
            definition: specification.CrosswalkSpecification
    ):

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

        TestBackendSpecificationConstruction.make_assertion_for_single_definition(
                test,
                parameters['backend'],
                definition.backend
        )

        test.assertEqual(definition.prediction_field_name, parameters['prediction_field_name'])
        test.assertEqual(definition.observation_field_name, parameters['observation_field_name'])

        for key in parameters.get('properties', dict()):
            test.assertIn(key, definition)
            test.assertEqual(definition[key], parameters['properties'][key])
            test.assertEqual(definition.properties[key], parameters['properties'][key])
            test.assertEqual(definition.get(key), parameters['properties'][key])

        test.assertIsNone(definition.get("NonExistentProperty"))
        test.assertTrue(definition.get("NonExistentProperty", True))

    def setUp(self) -> None:
        self.__full_object_parameters = {
            "backend": specification.BackendSpecification(
                    backend_type="file",
                    address="path/to/file",
                    data_format="json",
                    properties={
                      "prop3": True
                    },
                    prop1=6,
                    prop2=7
            ),
            "entity_path": "path/to/start",
            "prediction_field_name": "prediction_location",
            "observation_field_name": "observation_location",
            "field": specification.ValueSelector(
                    name="prediction_location",
                    where="key",
                    path=["* where site_no"],
                    origin="$",
                    datatype="string",
                    associated_fields=[
                        specification.AssociatedField(
                                name="observation_location",
                                path="site_no",
                                datatype="string"
                        )
                    ]
            ),
            "properties": {
                "prop1": 1,
                "prop2": 2,
                "prop3": True
            }
        }

        self.__full_object_parameter_list = list()
        self.__full_object_parameter_list.append(self.__full_object_parameters)
        self.__full_object_parameter_list.append(
                {
                    "backend": specification.BackendSpecification(
                            backend_type="service",
                            address="https://example.com",
                            data_format="xml",
                            properties={
                                "prop2": 9,
                                "prop3": False
                            },
                            prop1=8
                    ),
                    "entity_path": "padrth/tdo/stfgrtart",
                    "prediction_field_name": "prediction_field",
                    "observation_field_name": "observation_field",
                    "field": specification.ValueSelector(
                            name="x",
                            where="key"
                    ),
                    "properties": {
                        "prop1": 3,
                        "prop2": 8,
                        "prop3": False
                    }
                }
        )

        self.__full_object_parameter_list.append(
                {
                    "backend": specification.BackendSpecification(
                            backend_type="pubsub",
                            address="ws://dangerous.site.ru",
                            data_format="websocket",
                            prop1=10,
                            prop2=11,
                            prop3=True
                    ),
                    "entity_path": "",
                    "prediction_field_name": "prediction_field",
                    "observation_field_name": "observation_field",
                    "field": {
                        "name": "y",
                        "where": "value",
                        "path": ['x', 'y', 'z']
                    },
                    "properties": {
                        "prop1": 7,
                        "proasp2": "t",
                        "prop3": True
                    }
                }
        )

        self.__partial_object_parameters = {
            "backend": specification.BackendSpecification(
                    backend_type="file",
                    address="path/to/file",
                    data_format="json",
                    properties={
                        "prop3": True
                    },
                    prop1=6,
                    prop2=7
            ),
            "entity_path": "path/to/start",
            "prediction_field_name": "prediction_location",
            "field": specification.ValueSelector(
                    name="z",
                    where='one/two/three'
            ),
            "observation_field_name": "observation_field",
            "properties": {
                "prop1": 1,
                "prop2": 2,
                "prop3": True
            }
        }

        self.__partial_object_parameter_list = list()
        self.__partial_object_parameter_list.append(self.__partial_object_parameters.copy())

        self.__partial_object_parameter_list.append(
                {
                    "backend": {
                        "backend_type": "service",
                        "address": "https://example.com",
                        "data_format": "xml",
                        "properties": {
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        }
                    },
                    "entity_path": "padrth/tdo/stfgrtart",
                    "prediction_field_name": "prediction_field",
                    "observation_field_name": "observation_field",
                    "properties": {
                        "prop1": 3,
                        "prop2": 8,
                        "prop3": False
                    },
                    "field": {
                        "name": "ham",
                        "where": "sandwich"
                    }
                }
        )

        self.__partial_object_parameter_list.append(
                {
                    "backend": {
                        "backend_type": "pubsub",
                        "address": "ws://dangerous.site.ru",
                        "data_format": "websocket",
                        "properties": {
                            "prop1": 10,
                            "prop2": 11,
                            "prop3": True
                        }
                    },
                    "field": specification.ValueSelector(
                            name="cobb",
                            where="salad"
                    ),
                    "entity_path": "",
                    "prediction_field_name": "prediction_location",
                    "observation_field_name": "observation_field",
                    "properties": {
                        "prop1": 7,
                        "proasp2": "t",
                        "prop3": True
                    }
                }
        )

        self.__params = {
            "backend": dict(
                    backend_type="file",
                    address="path/to/file",
                    data_format="json",
                    properties={
                        "prop3": True
                    },
                    prop1=6,
                    prop2=7
            ),
            "entity_path": "path/to/start",
            "prediction_field_name": "prediction_field",
            "field": dict(
                    name="a",
                    where="value",
                    path=[
                        "one",
                        "two",
                        "three"
                    ]
            ),
            "observation_field_name": "observation_field",
            "properties": {
                "prop1": 1,
                "prop2": 2,
                "prop3": True
            }
        }

        self.__param_list = list()
        self.__param_list.append(self.__params.copy())

        self.__param_list.append(
                {
                    "backend": {
                        "backend_type": "service",
                        "address": "https://example.com",
                        "data_format": "xml",
                        "properties": {
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        }
                    },
                    "field": {
                        "name": "afa",
                        "where": "value"
                    },
                    "entity_path": "padrth/tdo/stfgrtart",
                    "prediction_field_name": "prediction",
                    "observation_field_name": "observation",
                    "properties": {
                        "prop1": 3,
                        "prop2": 8,
                        "prop3": False
                    }
                }
        )

        self.__param_list.append(
                {
                    "backend": {
                        "backend_type": "pubsub",
                        "address": "ws://dangerous.site.ru",
                        "data_format": "websocket",
                        "properties": {
                            "prop1": 10,
                            "prop2": 11,
                            "prop3": True
                        }
                    },
                    "field": {
                        "name": "stuff",
                        "where": "key"
                    },
                    "origin": "",
                    "prediction_field_name": "prediction",
                    "observation_field_name": "observation",
                    "properties": {
                        "prop1": 7,
                        "proasp2": "t",
                        "prop3": True
                    }
                }
        )

    @property
    def full_object_parameters(self) -> typing.Dict[str, typing.Any]:
        return self.__full_object_parameters

    @property
    def partial_object_parameters(self) -> typing.Dict[str, typing.Any]:
        return self.__partial_object_parameters

    @property
    def full_object_parameter_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__full_object_parameter_list

    @property
    def partial_object_parameter_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__partial_object_parameter_list

    @classmethod
    def get_model_to_construct(cls) -> typing.Type[specification.Specification]:
        return specification.CrosswalkSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
