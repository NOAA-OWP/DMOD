from pprint import pprint
from django.http import HttpRequest
from rest_framework.views import APIView

from .. import executors
from .. import configuration as configuration_generator

import logging
LOGGER = logging.getLogger("gui_log")


class Execute(APIView):
    def post(self, request: HttpRequest, *args, **kwargs):
        pprint(request.POST)
        framework = request.POST.get("framework", None)

        if framework is None or framework == "":
            raise ValueError("No model type was passed into the configuration compiler")

        configuration = configuration_generator.get_configuration(framework, request)

        return executors.execute(framework, configuration)
