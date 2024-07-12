#!/usr/bin/env python3
import typing
import os
import json
import re

from django.views.generic import View
from django.shortcuts import render
from django.shortcuts import reverse

from django.http import HttpResponse
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.http import JsonResponse

from rest_framework.views import APIView

from datetime import datetime

import utilities
from service import application_values


EVALUATION_ID_PATTERN = r"[a-zA-Z0-9\.\-_]+"

EVALUATION_TEMPLATE_PATH = os.path.join(application_values.STATIC_RESOURCES_PATH, "evaluation_template.json")

class LaunchEvaluation(APIView):
    """
    REST View used to post evaluation details and launch them out of process
    """
    def post(self, request, *args, **kwargs):
        """
        Handle a POST request

        Args:
            request: The raw request
            *args: Positional arguments coming in through the routed URL
            **kwargs: Keyword arguments coming in through the routed URL

        Returns:
            JSON data if this came from a standard request, a redirect if it came through a browser
        """
        evaluation_id = request.POST.get("evaluation_id")
        evaluation_id = evaluation_id.replace(" ", "_").replace(":", ".")
        instructions = request.POST.get("instructions")

        if 'HTTP_REFERER' in request.META:
            response_url = reverse("evaluation_service:Listen", kwargs={"channel_name": evaluation_id})
            response = HttpResponseRedirect(response_url)
        else:
            channel_key = utilities.get_channel_key(evaluation_id)
            data = {
                "channel_name": evaluation_id,
                "channel_key": channel_key,
                "channel_route": f"ws://{request.META['HTTP_HOST']}/evaluation_service/ws/channel/{channel_key}"
            }
            response = JsonResponse(data, json_dumps_params={"indent": 4})

        launch_parameters = {
            "purpose": "launch",
            "evaluation_id": evaluation_id,
            "verbosity": application_values.OUTPUT_VERBOSITY,
            "start_delay": application_values.START_DELAY,
            "instructions": instructions
        }
        connection = utilities.get_redis_connection()
        connection.xadd(application_values.EVALUATION_QUEUE_NAME, launch_parameters)

        return response


def get_evaluation_template() -> str:
    """
    Get raw text to serve as a starting point for an evaluation
    """
    with open(EVALUATION_TEMPLATE_PATH, "r") as evaluation_template_file:
        return evaluation_template_file.read()


def generate_evaluation_id() -> str:
    """
    Generate a unique evaluation id
    """
    current_date = datetime.now()
    date_representation = current_date.strftime("%m-%d_%H.%M")
    evaluation_id = f"manual_evaluation_at_{date_representation}"
    return evaluation_id


class ReadyListenEvaluation(View):
    """
    View to show an editor used for editing, launching, and listening to an evaluation
    """
    template = "evaluation_service/ready_evaluation.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Handle a GET request

        Args:
            request: The request sent over HTTP

        Returns:
            A response containing HTML information needed to show the Evaluation Ready page
        """
        context = {
            "evaluation_template": get_evaluation_template(),
            "launch_url": "/ws/launch",
            "metrics_url": "/evaluation_service/metrics",
            "generated_evaluation_id": generate_evaluation_id(),
            "evaluation_id_pattern": EVALUATION_ID_PATTERN,
            "geometry_name": "",
            "show_map": True,
            "production": not application_values.in_debug_mode()
        }
        return render(request, template_name=self.template, context=context)
