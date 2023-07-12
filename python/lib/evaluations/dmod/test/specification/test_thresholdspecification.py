import typing
import unittest

from ...evaluations import specification
from ..common import ConstructionTest
from ..common import OuterConstructionTest
from ..common import create_model_permutation_pairs

from ..test_backendspecification import TestBackendSpecificationConstruction
from ..test_locationspecification import TestLocationSpecificationConstruction
from ..test_thresholddefinition import TestThresholdDefinitionConstruction


class TestThresholdSpecificationConstruction(OuterConstructionTest, unittest.TestCase):
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

    """
    Tests whether complex ThresholdSpecifications can be built with a variety of different construction approaches
    """
    @classmethod
    def make_assertion_for_single_definition(
            cls,
            test: typing.Union[ConstructionTest, unittest.TestCase],
            parameters: typing.Dict[str, typing.Any],
            definition: specification.ThresholdSpecification
    ):
        """
        Tests to see if a single created object matches the expected parameters

        Args:
            test: The unit test that called this function
            parameters: The expected values
            definition: the created object
        """
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

    def setUp(self) -> None:
        self.__full_object_parameters = {
            "backend": specification.BackendSpecification(
                    backend_type="file",
                    address="path/to/file",
                    format="json",
                    properties={
                      "prop3": True
                    },
                    prop1=6,
                    prop2=7
            ),
            "locations": specification.LocationSpecification(
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
                specification.ThresholdDefinition(
                        name="Test1",
                        field="test_field1",
                        unit="feet",
                        weight=5,
                        properties={
                            "prop1": 6,
                            "prop2": 7
                        },
                        prop3=True
                ),
                specification.ThresholdDefinition(
                        name="Test2",
                        weight=6,
                        field="test_field2",
                        properties={
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        },
                        unit="feet"
                ),
                specification.ThresholdDefinition(
                        name="Test3",
                        weight=7,
                        field="test_field3",
                        prop1=10,
                        prop2=11,
                        prop3=True,
                        unit="miles"
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
                    "backend": specification.BackendSpecification(
                            backend_type="service",
                            address="https://example.com",
                            format="xml",
                            properties={
                                "prop2": 9,
                                "prop3": False
                            },
                            prop1=8
                    ),
                    "locations": specification.LocationSpecification(
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
                        specification.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                properties={
                                    "prop1": 4,
                                    "prop2": 3,
                                    "prop3": True
                                },
                                unit="candy"
                        ),
                        specification.ThresholdDefinition(
                                name="Test4",
                                weight=8,
                                field="test_field3",
                                properties={
                                    "prop1": 10
                                },
                                prop2=12,
                                prop3=False,
                                unit="acre"
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
                    "backend": specification.BackendSpecification(
                            backend_type="pubsub",
                            address="ws://dangerous.site.ru",
                            format="websocket",
                            prop1=10,
                            prop2=11,
                            prop3=True
                    ),
                    "locations": specification.LocationSpecification(
                            identify=False,
                            from_field=None,
                            pattern=None,
                            ids=[],
                            prop1=1,
                            prop2=3,
                            prop3=False
                    ),
                    "definitions": [
                        specification.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                properties={
                                    "prop3": True
                                },
                                prop1=4,
                                prop2=3,
                                unit="L"
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
            "backend": specification.BackendSpecification(
                    backend_type="file",
                    address="path/to/file",
                    format="json",
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
                    },
                    "unit": "kcal"
                },
                specification.ThresholdDefinition(
                        name="Test2",
                        weight=6,
                        field="test_field2",
                        properties={
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        },
                        unit="inch"
                ),
                specification.ThresholdDefinition(
                        name="Test3",
                        weight=7,
                        field="test_field3",
                        prop1=10,
                        prop2=11,
                        prop3=True,
                        unit="mm"
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
                        "format": "xml",
                        "properties": {
                            "prop1": 8,
                            "prop2": 9,
                            "prop3": False
                        }
                    },
                    "locations": specification.LocationSpecification(
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
                            },
                            "unit": "watt"
                        },
                        {
                            "name": "Test4",
                            "weight": 8,
                            "field": "test_field3",
                            "properties": {
                                "prop1": 10,
                                "prop2": 12,
                                "prop3": False
                            },
                            "unit": "pascal"
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
                        "format": "websocket",
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
                        specification.ThresholdDefinition(
                                name="Terdfst1",
                                weight=2,
                                field="test_field",
                                prop1=4,
                                prop2=3,
                                prop3=True,
                                unit="psi"
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
                "format": "json",
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
                    },
                    "unit": "psi"
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
                        "field": "measurement_unit"
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
                    "unit": {
                        "path": ["path", "to", "unit"]
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
                        "format": "xml",
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
                            },
                            "unit": {
                                "value": "in"
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
                            },
                            "unit": "decibel"
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
                        "format": "websocket",
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
                            },
                            "unit": {
                                "field": "hour"
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
    def get_model_to_construct(cls) -> typing.Type[specification.Specification]:
        return specification.ThresholdSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
