import unittest
import typing
import json
import io

from ..evaluations.specification import model


class TestModelConstruction(unittest.TestCase):

    def test_backendspecification(self):
        params = {
            "backend_type": "file",
            "address": "path/to/file",
            "data_format": "json",
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }

        definition: model.BackendSpecification = model.BackendSpecification.create(params)
        self.assertEqual(definition.type, "file")
        self.assertEqual(definition.address, "path/to/file")
        self.assertEqual(definition.format, "json")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        text_params = json.dumps(params)

        definition: model.BackendSpecification = model.BackendSpecification.create(text_params)
        self.assertEqual(definition.type, "file")
        self.assertEqual(definition.address, "path/to/file")
        self.assertEqual(definition.format, "json")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        bytes_params = text_params.encode()

        definition: model.BackendSpecification = model.BackendSpecification.create(bytes_params)
        self.assertEqual(definition.type, "file")
        self.assertEqual(definition.address, "path/to/file")
        self.assertEqual(definition.format, "json")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.BytesIO()
        buffer.write(bytes_params)
        buffer.seek(0)

        definition: model.BackendSpecification = model.BackendSpecification.create(buffer)
        self.assertEqual(definition.type, "file")
        self.assertEqual(definition.address, "path/to/file")
        self.assertEqual(definition.format, "json")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.StringIO()
        buffer.write(text_params)
        buffer.seek(0)

        definition: model.BackendSpecification = model.BackendSpecification.create(buffer)
        self.assertEqual(definition.type, "file")
        self.assertEqual(definition.address, "path/to/file")
        self.assertEqual(definition.format, "json")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

    def test_fieldmappingspecification(self):
        params = {
            "field": "value",
            "map_type": "field",
            "value": "observation",
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }

        definition: model.FieldMappingSpecification = model.FieldMappingSpecification.create(params)
        self.assertEqual(definition.value, "observation")
        self.assertEqual(definition.map_type, "field")
        self.assertEqual(definition.field, "value")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        text_params = json.dumps(params)

        definition: model.FieldMappingSpecification = model.FieldMappingSpecification.create(text_params)
        self.assertEqual(definition.value, "observation")
        self.assertEqual(definition.map_type, "field")
        self.assertEqual(definition.field, "value")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        bytes_params = text_params.encode()

        definition: model.FieldMappingSpecification = model.FieldMappingSpecification.create(bytes_params)
        self.assertEqual(definition.value, "observation")
        self.assertEqual(definition.map_type, "field")
        self.assertEqual(definition.field, "value")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.BytesIO()
        buffer.write(bytes_params)
        buffer.seek(0)

        definition: model.FieldMappingSpecification = model.FieldMappingSpecification.create(buffer)
        self.assertEqual(definition.value, "observation")
        self.assertEqual(definition.map_type, "field")
        self.assertEqual(definition.field, "value")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.StringIO()
        buffer.write(text_params)
        buffer.seek(0)

        definition: model.FieldMappingSpecification = model.FieldMappingSpecification.create(buffer)
        self.assertEqual(definition.value, "observation")
        self.assertEqual(definition.map_type, "field")
        self.assertEqual(definition.field, "value")
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

    def test_valueselector(self):
        params = {
            "where": "value",
            "path": ["path", "to", "field"],
            "properties": {
                "prop1": 6,
                "prop2": 7,
                "prop3": True
            }
        }

        definition: model.ValueSelector = model.ValueSelector.create(params)
        self.assertEqual(definition.where, "value")
        self.assertEqual(definition.origin, ["path", "to", "field"])
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        text_params = json.dumps(params)

        definition: model.ValueSelector = model.ValueSelector.create(text_params)
        self.assertEqual(definition.where, "value")
        self.assertEqual(definition.origin, ["path", "to", "field"])
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        bytes_params = text_params.encode()

        definition: model.ValueSelector = model.ValueSelector.create(bytes_params)
        self.assertEqual(definition.where, "value")
        self.assertEqual(definition.origin, ["path", "to", "field"])
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.BytesIO()
        buffer.write(bytes_params)
        buffer.seek(0)

        definition: model.ValueSelector = model.ValueSelector.create(buffer)
        self.assertEqual(definition.where, "value")
        self.assertEqual(definition.origin, ["path", "to", "field"])
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))

        buffer = io.StringIO()
        buffer.write(text_params)
        buffer.seek(0)

        definition: model.ValueSelector = model.ValueSelector.create(buffer)
        self.assertEqual(definition.where, "value")
        self.assertEqual(definition.origin, ["path", "to", "field"])
        self.assertIn("prop1", definition)
        self.assertIn("prop2", definition)
        self.assertIn("prop3", definition)
        self.assertEqual(definition["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.properties["prop1"], params["properties"]["prop1"])
        self.assertEqual(definition.properties["prop2"], params["properties"]["prop2"])
        self.assertEqual(definition.properties["prop3"], params["properties"]["prop3"])
        self.assertEqual(definition.get("prop1"), params["properties"]["prop1"])
        self.assertEqual(definition.get("prop2"), params["properties"]["prop2"])
        self.assertEqual(definition.get("prop3"), params["properties"]["prop3"])
        self.assertIsNone(definition.get("prop4"))
        self.assertTrue(definition.get("prop4", True))


if __name__ == '__main__':
    unittest.main()
