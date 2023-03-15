from django.test import TestCase
import enum

# Create your tests here.

from evaluation_service.choices import *

class FieldChoicesTest(TestCase):
    def test_StoredDatasetType(self):
        available_choices = StoredDatasetType.field_choices()
        self.assertEqual(len(available_choices), 1)

        choice = available_choices[0]
        self.assertEqual(choice[0], "geometry")
        self.assertEqual(choice[1], "Geometry")

        self.assertEqual(StoredDatasetType.geometry(), "geometry")

    def test_StoreDatasetFormat(self):
        available_choices = StoredDatasetFormat.field_choices()
        self.assertEqual(len(available_choices), 3)

        choice = available_choices[0]
        self.assertEqual(choice[0], "gpkg")
        self.assertEqual(choice[1], "GeoPackage")

        choice = available_choices[1]
        self.assertEqual(choice[0], "json")
        self.assertEqual(choice[1], "JSON")

        choice = available_choices[2]
        self.assertEqual(choice[0], "geojson")
        self.assertEqual(choice[1], "GeoJSON")

        self.assertEqual(StoredDatasetFormat.gpkg(), "gpkg")
        self.assertEqual(StoredDatasetFormat.json(), "json")
        self.assertEqual(StoredDatasetFormat.geojson(), "geojson")
