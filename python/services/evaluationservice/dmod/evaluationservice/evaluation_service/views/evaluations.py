#!/usr/bin/env python3
import typing
import os
import string

from django.views.generic import View
from django.shortcuts import render

from django.http import HttpResponse
from django.http import HttpRequest
from django.http import JsonResponse
from django.http import QueryDict

from rest_framework.views import APIView

import redis

import service.logging as logging
import utilities


EVALUATION_LIST_FIELDS = [
    b'complete',
    b'failed',
    b'last_updated',
    b'created_at'
]

EVALUATION_BOOLEAN_FIELDS = [
    b'failed',
    b'complete'
]


class EvaluationDetails(APIView):
    @classmethod
    def get_evaluations(cls, query: QueryDict) -> typing.List[typing.Dict[str, typing.Any]]:
        query = {
            key.lower(): value
            for key, value in query.items()
        }

        connection: redis.Redis = utilities.get_redis_connection()
        keys = [
            key
            for key in connection.keys(f"{utilities.redis_prefix()}*")
            if not key.endswith(b"MESSAGES") and not key.endswith(b"ERROR") and not key.endswith(b"INFO")
        ]

        evaluation_data: typing.List[typing.Dict[str, typing.Any]] = list()

        for key in keys:
            key = key.decode()
            evaluation_name: str = key.replace(utilities.redis_prefix(), "")
            evaluation_name = evaluation_name.strip(utilities.key_separator())

            evaluation: typing.Dict[str, typing.Any] = {
                "identifier": evaluation_name
            }

            evaluation_name = evaluation_name.replace("_", " ")

            if " " in evaluation_name:
                evaluation_name = evaluation_name.title()

            processed_name = [evaluation_name[0].upper()]

            for letter_index in range(len(evaluation_name) - 1):
                next_index = letter_index + 1
                current_character = evaluation_name[letter_index]
                next_character = evaluation_name[next_index]
                current_is_lowercase = current_character in string.ascii_lowercase
                next_is_uppercase = next_character in string.ascii_uppercase

                current_is_letter = current_character in string.ascii_letters
                next_is_not_letter = next_character not in string.ascii_letters
                next_is_not_whitespace = next_character not in string.whitespace

                if current_is_lowercase and next_is_uppercase:
                    processed_name.append(" ")
                elif current_is_letter and next_is_not_letter and next_is_not_whitespace:
                    processed_name.append(" ")

                if current_character in string.whitespace and next_character in string.ascii_lowercase:
                    processed_name.append(next_character.upper())
                else:
                    processed_name.append(next_character)

            evaluation['name'] = "".join(processed_name)

            data = {key: value for key, value in connection.hgetall(key).items() if key in EVALUATION_LIST_FIELDS}

            for data_key, value in data.items():
                if data_key in EVALUATION_BOOLEAN_FIELDS:
                    evaluation[data_key.decode()] = bool(int(value))
                elif isinstance(value, bytes):
                    evaluation[data_key.decode()] = value.decode()
                else:
                    evaluation[data_key.decode()] = value

            for pointer_type, pointer_key in utilities.get_evaluation_pointers(key).items():
                pointer_value_type = connection.type(pointer_key)
                pointer_value = list()

                if pointer_value_type == b'list':
                    pointer_value = [value.decode() for value in connection.lrange(pointer_key, 0, -1)]
                elif pointer_value_type == b'hash':
                    pass
                elif pointer_value_type == b'set':
                    pointer_value = [value.decode() for value in connection.smembers(pointer_key)]
                elif pointer_value_type == b'zset':
                    pointer_value = [value.decode() for value in connection.zrange(pointer_key, 0, -1)]
                elif pointer_value_type != b'none':
                    logging.warn(
                        f"Pointers to {pointer_value_type.decode()} types are not supported by "
                        f"{cls.__class__.__name__}. {pointer_type} cannot be returned in the result set"
                    )

                evaluation[pointer_type.replace("_key", "")] = pointer_value

            if not evaluation['complete']:
                evaluation['failed'] = False
            elif 'failed' in evaluation and evaluation['failed']:
                evaluation['failed'] = True
            elif 'failed' in evaluation:
                evaluation['failed'] = True
            else:
                evaluation['failed'] = False

            if "failed" in query and query['failed'] and not evaluation['failed']:
                continue
            elif "failed" in query and not query["failed"] and evaluation['failed']:
                continue

            evaluation_data.append(evaluation)
        return evaluation_data

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        listing = self.get_evaluations(request.GET)
        return JsonResponse(listing, safe=False)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        listing = self.get_evaluations(request.POST)
        return JsonResponse(listing, safe=False)


class EvaluationList(View):
    template = "evaluation_service/evaluation_listing.html"

    @classmethod
    def get_evaluations(cls) -> typing.List[typing.Dict[str, typing.Any]]:
        connection: redis.Redis = utilities.get_redis_connection()
        keys = [
            key
            for key in connection.keys(f"{utilities.redis_prefix()}*")
            if not key.endswith(b"MESSAGES") and not key.endswith(b"ERROR") and not key.endswith(b"INFO")
        ]

        evaluation_data: typing.List[typing.Dict[str, typing.Any]] = list()

        for key in keys:
            evaluation: typing.Dict[str, typing.Any] = dict()
            key = key.decode()

            evaluation_name: str = key.replace(utilities.redis_prefix(), "")
            evaluation_name = evaluation_name.strip(utilities.key_separator())

            identifier = evaluation_name

            evaluation_name = evaluation_name.replace("_", " ")
            evaluation_name = evaluation_name.title()

            evaluation['name'] = evaluation_name

            data = {key: value for key, value in connection.hgetall(key).items() if key in EVALUATION_LIST_FIELDS}

            for data_key, value in data.items():
                if data_key in EVALUATION_BOOLEAN_FIELDS:
                    evaluation[data_key.decode()] = bool(int(value))
                elif isinstance(value, bytes):
                    evaluation[data_key.decode()] = value.decode()
                else:
                    evaluation[data_key.decode()] = value

            if 'complete' in evaluation and evaluation['complete']:
                evaluation['completed'] = 'Yes' if evaluation['complete'] else 'No'
                evaluation['completed_icon'] = '/static/evaluation_service/img/ok.png'
            else:
                evaluation['completed'] = 'No'
                evaluation['completion_icon'] = '/static/evaluation_service/img/unknown.png'

            if not evaluation['complete']:
                evaluation['failed'] = 'Not Completed'
                evaluation['failed_icon'] = '/static/evaluation_service/img/unknown.png'
            elif 'failed' in evaluation and evaluation['failed']:
                evaluation['failed_icon'] = "/static/evaluation_service/img/error.png"
                evaluation['failed'] = "Fail"
            elif 'failed' in evaluation:
                evaluation['failed_icon'] = "/static/evaluation_service/img/ok.png"
                evaluation['failed'] = "Success"
            else:
                evaluation['failed'] = 'Not Completed'
                evaluation['failed_icon'] = '/static/evaluation_service/img/unknown.png'

            evaluation['listen_url'] = "/evaluation_service/" + os.path.join("listen", identifier)
            evaluation['status_url'] = "/evaluation_service/" + os.path.join("status", identifier)

            evaluation_data.append(evaluation)
        return evaluation_data

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {"evaluations": self.get_evaluations()}
        return render(request, template_name=self.template, context=context)

