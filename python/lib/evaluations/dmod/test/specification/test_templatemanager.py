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


class TestSpecificationDeserialization(unittest.TestCase):
    def setUp(self) -> None:
        self.__template_manager: specification.TemplateManager = specification.FileTemplateManager(
            manifest_path=TEMPLATE_MANIFEST_PATH
        )

    def test_manager(self):
        specification_types: typing.Sequence[typing.Tuple[str, str]] = self.__template_manager.get_specification_types()

    def test_evaluationspecification(self):
        specification_type = specification.EvaluationSpecification.get_specification_type()

        options: typing.Sequence[typing.Tuple[str, str]] = self.__template_manager.get_options(
            specification_type=specification_type
        )

        self.assertEqual(len(options), 1)

        value_name, text_name = options[0]

        self.assertEqual(value_name, "no-template")
        self.assertEqual(text_name, "no-template")

        templates: typing.Sequence[specification.TemplateDetails] = self.__template_manager.get_templates(
            specification_type=specification_type
        )

        self.assertEqual(len(templates), 1)

        first_template = templates[0]

        self.assertEqual(
            first_template.specification_type,
            specification_type
        )

        self.assertEqual(
            first_template.name,
            "no-template"
        )

        configuration_from_details: dict = first_template.get_configuration(decoder_type=TEST_DECODER)
        configuration_from_manager: dict = self.__template_manager.get_template(
            specification_type=specification_type,
            name=first_template.name,
            decoder_type=TEST_DECODER
        )

        self.assertIn("name", configuration_from_details)
        self.assertIn("name", configuration_from_manager)

        self.assertEqual(configuration_from_manager['name'], configuration_from_details['name'])


if __name__ == '__main__':
    unittest.main()
