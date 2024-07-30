"""
Defines tests used to check that specification template rest operations work as intended
"""
from __future__ import annotations

import json
import os
import typing
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from dmod.core.common import Status
from dmod.core.common import find
from dmod.evaluations.specification import TemplateDetails

from dmod.evaluations.specification.template import FileTemplateManager
from rest_framework.authtoken.models import Token

from evaluation_service import models
from evaluation_service.messages import TemplateAction

TEMPLATE_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "templates", "template_manifest.json")

USERNAME = "template_test_user"
FIRST_NAME = "Template-Test"
LAST_NAME = "User"
PASSWORD = "TestPassword"


class TemplateViewTest(TestCase):
    test_user: User
    token: Token
    manager: FileTemplateManager

    @classmethod
    def setUpTestData(cls):
        for wrapper in models.get_model_wrappers():
            wrapper.disable_concurrency()

        cls.test_user = User.objects.create_user(username=USERNAME, email="", password=PASSWORD)
        cls.test_user.first_name = FIRST_NAME
        cls.test_user.last_name = LAST_NAME
        cls.test_user.save()

        cls.token = Token.objects.create(user=cls.test_user)

        cls.manager = FileTemplateManager(path=TEMPLATE_MANIFEST_PATH)

        for template_details_group in cls.manager.get_all_templates().values():
            for template_details in template_details_group:
                new_model = models.SpecificationTemplate.from_template_details(cls.test_user, template_details)
                new_model.save()

    def test_get_templatespecification_types(self):
        get_response = self.client.get("/evaluation_service/templates/types")
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)

        get_data = get_response.json()
        self.assertIn("response_to", get_data)
        self.assertIn("response_time", get_data)
        self.assertIn("errors", get_data)
        self.assertIn("result", get_data)
        self.assertIn("specification_types", get_data)

        self.assertEqual(get_data.get('response_to'), TemplateAction.GET_SPECIFICATION_TYPES)
        self.assertEqual(get_data.get('errors'), list())
        self.assertEqual(get_data.get('result'), Status.SUCCESS)

        specification_types: typing.List = get_data.get('specification_types')

        def verify_element(text: str, value: str):
            index = specification_types.index({"value": value, "text": text})
            self.assertGreater(index, -1)

        verify_element("Backend", "BackendSpecification")
        verify_element("Loader", "LoaderSpecification")
        verify_element("Field Mapping", "FieldMappingSpecification")
        verify_element("Associated Field", "AssociatedField")
        verify_element("Value Selector", "ValueSelector")
        verify_element("Location", "LocationSpecification")
        verify_element("Unit Definition", "UnitDefinition")
        verify_element("Metric", "MetricSpecification")
        verify_element("Scheme", "SchemeSpecification")
        verify_element("Threshold Definition", "ThresholdDefinition")
        verify_element("Threshold Application Rules", "ThresholdApplicationRules")
        verify_element("Evaluation", "EvaluationSpecification")

        post_response = self.client.post("/evaluation_service/templates/types")
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)
        post_data = post_response.json()
        self.assertIn("response_to", post_data)
        self.assertIn("response_time", post_data)
        self.assertIn("errors", post_data)
        self.assertIn("result", post_data)
        self.assertIn("specification_types", post_data)

        self.assertEqual(post_data.get('response_to'), TemplateAction.GET_SPECIFICATION_TYPES)
        self.assertEqual(post_data.get('errors'), list())
        self.assertEqual(post_data.get('result'), Status.SUCCESS)

        self.assertEqual(post_data.get('specification_types'), specification_types)

    def test_search_templates(self):
        address = "/evaluation_service/templates"

        arguments = {
            "author": USERNAME,
            "specification_type": "AssociatedField"
        }

        get_response = self.client.get(os.path.join(address, "search"), data=arguments)
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)
        get_data = get_response.json()

        self.assertEqual(get_data['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(get_data.get("errors", list())), 0)
        templates = get_data.get("templates")

        self.assertIsNotNone(templates)
        self.assertEqual(len(templates), 1)

        self.assertIn("AssociatedField", templates)
        self.assertEqual(len(templates['AssociatedField']), 5)

        expected_field_names = [
            "NWIS Value Date",
            "NWIS Observation Location",
            "NWIS Unit", "Columnar Date",
            "Observed Site Number JSON Value"
        ]

        for found_field in templates['AssociatedField']:
            self.assertIn("description", found_field)
            self.assertIn("name", found_field)
            self.assertIn("specification_type", found_field)
            self.assertIn("id", found_field)
            self.assertIn("author", found_field)

            if found_field['name'] in expected_field_names:
                expected_field_names.remove(found_field['name'])

        self.assertEqual(len(expected_field_names), 0)

        post_response = self.client.post(os.path.join(address, "search"), data=arguments)
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)
        post_data = post_response.json()

        self.assertEqual(post_data['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(post_data.get("errors", list())), 0)
        post_templates = post_data.get("templates")

        self.assertEqual(post_templates, templates)

        path_response = self.client.get(os.path.join(address, USERNAME, "AssociatedField"))
        self.assertEqual(path_response.status_code, HTTPStatus.CREATED)
        path_data = path_response.json()

        self.assertEqual(path_data['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(path_data.get("errors", list())), 0)
        path_templates = path_data.get("templates")

        self.assertEqual(path_templates, templates)

        duplicate_path_response = self.client.get(
            os.path.join(address, USERNAME, "AssociatedField"),
            data=arguments
        )
        self.assertEqual(duplicate_path_response.status_code, HTTPStatus.CREATED)
        duplicate_path_data = duplicate_path_response.json()

        self.assertEqual(duplicate_path_data['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(duplicate_path_data.get("errors", list())), 0)
        duplicate_path_templates = duplicate_path_data.get("templates")

        self.assertEqual(duplicate_path_templates, templates)

        conflicting_path_response = self.client.get(
            os.path.join(address, USERNAME, "SomethingElse"),
            data=arguments
        )
        self.assertEqual(conflicting_path_response.status_code, HTTPStatus.BAD_REQUEST)

        value_date = None

        for found_field in templates['AssociatedField']:
            if found_field['name'] == "NWIS Value Date":
                value_date = found_field
                break

        self.assertIsNotNone(value_date)

        arguments['name'] = value_date['name']

        post_response_with_name = self.client.post(os.path.join(address, "search"), data=arguments)
        self.assertEqual(post_response_with_name.status_code, HTTPStatus.CREATED)
        post_data_with_name = post_response_with_name.json()

        self.assertEqual(post_data_with_name['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(post_data_with_name.get("errors", list())), 0)
        post_templates_with_name = post_data_with_name.get("templates")

        self.assertEqual(len(post_templates_with_name), 1)

        self.assertIn("AssociatedField", post_templates_with_name)
        self.assertEqual(len(post_templates_with_name['AssociatedField']), 1)

        arguments = {
            "name": value_date['name']
        }

        post_response_with_only_name = self.client.post(os.path.join(address, "search"), data=arguments)
        self.assertEqual(post_response_with_only_name.status_code, HTTPStatus.CREATED)
        post_data_with_only_name = post_response_with_only_name.json()

        self.assertEqual(post_data_with_only_name['response_to'], 'SEARCH_TEMPLATES')
        self.assertEqual(len(post_data_with_only_name.get("errors", list())), 0)
        post_templates_with_only_name = post_data_with_only_name.get("templates")

        self.assertEqual(len(post_templates_with_only_name), 1)

        self.assertIn("AssociatedField", post_templates_with_only_name)
        self.assertEqual(len(post_templates_with_only_name['AssociatedField']), 1)

        field = post_templates_with_only_name['AssociatedField'][0]

        self.assertEqual(field['description'].lower(), "the value date for nwis input")
        self.assertEqual(field['name'].lower(), "nwis value date")
        self.assertEqual(field['specification_type'], 'AssociatedField')
        self.assertEqual(field['author'], USERNAME)

        all_template_response = self.client.get(os.path.join(address, USERNAME))
        self.assertEqual(all_template_response.status_code, HTTPStatus.CREATED)
        all_template_data = all_template_response.json()
        all_templates = all_template_data['templates']
        all_configured_templates = self.manager.get_all_templates()

        self.assertEqual(len(all_configured_templates), len(all_templates))

        for specification_type, received_templates in all_templates.items():
            self.assertIn(specification_type, all_configured_templates)

            configured_templates: typing.Sequence[TemplateDetails] = all_configured_templates[specification_type]

            self.assertEqual(len(configured_templates), len(received_templates))

            for received_template in received_templates:
                matching_template = find(
                    configured_templates,
                    lambda template: template.name == received_template['name']
                                     and template.description == received_template['description']
                )

                self.assertIsNotNone(matching_template)

    def test_get_all_templates(self):
        get_response = self.client.get(
            "/evaluation_service/templates/"
        )

        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)

        get_data = get_response.json()
        self.assertEqual(get_data.get('result'), Status.SUCCESS)
        self.assertEqual(get_data.get("response_to"), TemplateAction.GET_ALL_TEMPLATES)

        self.assertIn("templates", get_data)
        templates = get_data['templates']

        self.assertTrue(isinstance(templates, typing.Mapping))
        self.assertEqual(len(templates), 12)

        self.assertIn("BackendSpecification", templates)
        self.assertIn("FieldMappingSpecification", templates)
        self.assertIn("AssociatedField", templates)
        self.assertIn("ValueSelector", templates)
        self.assertIn("LocationSpecification", templates)
        self.assertIn("SchemeSpecification", templates)
        self.assertIn("ThresholdDefinition", templates)
        self.assertIn("ThresholdApplicationRules", templates)
        self.assertIn("EvaluationSpecification", templates)
        self.assertIn("CrosswalkSpecification", templates)
        self.assertIn("DataSourceSpecification", templates)
        self.assertIn("ThresholdSpecification", templates)

        self.assertEqual(len(templates['BackendSpecification']), 4)
        self.assertEqual(len(templates['FieldMappingSpecification']), 3)
        self.assertEqual(len(templates['AssociatedField']), 5)
        self.assertEqual(len(templates['ValueSelector']), 4)
        self.assertEqual(len(templates['LocationSpecification']), 3)
        self.assertEqual(len(templates['SchemeSpecification']), 1)
        self.assertEqual(len(templates['ThresholdDefinition']), 3)
        self.assertEqual(len(templates['ThresholdApplicationRules']), 1)
        self.assertEqual(len(templates['EvaluationSpecification']), 5)
        self.assertEqual(len(templates['CrosswalkSpecification']), 2)
        self.assertEqual(len(templates["DataSourceSpecification"]), 4)
        self.assertEqual(len(templates["ThresholdSpecification"]), 2)

        post_response = self.client.post(
            "/evaluation_service/templates/"
        )

        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data.get('result'), Status.SUCCESS)
        self.assertEqual(post_data.get("response_to"), TemplateAction.GET_ALL_TEMPLATES)

        self.assertIn("templates", post_data)
        self.assertEqual(templates, post_data['templates'])

    def test_get_template(self):
        get_response = self.client.get(
            "/evaluation_service/templates/get",
            data={
                "specification_type": "CrosswalkSpecification",
                "name": "Crosswalk",
                "author": self.test_user.username
            }
        )
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)
        get_data = get_response.json()
        self.assertEqual(get_data.get('response_to'), TemplateAction.GET_TEMPLATE)
        self.assertEqual(get_data.get('result'), Status.SUCCESS)
        self.assertIn("template", get_data)

        try:
            json.loads(get_data.get('template'))
        except BaseException as exception:
            self.fail(f"Passed template cannot be deserialized: {str(exception)}")

        parameterized_get_response = self.client.get(
            f"/evaluation_service/templates/{self.test_user.username}/CrosswalkSpecification/Crosswalk"
        )
        self.assertEqual(parameterized_get_response.status_code, HTTPStatus.CREATED)
        parameterized_get_data = parameterized_get_response.json()
        self.assertEqual(parameterized_get_data.get('response_to'), TemplateAction.GET_TEMPLATE)

        self.assertIn("template", parameterized_get_data)
        self.assertEqual(parameterized_get_data.get('template'), get_data.get('template'))

        missing_get_response = self.client.get(
            "/evaluation_service/templates/get",
            data={
                "specification_type": "CrosswalkSpecification",
                "name": "Crosswalkstugsdfsf",
                "author": self.test_user.username
            }
        )
        self.assertEqual(missing_get_response.status_code, HTTPStatus.NOT_FOUND)
        missing_get_data = missing_get_response.json()
        self.assertEqual(missing_get_data.get('response_to'), TemplateAction.GET_TEMPLATE)
        self.assertEqual(missing_get_data.get('result'), Status.ERROR)
        self.assertEqual(len(missing_get_data.get('errors')), 1)

        post_response = self.client.post(
            "/evaluation_service/templates/get",
            data={
                "specification_type": "CrosswalkSpecification",
                "name": "Crosswalk",
                "author": self.test_user.username
            }
        )
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)
        post_data = post_response.json()
        self.assertEqual(post_data.get('response_to'), TemplateAction.GET_TEMPLATE)
        self.assertEqual(post_data.get('result'), Status.SUCCESS)
        self.assertIn("template", post_data)

        self.assertEqual(get_data['template'], post_data['template'])

    def test_get_template_by_id(self):
        get_response = self.client.get("/evaluation_service/templates/1")
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)
        get_data = get_response.json()

        incorrect_get_response = self.client.get("/evaluation_service/templates/900")
        self.assertEqual(incorrect_get_response.status_code, HTTPStatus.NOT_FOUND)
        incorrect_get_data = incorrect_get_response.json()

        post_response = self.client.post("/evaluation_service/templates/1")
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)
        post_data = post_response.json()

        incorrect_post_response = self.client.post("/evaluation_service/templates/900")
        self.assertEqual(incorrect_post_response.status_code, HTTPStatus.NOT_FOUND)
        incorrect_post_data = incorrect_post_response.json()


    def test_save_template(self):
        pass
