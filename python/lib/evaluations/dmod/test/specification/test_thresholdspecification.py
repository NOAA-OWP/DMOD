import typing
import unittest

from ...evaluations.specification import model
from ..common import TestConstruction
from ..common import TestOuterConstruction

from ..test_backendspecification import TestBackendSpecificationConstruction
from ..test_locationspecification import TestLocationSpecificationConstruction
from ..test_thresholddefinition import TestThresholdDefinitionConstruction

class TestThresholdSpecificationConstruction(TestOuterConstruction):
    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: TestConstruction,
            parameters: typing.Dict[str, typing.Any],
            definition: model.ThresholdSpecification
    ):
        TestBackendSpecificationConstruction.make_assertion_for_single_definition(
                test,
                parameters['backend'],
                definition.backend
        )
        TestLocationSpecificationConstruction.make_assertion_for_single_definition(
                test,
                parameters["locations"],
                definition.locations
        )
        TestThresholdDefinitionConstruction.make_assertions_for_multiple_definitions(
                test,
                definition.definitions,
                parameter_list=parameters['definitions']
        )

        for key in parameters['properties']:
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
            "locations": model.LocationSpecification(
                    identify=True,
                    from_field="field",
                    pattern="safsd*",
                    ids=[],
                    properties={
                        "prop5": 8,
                        "property45": 16
                    },
                    prope32="test"
            ),
            "definitions": [
                model.ThresholdDefinition(
                        name="Test1",
                        field="test_field1",
                        weight=5,
                        properties={
                            "prop1": 6,
                            "prop2": 7
                        },
                        prop3=True
                ),
                model.ThresholdDefinition(
                        name="Test2",
                        weight=6,
                        field="test_field2",
                        properties={
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        }
                ),
                model.ThresholdDefinition(
                        name="Test3",
                        weight=7,
                        field="test_field3",
                        prop1=10,
                        prop2=11,
                        prop3=True
                )
            ],
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
                    "locations": model.LocationSpecification(
                            identify=True,
                            from_field=None,
                            pattern=None,
                            ids=[
                                "Fred",
                                "Ed",
                                "Trey",
                                "Mark",
                                "Tom",
                                "Russ",
                                "Darone"
                            ],
                            properties={
                                "prop1": 6,
                                "prop3": False
                            },
                            prop2="one"
                    ),
                    "definitions": [
                        model.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                properties={
                                    "prop1": 4,
                                    "prop2": 3,
                                    "prop3": True
                                }
                        ),
                        model.ThresholdDefinition(
                                name="Test4",
                                weight=8,
                                field="test_field3",
                                properties={
                                    "prop1": 10
                                },
                                prop2=12,
                                prop3=False
                        )
                    ],
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
                    "locations": model.LocationSpecification(
                            identify=False,
                            from_field=None,
                            pattern=None,
                            ids=[],
                            prop1=1,
                            prop2=3,
                            prop3=False
                    ),
                    "definitions": [
                        model.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                properties={
                                    "prop3": True
                                },
                                prop1=4,
                                prop2=3
                        )
                    ],
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
            "locations": {
                "identify": True,
                "from_field": "field",
                "pattern": "safsd*",
                "ids": [],
                "properties": {
                    "prop5": 8,
                    "property45": 16,
                    "prope32": "test"
                },
            },
            "definitions": [
                {
                    "name": "Test1",
                    "weight": 5,
                    "field": "test_field1",
                    "properties": {
                        "prop1": 6,
                        "prop2": 7,
                        "prop3": True
                    }
                },
                model.ThresholdDefinition(
                        name="Test2",
                        weight=6,
                        field="test_field2",
                        properties={
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        }
                ),
                model.ThresholdDefinition(
                        name="Test3",
                        weight=7,
                        field="test_field3",
                        prop1=10,
                        prop2=11,
                        prop3=True
                )
            ],
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
                    "locations": model.LocationSpecification(
                            identify=True,
                            ids=[
                                "Fred",
                                "Ed",
                                "Trey",
                                "Mark",
                                "Tom",
                                "Russ",
                                "Darone"
                            ],
                            properties={
                                "prop2": "one"
                            },
                            prop1=6,
                            prop3=False
                    ),
                    "definitions": [
                        {
                            "name": "Terdfst1",
                            "weight": 2,
                            "field": "test_field",
                            "properties": {
                                "prop1": 4,
                                "prop2": 3,
                                "prop3": True
                            }
                        },
                        {
                            "name": "Test4",
                            "weight": 8,
                            "field": "test_field3",
                            "properties": {
                                "prop1": 10,
                                "prop2": 12,
                                "prop3": False
                            }
                        }
                    ],
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
                    "locations": {
                        "identify": False,
                        "from_field": None,
                        "pattern": None,
                        "ids": [],
                        "properties": {
                            "prop1": 1,
                            "prop2": 3,
                            "prop3": False
                        }
                    },
                    "definitions": [
                        model.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                prop1=4,
                                prop2=3,
                                prop3=True
                        )
                    ],
                    "properties": {
                        "prop1": 7,
                        "proasp2": "t",
                        "prop3": True
                    }
                }
        )

        self.__params = {
            "backend": {
                "backend_type": "file",
                "address": "path/to/file",
                "data_format": "json",
                "properties": {
                    "prop1": 6,
                    "prop2": 7,
                    "prop3": True
                }
            },
            "locations": {
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
            "definitions": [
                {
                    "name": "Test1",
                    "weight": 5,
                    "field": "test_field1",
                    "properties": {
                        "prop1": 6,
                        "prop2": 7,
                        "prop3": True
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
                    }
                }
            ],
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
                    "locations": {
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
                    "definitions": [
                        {
                            "name": "Terdfst1",
                            "weight": 2,
                            "field": "test_field",
                            "properties": {
                                "prop1": 4,
                                "prop2": 3,
                                "prop3": True
                            }
                        },
                        {
                            "name": "Test4",
                            "weight": 8,
                            "field": "test_field3",
                            "properties": {
                                "prop1": 10,
                                "prop2": 12,
                                "prop3": False
                            }
                        }
                    ],
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
                    "locations": {
                        "identify": False,
                        "from_field": None,
                        "pattern": None,
                        "ids": [],
                        "properties": {
                            "prop1": 1,
                            "prop2": 3,
                            "prop3": False
                        }
                    },
                    "definitions": [
                        {
                            "name": "Terdfst1",
                            "weight": 2,
                            "field": "test_field",
                            "properties": {
                                "prop1": 4,
                                "prop2": 3,
                                "prop3": True
                            }
                        }
                    ],
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
        return model.ThresholdSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
