from django.http import HttpRequest
from django.http import HttpResponseBadRequest
from django.views import View
from django.shortcuts import render

from rest_framework.views import APIView

from .. import configuration as configuration_generator
from .. import executors

import logging
logger = logging.getLogger("gui_log")


class CreateConfiguration(View):
    def post(self, request: HttpRequest):
        framework = request.POST.get('framework')
        editor_name = configuration_generator.get_editor_name(framework)
        payload = configuration_generator.get_editor_parameters(framework, request.POST)
        return render(request, editor_name, payload)


class Compiler(APIView):
    def post(self, request: HttpRequest, *args, **kwargs):
        framework = request.POST.get("framework", None)

        if framework is None or framework == "":
            return HttpResponseBadRequest("No framework was specified")

        configuration_for_model = configuration_generator.get_configuration(framework, request)

        return executors.execute(framework, configuration_for_model)