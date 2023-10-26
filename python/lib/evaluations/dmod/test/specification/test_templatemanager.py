import logging
import os
import sqlite3
import unittest
import typing
import traceback
import shutil
import zipfile

from dmod.core.common import find

from ...evaluations import specification
from ..common import RESOURCE_DIRECTORY
from ..common import allocate_output_directory

TEMPLATE_MANIFEST_PATH = os.path.join(
    RESOURCE_DIRECTORY,
    "evaluations",
    "templates",
    "template_manifest.json"
)

TEST_DECODER = None


class TestTemplateManager(unittest.TestCase):
    def setUp(self) -> None:
        self.template_manager: specification.TemplateManager = specification.FileTemplateManager(
            manifest_path=TEMPLATE_MANIFEST_PATH
        )

    def test_manager(self):
        specification_types: typing.Sequence[typing.Tuple[str, str]] = self.template_manager.get_specification_types()

        expected_types = [
            ('EvaluationSpecification', 'Evaluation'),
            ('SchemeSpecification', 'Scheme'),
            ('ThresholdDefinition', 'Threshold Definition'),
            ('ThresholdSpecification', 'Threshold'),
            ('LocationSpecification', 'Location'),
            ('DataSourceSpecification', 'Data Source'),
            ('FieldMappingSpecification', 'Field Mapping'),
            ('ValueSelector', 'Value Selector'),
            ('CrosswalkSpecification', 'Crosswalk'),
            ('BackendSpecification', 'Backend'),
            ('AssociatedField', 'Associated Field'),
            ('ThresholdApplicationRules', 'Threshold Application Rules'),
            ('UnitDefinition', 'Unit Definition'),
            ('MetricSpecification', 'Metric'),
        ]
        self.assertEqual(len(specification_types), len(expected_types))

        for type_pair in expected_types:
            self.assertIn(
                type_pair,
                specification_types,
                f"The specification type pair of ({type_pair[0]}, {type_pair[1]}) wasn't returned from the template manager"
            )

    def test_file_export(self):
        output_directory = allocate_output_directory("test_file_export")

        try:
            manifest_path = self.template_manager.export_to_file(output_directory)
        except Exception as export_error:
            message = str(export_error)
            message += os.linesep
            message += traceback.format_exc()
            self.fail(message)

        new_manager: specification.TemplateManager = specification.FileTemplateManager(
            manifest_path=manifest_path
        )

        self.assertEqual(self.template_manager, new_manager)

        shutil.rmtree(output_directory, ignore_errors=True)

    def test_archive_export(self):
        output_directory = allocate_output_directory("test_archive_export")

        try:
            archive_path = self.template_manager.export_to_archive(output_directory / "archive")
        except BaseException as export_error:
            message = str(export_error)
            message += os.linesep
            message += traceback.format_exc(limit=4)
            self.fail(message)

        comparison_directory = output_directory / "comparison"

        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(path=comparison_directory)
        except BaseException as extraction_error:
            message = "Exported archive could not be unpacked"
            message += os.linesep
            message += str(extraction_error)
            message += os.linesep
            message += traceback.format_exc(limit=4)
            self.fail(message)

        comparison_manifest = comparison_directory / "template_manifest.json"

        self.assertTrue(comparison_manifest.exists(), msg="The uncompressed template manifest could not be found")

        new_manager: specification.TemplateManager = specification.FileTemplateManager(
            manifest_path=comparison_manifest
        )

        self.assertEqual(
            self.template_manager,
            new_manager,
            msg="The two managers were deemed different due to different contents"
        )

        shutil.rmtree(output_directory, ignore_errors=True)

    def test_database_export(self):
        template_table = "template"

        database_directory = allocate_output_directory("test_database_export")
        database_file = database_directory / "test_database_export.sqlite3"

        try:
            with sqlite3.connect(database=database_file) as database_connection:
                self.template_manager.export_to_database(table_name=template_table, connection=database_connection)

            with sqlite3.connect(database=database_file) as database_connection:
                database_template_manager: specification.TemplateManager = specification.DatabaseTemplateManager(
                    table_name=template_table,
                    connection=database_connection
                )

                for specification_type, templates in database_template_manager.get_all_templates().items():
                    control_templates = self.template_manager.get_templates(specification_type=specification_type)

                    self.assertEqual(len(templates), len(control_templates))

                    for control_template in control_templates:
                        matching_template = find(templates, lambda template: template.name == control_template.name)
                        self.assertIsNotNone(
                            matching_template,
                            msg="The database is missing a template from the file manager"
                        )
        finally:
            database_file.unlink(missing_ok=True)

    def test_evaluationspecification(self):
        specification_type = specification.EvaluationSpecification.get_specification_type()

        options: typing.Sequence[typing.Tuple[str, str]] = self.template_manager.get_options(
            specification_type=specification_type
        )

        self.assertEqual(len(options), 5)

        value_name, text_name = options[0]

        self.assertEqual(value_name, "no-template")
        self.assertEqual(text_name, "no-template")

        templates: typing.Sequence[specification.TemplateDetails] = self.template_manager.get_templates(
            specification_type=specification_type
        )

        self.assertEqual(len(templates), 5)

        self.template_matches(
            specification_type=specification_type,
            template=templates[0],
            template_name='no-template'
        )

        self.template_matches(
            specification_type=specification_type,
            template=templates[1],
            template_name='Templated Evaluation'
        )

        self.template_matches(
            specification_type=specification_type,
            template=templates[2],
            template_name="Top Half"
        )

        self.template_matches(
            specification_type=specification_type,
            template=templates[3],
            template_name="Bottom Half"
        )

        self.template_matches(
            specification_type=specification_type,
            template=templates[4],
            template_name="Multi-Template"
        )

    def template_matches(self, specification_type: str, template: specification.TemplateDetails, template_name: str):
        self.assertEqual(
            template.specification_type,
            specification_type
        )

        self.assertEqual(
            template.name,
            template_name
        )

        configuration_from_details: dict = template.get_configuration(decoder_type=TEST_DECODER)
        configuration_from_manager: dict = self.template_manager.get_template(
            specification_type=specification_type,
            name=template.name,
            decoder_type=TEST_DECODER
        )

        self.assertIn("name", configuration_from_details)
        self.assertIn("name", configuration_from_manager)

        self.assertEqual(configuration_from_manager['name'], configuration_from_details['name'])


if __name__ == '__main__':
    unittest.main()
