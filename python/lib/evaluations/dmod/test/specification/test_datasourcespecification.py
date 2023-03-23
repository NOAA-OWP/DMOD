import typing
import unittest

from ...evaluations import specification
from ..common import ConstructionTest
from ..common import OuterConstructionTest
from ..common import create_model_permutation_pairs

from ..test_backendspecification import TestBackendSpecificationConstruction
from ..test_locationspecification import TestLocationSpecificationConstruction
from ..test_fieldmappingspecification import TestFieldMappingSpecificationConstruction
from ..test_valueselector import TestValueSelectorConstruction
from .test_unitdefinition import TestUnitDefinitionConstruction


class TestDataSourceSpecificationConstruction(OuterConstructionTest, unittest.TestCase):
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
            definition: specification.DataSourceSpecification
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
        TestUnitDefinitionConstruction.make_assertion_for_single_definition(
                test,
                parameters['unit'],
                definition.unit
        )
        TestValueSelectorConstruction.make_assertions_for_multiple_definitions(
                test,
                definition.value_selectors,
                parameter_list=parameters['value_selectors']
        )
        TestFieldMappingSpecificationConstruction.make_assertions_for_multiple_definitions(
                test,
                definition.field_mapping,
                parameter_list=parameters['field_mapping']
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
            "value_field": "sads",
            "unit": "feet",
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
            "field_mapping": [
                specification.FieldMappingSpecification(
                        value="Value1",
                        map_type="test",
                        field="Field1"
                ),
                specification.FieldMappingSpecification(
                        value="Value2",
                        map_type="column",
                        field="Field2"
                ),
                specification.FieldMappingSpecification(
                        value="Value3",
                        map_type="test56",
                        field="Field3"
                )
            ],
            "value_selectors": [
                specification.ValueSelector(
                        name="array",
                        where="key",
                        origin="path/to/array",
                        prop1=5
                ),
                specification.ValueSelector(
                        name="site_no",
                        where="value:*/site_no",
                        path="/path/to/value",
                        associated_fields=[
                            specification.AssociatedField(
                                    name="two",
                                    datatype="int"
                            ),
                            specification.AssociatedField(
                                    name="three",
                                    datatype="datetime",
                                    prop1=3
                            ),
                            specification.AssociatedField(
                                    name="four",
                                    datatype="string"
                            )
                        ]
                ),
                specification.ValueSelector(
                        name="name",
                        where="filename",
                        path="dunno",
                        datatype="datetime"
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
                    "value_field": "x",
                    "name": "y",
                    "unit": specification.UnitDefinition(
                            path="path/to/value"
                    ),
                    "x_axis": "time",
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
                    "field_mapping": [
                        specification.FieldMappingSpecification(
                                value="Val45ue2",
                                map_type="cfrtolumn",
                                field="Fielhdd2"
                        ),
                        specification.FieldMappingSpecification(
                                value="Valudfe3",
                                map_type="tegst56",
                                field="Fieldfd3"
                        )
                    ],
                    "value_selectors": [
                        specification.ValueSelector(
                                name="example",
                                where="kezfdgy",
                                origin="path/tofdz/array",
                                prop1=55
                        ),
                        specification.ValueSelector(
                                name="otherExample",
                                where="filzdfgename",
                                path="zfdunno",
                                datatype="datetime"
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
                            data_format="websocket",
                            prop1=10,
                            prop2=11,
                            prop3=True
                    ),
                    "x_axis": "time",
                    "name": "timmy",
                    "value_field": "y",
                    "unit": specification.UnitDefinition(
                            field="unit"
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
                    "field_mapping": [
                        specification.FieldMappingSpecification(
                                value="Valudee1",
                                map_type="tedest",
                                field="Fielxzxd1"
                        )
                    ],
                    "value_selectors": [
                        specification.ValueSelector(
                                where="filcxdfbgename",
                                path="dundxfno",
                                name="sdhfsdhfh"
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
                    data_format="json",
                    properties={
                        "prop3": True
                    },
                    prop1=6,
                    prop2=7
            ),
            "name": "partial_object_parameters",
            "x_axis": "x",
            "value_field": "y",
            "unit": specification.UnitDefinition(
                    field="unit"
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
            "field_mapping": [
                {
                    "value": "Value1",
                    "map_type": "test",
                    "field": "Field1"
                },
                specification.FieldMappingSpecification(
                        value="Value2",
                        map_type="column",
                        field="Field2"
                ),
                {
                    "value": "Value3",
                    "map_type": "test56",
                    "field": "Field3"
                }
            ],
            "value_selectors": [
                specification.ValueSelector(
                        where="key",
                        origin="path/to/array",
                        prop1=5,
                        name="nameOfSelectedValue"
                ),
                {
                    "name": "dsfsf",
                    "where": "value:*/site_no",
                    "path": "/path/to/value",
                    "associated_fields": [
                        {
                            "name": "two",
                            "datatype": "int"
                        },
                        {
                            "name": "three",
                            "datatype": "datetime",
                            "prop1": 3
                        },
                        specification.AssociatedField(
                                name="four",
                                datatype="string"
                        )
                    ]
                },
                specification.ValueSelector(
                        where="filename",
                        path="dunno",
                        datatype="datetime",
                        name="filename"
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
                    "x_axis": "duration",
                    "name": "George",
                    "value_field": "x",
                    "unit": specification.UnitDefinition(
                            path=["one", "two", "three"]
                    ),
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
                    "value_selectors": [
                        specification.ValueSelector(
                                where="kezfdgy",
                                origin="path/tofdz/array",
                                prop1=55,
                                name="nameOfValue"
                        ),
                        dict(
                                where="filzdfgename",
                                path="zfdunno",
                                datatype="datetime",
                                name="nameOfValue"
                        )
                    ],
                    "field_mapping": [
                        {
                                "value": "Val45ue2",
                                "map_type": "cfrtolumn",
                                "field": "Fielhdd2"
                        },
                        specification.FieldMappingSpecification(
                                value="Valudfe3",
                                map_type="tegst56",
                                field="Fieldfd3"
                        )
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
                    "name": "partial_object",
                    "value_field": "x",
                    "unit": specification.UnitDefinition(
                            field="unit"
                    ),
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
                    "field_mapping": [
                        specification.FieldMappingSpecification(
                                value="Valudee1",
                                map_type="tedest",
                                field="Fielxzxd1"
                        )
                    ],
                    "value_selectors": [
                        dict(
                                name="sdfhsdhfoi",
                                where="filcxdfbgename",
                                path="dundxfno"
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
            "name": "params",
            "value_field": "prediction",
            "unit": "hr",
            "x_axis": "time",
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
            "value_selectors": [
                dict(
                        name="keyValue",
                        where="key",
                        origin="path/to/array",
                        prop1=5
                ),
                dict(
                        name="asdads",
                        where="value:*/site_no",
                        path="/path/to/value",
                        associated_fields=[
                            dict(
                                    name="two",
                                    datatype="int"
                            ),
                            dict(
                                    name="three",
                                    datatype="datetime",
                                    prop1=3
                            ),
                            dict(
                                    name="four",
                                    datatype="string"
                            )
                        ]
                ),
                dict(
                        name="name",
                        where="filename",
                        path="dunno",
                        datatype="datetime"
                )
            ],
            "field_mapping": [
                dict(
                        value="Value1",
                        map_type="test",
                        field="Field1"
                ),
                dict(
                        value="Value2",
                        map_type="column",
                        field="Field2"
                ),
                dict(
                        value="Value3",
                        map_type="test56",
                        field="Field3"
                )
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
                    "name": "param_list_2",
                    "value_field": "values",
                    "unit": {
                        "field": "m_unit"
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
                    "field_mapping": [
                        dict(
                                value="Val45ue2",
                                map_type="cfrtolumn",
                                field="Fielhdd2"
                        ),
                        dict(
                                value="Valudfe3",
                                map_type="tegst56",
                                field="Fieldfd3"
                        )
                    ],
                    "value_selectors": [
                        dict(
                                name="asdasd",
                                where="kezfdgy",
                                origin="path/tofdz/array",
                                prop1=55
                        ),
                        dict(
                                name="sdfsdf",
                                where="filzdfgename",
                                path="zfdunno",
                                datatype="datetime"
                        )
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
                    "name": "param_list_3",
                    "value_field": "x",
                    "unit": {
                        "path": ["one", "two", "three"]
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
                    "field_mapping": [
                        dict(
                                value="Valudee1",
                                map_type="tedest",
                                field="Fielxzxd1"
                        )
                    ],
                    "value_selectors": [
                        dict(
                                name="sdfdsf",
                                where="filcxdfbgename",
                                path="dundxfno"
                        )
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
        return specification.DataSourceSpecification

    @property
    def params(self) -> typing.Dict[str, typing.Any]:
        return self.__params

    @property
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        return self.__param_list


if __name__ == '__main__':
    unittest.main()
