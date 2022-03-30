import typing
import unittest

from ...evaluations.specification import model
from ..common import TestConstruction
from ..common import TestOuterConstruction

from ..test_backendspecification import TestBackendSpecificationConstruction
from ..test_valueselector import TestValueSelectorConstruction

class TestCrosswalkSpecificationConstruction(TestOuterConstruction):
    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: TestConstruction,
            parameters: typing.Dict[str, typing.Any],
            definition: model.CrosswalkSpecification
    ):

        entity_path = parameters.get("entity_path")

        if entity_path is not None:
            if isinstance(entity_path, bytes):
                entity_path = entity_path.decode()
            if isinstance(entity_path, str):
                entity_path = entity_path.split("/")

            test.assertEqual(len(definition.entity_path), len(entity_path))

            for value in entity_path:
                test.assertIn(value, definition.entity_path)
        else:
            test.assertIsNone(definition.entity_path)

        TestBackendSpecificationConstruction.make_assertion_for_single_definition(
                test,
                parameters['backend'],
                definition.backend
        )

        TestValueSelectorConstruction.make_assertion_for_single_definition(
                test,
                parameters=parameters['prediction_field'],
                definition=definition.prediction_field
        )

        TestValueSelectorConstruction.make_assertion_for_single_definition(
                test,
                parameters=parameters['observation_field'],
                definition=definition.fields
        )

        for key in parameters.get('properties', dict()):
            test.assertIn(key, definition)
            test.assertEqual(definition[key], parameters['properties'][key])
            test.assertEqual(definition.properties[key], parameters['properties'][key])
            test.assertEqual(definition.get(key), parameters['properties'][key])

        test.assertIsNone(definition.get("NonExistentProperty"))
        test.assertTrue(definition.get("NonExistentProperty", True))

    def setUp(self) -> None:
        self.__full_object_parameters = {
            "backend": model.BackendSpecification(
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
            "prediction_field": model.ValueSelector(
                    where="key",
                    path="path/to/key",
                    origin="path/to/starting_point",
                    datatype="datetime"
            ),
            "observation_field": model.ValueSelector(
                    where="value",
                    path=[
                        "key",
                        "path"
                    ],
                    associated_fields=[
                        model.AssociatedField(
                                name="example_1",
                                datatype="int"
                        ),
                        model.AssociatedField(
                                name="example_2",
                                datatype="datetime"
                        )
                    ],
                    datatype="datetime"
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
                    "backend": model.BackendSpecification(
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
                    "prediction_field": model.ValueSelector(
                            where="key",
                            path=["path", "to", "key"],
                            datatype="datetime"
                    ),
                    "observation_field": model.ValueSelector(
                            where="vasdflue",
                            path=[
                                "path"
                            ],
                            associated_fields=[
                                model.AssociatedField(
                                        name="example_2",
                                        datatype="datetime"
                                )
                            ],
                            datatype="datetime"
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
                    "backend": model.BackendSpecification(
                            backend_type="pubsub",
                            address="ws://dangerous.site.ru",
                            data_format="websocket",
                            prop1=10,
                            prop2=11,
                            prop3=True
                    ),
                    "entity_path": "",
                    "prediction_field": model.ValueSelector(
                            where="filename"
                    ),
                    "observation_field": model.ValueSelector(
                            where="value",
                            path=[
                                "key",
                                "path",
                                "path"
                            ]
                    ),
                    "properties": {
                        "prop1": 7,
                        "proasp2": "t",
                        "prop3": True
                    }
                }
        )

        self.__partial_object_parameters = {
            "backend": model.BackendSpecification(
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
            "prediction_field": dict(
                    where="key",
                    path="path/to/key",
                    origin="path/to/starting_point",
                    datatype="datetime"
            ),
            "observation_field": model.ValueSelector(
                    where="value",
                    path=[
                        "key",
                        "path"
                    ],
                    associated_fields=[
                        model.AssociatedField(
                                name="example_1",
                                datatype="int"
                        ),
                        model.AssociatedField(
                                name="example_2",
                                datatype="datetime"
                        )
                    ],
                    datatype="datetime"
            ),
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
                    "prediction_field": dict(
                            where="key",
                            path=["path", "to", "key"],
                            datatype="datetime"
                    ),
                    "observation_field": model.ValueSelector(
                            where="vasdflue",
                            path=[
                                "path"
                            ],
                            associated_fields=[
                                model.AssociatedField(
                                        name="example_2",
                                        datatype="datetime"
                                )
                            ],
                            datatype="datetime"
                    ),
                    "properties": {
                        "prop1": 3,
                        "prop2": 8,
                        "prop3": False
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
                    "entity_path": "",
                    "prediction_field": dict(
                            where="filename"
                    ),
                    "observation_field": model.ValueSelector(
                            where="value",
                            path=[
                                "key",
                                "path",
                                "path"
                            ]
                    ),
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
            "prediction_field": dict(
                    where="key",
                    path="path/to/key",
                    origin="path/to/starting_point",
                    datatype="datetime"
            ),
            "observation_field": dict(
                    where="value",
                    path=[
                        "key",
                        "path"
                    ],
                    index=[
                        dict(
                                name="example_1",
                                datatype="int"
                        ),
                        dict(
                                name="example_2",
                                datatype="datetime"
                        )
                    ],
                    datatype="datetime"
            ),
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
                    "entity_path": "padrth/tdo/stfgrtart",
                    "prediction_field": dict(
                            where="key",
                            path=["path", "to", "key"],
                            datatype="datetime"
                    ),
                    "observation_field": dict(
                            where="vasdflue",
                            path=[
                                "path"
                            ],
                            index=[
                                dict(
                                        name="example_2",
                                        datatype="datetime"
                                )
                            ],
                            datatype="datetime"
                    ),
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
                    "entity_path": "",
                    "prediction_field": dict(
                            where="filename"
                    ),
                    "observation_field": dict(
                            where="value",
                            path=[
                                "key",
                                "path",
                                "path"
                            ]
                    ),
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
    def get_model_to_construct(cls) -> typing.Type[model.Specification]:
        return model.CrosswalkSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
