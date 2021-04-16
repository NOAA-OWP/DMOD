#!/usr/bin/env python

from django.http import HttpResponse
from django.http import JsonResponse

IS_EXECUTOR = True
FRIENDLY_NAME = "NextGen"


def execute(configuration: dict) -> HttpResponse:

    # TODO: Actually wire up the execution instead of just returning the config
    return JsonResponse(data=configuration)
