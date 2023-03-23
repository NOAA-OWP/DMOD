import os.path
import unittest
import json
import pathlib
import typing

from ...evaluations import specification
from ..common import ConstructionTest
from ..common import RESOURCE_DIRECTORY


NO_TEMPLATE_CONFIGURATION = os.path.join(
    RESOURCE_DIRECTORY,
    "evaluations",
    "templates",
    "evaluation",
    "untemplated_configuration.json"
)
TEMPLATE_MANIFEST_PATH = os.path.join(RESOURCE_DIRECTORY, "evaluations", "templates", "template_manifest.json")

TEST_DECODER = None


class TestSpecificationDeserialization(unittest.TestCase):
    def setUp(self) -> None:
        self.__template_manager: specification.TemplateManager = specification.FileTemplateManager(
            manifest_path=TEMPLATE_MANIFEST_PATH
        )

        with open(NO_TEMPLATE_CONFIGURATION, 'r') as no_template_configuration_file:
            self.__no_template_configuration = json.load(fp=no_template_configuration_file, cls=TEST_DECODER)

    def test_notemplate_deserialization(self):
        pass


if __name__ == '__main__':
    unittest.main()
