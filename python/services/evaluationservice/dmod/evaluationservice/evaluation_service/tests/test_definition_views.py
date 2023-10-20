"""
Tests to check if rest requests for evaluation definitions work
"""
from __future__ import annotations

import json
import os

from http import HTTPStatus

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.test import TestCase

from evaluation_service import models
from utilities import create_basic_credentials
from utilities import create_token_credentials

EVALUATION_ONE_PATH = os.path.join(os.path.dirname(__file__), "data", "evaluation_one.json")
EVALUATION_TWO_PATH = os.path.join(os.path.dirname(__file__), "data", "evaluation_two.json")
EVALUATION_THREE_PATH = os.path.join(os.path.dirname(__file__), "data", "evaluation_three.json")
EVALUATION_FOUR_PATH = os.path.join(os.path.dirname(__file__), "data", "evaluation_four.json")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%SZ"


USERNAME = "definition_test_user"
PASSWORD = "TestPassword"
FIRST_NAME = "Definition-Test"
LAST_NAME = "User"


class DefinitionViewTest(TestCase):
    """
    Tests used to ensure that core definition operations behave as expected
    """
    first_configuration: str

    second_configuration: str

    third_configuration: str

    fourth_configuration: str

    test_user: User
    token: Token

    @classmethod
    def setUpTestData(cls):
        """
        Add in the basic test data, set up a User, and create a token for said user
        """
        # Disable all possible concurrency with the model wrappers - running with possible concurrency here can
        # - and will - lead to issues like deadlocks.
        for wrapper in models.get_model_wrappers():
            wrapper.disable_concurrency()

        # Create a new user and make them a superuser in order to avoid any possible data model permissions issues
        cls.test_user = User.objects.create_superuser(username=USERNAME, email="", password=PASSWORD)
        cls.test_user.first_name = FIRST_NAME
        cls.test_user.last_name = LAST_NAME
        cls.test_user.save()

        cls.token = Token.objects.create(user=cls.test_user)

        with open(EVALUATION_ONE_PATH) as first_evaluation_file:
            cls.first_configuration = first_evaluation_file.read()

        models.EvaluationDefinitionCommunicator.create(
            name="Evaluation One",
            author="Ichabod Crane",
            description="The first definition",
            definition=cls.first_configuration,
            owner=cls.test_user
        )

        with open(EVALUATION_TWO_PATH) as second_evaluation_file:
            cls.second_configuration = second_evaluation_file.read()

        models.EvaluationDefinitionCommunicator.create(
            name="Evaluation Two",
            author="Jar-Jar Binks",
            description="The second definition",
            definition=cls.second_configuration,
            owner=cls.test_user
        )

        with open(EVALUATION_THREE_PATH) as third_evaluation_file:
            cls.third_configuration = third_evaluation_file.read()

        models.EvaluationDefinitionCommunicator.create(
            name="Evaluation Three",
            author="Burt Reynolds",
            description="The third definition",
            definition=cls.third_configuration,
            owner=cls.test_user
        )

        with open(EVALUATION_FOUR_PATH) as fourth_evaluation_file:
            cls.fourth_configuration = fourth_evaluation_file.read()

        models.EvaluationDefinitionCommunicator.create(
            name="Evaluation Four",
            author="Ichabod Crane",
            description="The fourth definition",
            definition=cls.fourth_configuration,
            owner=cls.test_user
        )

    def test_get_all_definitions(self):
        """
        Test to make sure that both get and post requests to get all definitions correct return every definition that
        has been added
        """
        first_approach = self.client.get("/evaluation_service/definitions")
        first_data = first_approach.json()
        self.assertEqual(first_approach.status_code, HTTPStatus.CREATED)
        self.assertIn("definitions", first_data)
        self.assertIn("response_to", first_data)
        self.assertEqual(first_data['response_to'], "SEARCH_FOR_DEFINITION")
        self.assertIn("errors", first_data)
        self.assertEqual(len(first_data['errors']), 0)
        self.assertIn("result", first_data)
        self.assertEqual(len(first_data['definitions']), 4)

        second_approach = self.client.get("/evaluation_service/definitions/search")
        self.assertEqual(second_approach.status_code, HTTPStatus.CREATED)
        second_data = second_approach.json()

        self.assertEqual(first_data['response_to'], second_data['response_to'])
        self.assertEqual(first_data['errors'], second_data['errors'])
        self.assertEqual(first_data['definitions'], second_data['definitions'])

        expected_records = [
            {
                'definition_id': 1,
                'author': 'Ichabod Crane',
                'title': 'Evaluation One',
                'description': 'The first definition',
            },
            {
                'definition_id': 2,
                'author': 'Jar-Jar Binks',
                'title': 'Evaluation Two',
                'description': 'The second definition',
            },
            {
                'definition_id': 3,
                'author': 'Burt Reynolds',
                'title': 'Evaluation Three',
                'description': 'The third definition',
            },
            {
                'definition_id': 4,
                'author': 'Ichabod Crane',
                'title': 'Evaluation Four',
                'description': 'The fourth definition',
            },
        ]

        for definition in first_data['definitions']:
            self.assertIn("definition_id", definition)
            self.assertIn("author", definition)
            self.assertIn("title", definition)
            self.assertIn("description", definition)
            matching_definition = None

            for expected_definition in expected_records:
                if expected_definition['definition_id'] != definition['definition_id']:
                    continue
                matching_definition = expected_definition
                self.assertEqual(expected_definition['author'], definition['author'])
                self.assertEqual(expected_definition['title'], definition['title'])
                self.assertEqual(expected_definition['description'], definition['description'])

            if matching_definition is not None:
                expected_records.remove(matching_definition)

    def test_search_definitions(self):
        """
        Check to see if get and post requests return messages when needed and that a query with no results correctly
        returns an empty list and no errors
        """
        get_response = self.client.get("/evaluation_service/definitions/search?author=Ichabod Crane")
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)

        get_data = get_response.json()
        self.assertEqual(get_data['response_to'], "SEARCH_FOR_DEFINITION")
        self.assertEqual(len(get_data['errors']), 0)
        self.assertEqual(get_data['result'], "SUCCESS")
        self.assertEqual(len(get_data['definitions']), 2)

        first_definition = get_data['definitions'][0]
        self.assertEqual(first_definition['author'], "Ichabod Crane")
        self.assertEqual(first_definition['title'], 'Evaluation One')
        self.assertEqual(first_definition['description'], "The first definition")

        second_definition = get_data['definitions'][1]
        self.assertEqual(second_definition['author'], "Ichabod Crane")
        self.assertEqual(second_definition['title'], 'Evaluation Four')
        self.assertEqual(second_definition['description'], "The fourth definition")

        post_response = self.client.post("/evaluation_service/definitions/search", data={"author": "Ichabod Crane"})
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['response_to'], "SEARCH_FOR_DEFINITION")
        self.assertEqual(len(post_data['errors']), 0)
        self.assertEqual(post_data['result'], "SUCCESS")
        self.assertEqual(len(post_data['definitions']), 2)

        self.assertDictEqual(get_data['definitions'][0], post_data['definitions'][0])
        self.assertDictEqual(get_data['definitions'][1], post_data['definitions'][1])

        get_response = self.client.get("/evaluation_service/definitions/search?author=Headless Horseman")
        self.assertEqual(get_response.status_code, HTTPStatus.CREATED)
        get_data = get_response.json()
        self.assertEqual(get_data['response_to'], "SEARCH_FOR_DEFINITION")
        self.assertEqual(len(get_data['errors']), 0)
        self.assertEqual(get_data['result'], 'SUCCESS')
        self.assertEqual(len(get_data['definitions']), 0)


    def test_get_definition(self):
        """
        Test to make sure the first definition can be retrieved by id and test to see if invalid input yields
        the correct error
        """
        get_response = self.client.get("/evaluation_service/definitions/1")
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        get_data = get_response.json()
        self.assertEqual(get_data['response_to'], "GET_DEFINITION")
        self.assertEqual(len(get_data['errors']), 0)
        self.assertEqual(get_data['result'], 'SUCCESS')
        self.assertEqual(get_data['author'], "Ichabod Crane")
        self.assertEqual(get_data['title'], 'Evaluation One')
        self.assertEqual(get_data['description'], "The first definition")
        self.assertEqual(get_data['definition'], self.first_configuration)

        get_response = self.client.get("/evaluation_service/definitions/77")
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_validate_definition(self):
        """
        Test to make sure that data cannot be validated via 'GET', that validating correct definitions yields the
        correct status, and that evaluating obviously incorrect data yields validation errors yet does not create
        HTTP errors - an 'error' in this context is appreciated, not an indication of communication failure
        """
        get_response = self.client.get("/evaluation_service/definitions/validate?definition={}")
        self.assertEqual(get_response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        post_arguments = {
            "definition": self.first_configuration
        }

        post_response = self.client.post("/evaluation_service/definitions/validate/", data=post_arguments)
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['response_to'], "VALIDATE_DEFINITION")
        self.assertEqual(len(post_data['errors']), 0)
        self.assertEqual(post_data['result'], "SUCCESS")
        self.assertEqual(len(post_data['messages']), 0)

        post_arguments['definition'] = "{}"
        post_response = self.client.post("/evaluation_service/definitions/validate/", data=post_arguments)
        post_data = post_response.json()
        self.assertEqual(post_data['response_to'], "VALIDATE_DEFINITION")
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)
        self.assertEqual(post_data['result'], "ERROR")
        self.assertEqual(len(post_data["errors"]), 1)
        self.assertEqual(len(post_data['messages']), 1)
        self.assertEqual(post_data['messages'][0]['message'], post_data['errors'][0])
        self.assertEqual(post_data['messages'][0]['level'], "ERROR")

    def test_save_definition(self):
        """
        Test to ensure that data cannot be saved via 'GET'
        """
        get_response = self.client.get("/evaluation_service/definitions/save?definition={}")
        self.assertEqual(get_response.status_code, HTTPStatus.UNAUTHORIZED)

        post_arguments = {
            "definition": self.first_configuration,
            "author": "Some Other User",
            "description": "An example of a new definition",
            "title": "Some Copied Definition"
        }
        post_response = self.client.post("/evaluation_service/definitions/save", data=post_arguments)
        self.assertEqual(post_response.status_code, HTTPStatus.UNAUTHORIZED)

        post_response = self.client.get(
            "/evaluation_service/definitions/save",
            data=post_arguments,
            **create_token_credentials(self.token.key)
        )
        self.assertEqual(post_response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        post_response = self.client.post(
            "/evaluation_service/definitions/save",
            data=post_arguments,
            **create_token_credentials(self.token.key)
        )
        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['author'], post_arguments['author'])
        self.assertEqual(post_data['title'], post_arguments['title'])
        self.assertEqual(post_data['description'], post_arguments['description'])
        self.assertEqual(post_data['response_to'], 'SAVE_DEFINITION')
        self.assertEqual(len(post_data['errors']), 0)
        self.assertEqual(post_data['result'], 'SUCCESS')
        self.assertEqual(post_data['created'], True)

        post_arguments = {
            "definition": self.first_configuration,
            "author": "Basic Auth User",
            "description": "An example testing basic auth",
            "title": "Some other Copied Definition"
        }

        post_response = self.client.post(
            "/evaluation_service/definitions/save",
            data=post_arguments,
            **create_basic_credentials(USERNAME, PASSWORD)
        )

        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['author'], post_arguments['author'])
        self.assertEqual(post_data['title'], post_arguments['title'])
        self.assertEqual(post_data['description'], post_arguments['description'])
        self.assertEqual(post_data['response_to'], 'SAVE_DEFINITION')
        self.assertEqual(len(post_data['errors']), 0)
        self.assertEqual(post_data['result'], 'SUCCESS')
        self.assertEqual(post_data['created'], True)
        self.assertEqual(post_data['definition_id'], 6)

        # Test to make sure the json can be edited but maintain core attributes of the definition
        new_title = "Bosephus"

        json_to_update = json.loads(post_arguments['definition'])
        json_to_update['name'] = new_title
        post_arguments['definition'] = json.dumps(json_to_update, indent=4)
        post_arguments['definition_id'] = 6

        post_response = self.client.post(
            "/evaluation_service/definitions/save",
            data=post_arguments,
            **create_basic_credentials(USERNAME, PASSWORD)
        )

        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['definition_id'], 6)

        json_to_check = json.loads(post_arguments['definition'])

        self.assertEqual(json_to_check['name'], new_title)

        new_title = "Edited title"

        post_arguments['title'] = new_title

        # Test to make sure that core attributes of the definition can be changed without changing the id
        post_response = self.client.post(
            "/evaluation_service/definitions/save",
            data=post_arguments,
            **create_basic_credentials(USERNAME, PASSWORD)
        )

        self.assertEqual(post_response.status_code, HTTPStatus.CREATED)

        post_data = post_response.json()
        self.assertEqual(post_data['definition_id'], 6)
        self.assertEqual(post_data['title'], new_title)




