import os.path
import unittest
import json
import pathlib
import typing

from ...evaluations import specification
from ..common import RESOURCE_DIRECTORY

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
            ('ThresholdApplicationRules', 'Threshold Application Rules')
        ]
        self.assertEqual(len(specification_types), len(expected_types))

        for type_pair in expected_types:
            self.assertIn(
                type_pair,
                specification_types,
                f"The specification type pair of ({type_pair[0]}, {type_pair[1]}) wasn't returned from the template manager"
            )

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
