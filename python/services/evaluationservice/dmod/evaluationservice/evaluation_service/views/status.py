#!/usr/bin/env python3
import typing

from django.views.generic import View

from django.http import HttpResponse
from django.http import HttpRequest
from django.http import JsonResponse

import redis


import utilities

EVALUATION_BOOLEAN_FIELDS = [
    b'failed',
    b'complete'
]


class EvaluationStatus(View):
    def get_status_info(self, name: str) -> dict:
        status = dict()

        connection: redis.Redis = utilities.get_redis_connection()

        key = name.replace(" ", "_")
        if not name.startswith(utilities.redis_prefix()):
            prefix = utilities.redis_prefix()
            if not prefix.endswith("::"):
                prefix += "::"
            key = prefix + name

        key = key.lower()

        possible_keys = [
            existing_key.decode()
            for existing_key in connection.keys(utilities.redis_prefix() + "*")
            if existing_key.decode().lower() == key
        ]

        if not possible_keys:
            return {
                "ERROR": f"No evaluations with a name like '{name}' could be found"
            }

        key = possible_keys[0]

        evaluation_data = connection.hgetall(key)

        if not evaluation_data:
            return status

        for key, value in evaluation_data.items():
            if key in EVALUATION_BOOLEAN_FIELDS:
                status[key.decode()] = bool(int(value))
                continue

            key = key.decode()
            if isinstance(value, bytes):
                value = value.decode()

            if key.endswith("_key"):
                list_name = key.replace("_key", "")
                status[list_name] = [
                    member.decode() if isinstance(member, bytes) else member
                    for member in connection.lrange(value, 0, -1)
                ]
                continue

            status[key] = value

        return status

    def get(self, request: HttpRequest, name: str = None) -> HttpResponse:
        if name:
            status = self.get_status_info(name)
        elif 'name' in request.GET:
            status = self.get_status_info(request.GET['name'])
        else:
            status = {
                "ERROR": "The name of the evaluation was missing"
            }

        return JsonResponse(status)

    def post(self, request: HttpRequest, name: str = None) -> HttpResponse:
        if name:
            status = self.get_status_info(name)
        elif 'name' in request.POST:
            status = self.get_status_info(request.POST['name'])
        else:
            status = {
                "ERROR": "The name of the evaluation was missing"
            }

        return JsonResponse(status)
