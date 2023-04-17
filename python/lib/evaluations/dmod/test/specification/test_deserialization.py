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

    @property
    def template_manager(self) -> specification.TemplateManager:
        return self.__template_manager

    def test_multitemplate(self):
        multitemplate = self.template_manager.get_template(
            specification_type=specification.EvaluationSpecification,
            name="Multi-Template"
        )

        single_instance = specification.EvaluationSpecification.create(
            data=multitemplate,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.EvaluationSpecification.create(
            data={"template_name": "no-template"},
            template_manager=self.template_manager
        )

        self.assertEqual(single_instance, pure_template_instance)

    def test_evaluation_deserialization(self):
        normal_specification = self.template_manager.get_template(
            specification_type=specification.EvaluationSpecification,
            name="no-template"
        )

        all_template_spec = self.template_manager.get_template(
            specification_type=specification.EvaluationSpecification,
            name="Templated Evaluation"
        )

        normal_instance = specification.EvaluationSpecification.create(
            data=normal_specification,
            template_manager=self.template_manager
        )

        templated_instance = specification.EvaluationSpecification.create(
            data=all_template_spec,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.EvaluationSpecification.create(
            data={"template_name": "no-template"},
            template_manager=self.template_manager
        )

        self.assertEqual(normal_instance, templated_instance)
        self.assertEqual(normal_instance, pure_template_instance)

    def test_crosswalk_deserialization(self):
        normal_specification = self.template_manager.get_template(
            specification_type=specification.CrosswalkSpecification,
            name="Crosswalk"
        )

        all_template_spec = self.template_manager.get_template(
            specification_type=specification.CrosswalkSpecification,
            name="Templated Crosswalk"
        )

        normal_instance = specification.CrosswalkSpecification.create(
            data=normal_specification,
            template_manager=self.template_manager
        )

        templated_instance = specification.CrosswalkSpecification.create(
            data=all_template_spec,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.CrosswalkSpecification.create(
            data={"template_name": "Crosswalk"},
            template_manager=self.template_manager
        )

        self.assertEqual(normal_instance, templated_instance)
        self.assertEqual(normal_instance, pure_template_instance)

    def test_thresholdspecification_deserialization(self):
        normal_nwis_stat_spec = self.template_manager.get_template(
            specification_type=specification.ThresholdSpecification,
            name="NWIS Stat Percentiles"
        )

        all_template_stat_spec = self.template_manager.get_template(
            specification_type=specification.ThresholdSpecification,
            name="All Templates for NWIS Stat Percentiles"
        )

        normal_instance = specification.ThresholdSpecification.create(
            data=normal_nwis_stat_spec,
            template_manager=self.template_manager
        )

        templated_instance = specification.ThresholdSpecification.create(
            data=all_template_stat_spec,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.ThresholdSpecification.create(
            data={"template_name": "NWIS Stat Percentiles"},
            template_manager=self.template_manager
        )

        self.assertEqual(normal_instance, templated_instance)
        self.assertEqual(normal_instance, pure_template_instance)

    def test_datasourcespecification_deserialization(self):
        normal_specification = self.template_manager.get_template(
            specification_type=specification.DataSourceSpecification,
            name="Observations"
        )

        all_template_stat_spec = self.template_manager.get_template(
            specification_type=specification.DataSourceSpecification,
            name="Observations from Templates"
        )

        normal_instance = specification.DataSourceSpecification.create(
            data=normal_specification,
            template_manager=self.template_manager
        )

        templated_instance = specification.DataSourceSpecification.create(
            data=all_template_stat_spec,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.DataSourceSpecification.create(
            data={"template_name": "Observations"},
            template_manager=self.template_manager
        )

        self.assertEqual(normal_instance, templated_instance)
        self.assertEqual(normal_instance, pure_template_instance)

    def test_value_selector_deserialization(self):
        normal_specification = self.template_manager.get_template(
            specification_type=specification.ValueSelector,
            name="NWIS Record"
        )

        all_template_spec = self.template_manager.get_template(
            specification_type=specification.ValueSelector,
            name="Templated NWIS Record"
        )

        normal_instance = specification.ValueSelector.create(
            data=normal_specification,
            template_manager=self.template_manager
        )

        templated_instance = specification.ValueSelector.create(
            data=all_template_spec,
            template_manager=self.template_manager
        )

        pure_template_instance = specification.ValueSelector.create(
            data={"template_name": "NWIS Record"},
            template_manager=self.template_manager
        )

        self.assertEqual(normal_instance, templated_instance)
        self.assertEqual(normal_instance, pure_template_instance)


if __name__ == '__main__':
    unittest.main()
