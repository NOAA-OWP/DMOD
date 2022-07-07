#!/usr/bin/env python3
import typing
import os

from django.views.generic import View
from django.shortcuts import render

from django.http import HttpResponse
from django.http import HttpRequest

import redis


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


class EvaluationList(View):
    template = "evaluation_service/evaluation_listing.html"

    def get_evaluations(self, request: HttpRequest) -> typing.List[typing.Dict[str, typing.Any]]:
        connection: redis.Redis = utilities.get_redis_connection()
        keys = [
            key
            for key in connection.keys(f"{utilities.redis_prefix()}*")
            if not key.endswith(b"MESSAGES") and not key.endswith(b"ERROR") and not key.endswith(b"INFO")
        ]

        evaluation_data: typing.List[typing.Dict[str, typing.Any]] = list()

        for key in keys:
            evaluation: typing.Dict[str, typing.Any] = dict()

            evaluation_name = key.decode().replace(utilities.redis_prefix(), "")

            while evaluation_name.startswith(":"):
                evaluation_name = evaluation_name[1:]

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
        context = {"evaluations": self.get_evaluations(request)}
        return render(request, template_name=self.template, context=context)

