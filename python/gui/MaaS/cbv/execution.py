from pprint import pprint
from django.http import HttpRequest, JsonResponse
from rest_framework.views import APIView

from .. import executors

import logging
LOGGER = logging.getLogger("gui_log")

class Execute(APIView):
    def post(self, request: HttpRequest, *args, **kwargs):
        pprint(request.POST)
        framework = request.POST.get("framework", None)

        if framework is None or framework == "":
            raise ValueError("No model type was passed into the configuration compiler")

        configuration_compiler = get_configuration_compiler(framework)

        if configuration_compiler is None:
            raise ValueError("'{}' is not a valid model type")

        configuration = configuration_compiler(request)

        return JsonResponse(configuration)
