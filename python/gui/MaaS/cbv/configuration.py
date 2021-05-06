"""
Defines a view that may be used to configure different model frameworks
"""
import logging

from django.http import HttpRequest
from django.http import HttpResponse

from django.views import View
from django.shortcuts import render

from .. import configuration as configuration_generator
from .. import utilities

logger = logging.getLogger("gui_log")


class CreateConfiguration(View):
    """
    A view that allows a user to configure a framework in order to utilize MaaS
    """

    @staticmethod
    def _create(request: utilities.RequestWrapper) -> HttpResponse:
        """
        Reads the passed request in order to render the desired configuration screen

        Parameters
        ----------
        request
            A wrapped HttpRequest; this ensures that inspecting GET or POST will yield the correct values

        Returns
        -------
        HttpResponse
            A rendered configuration screen
        """
        framework: str = request.POST.get('framework', None)

        # Error out if no framework is passed or the framework isn't supported
        if framework is None or framework.strip() == "":
            raise ValueError("A framework to configure was not supplied")
        elif framework.strip() not in configuration_generator.get_configuration_types():
            raise ValueError("'{}' is not a valid framework".format(framework.strip()))

        # Clean up the framework in order to avoid any possible issues due to whitespace
        framework = framework.strip()

        # Get the template name for the editor
        editor_name = configuration_generator.get_editor_name(framework)

        # Get all appropriate variables needed to render the editor
        payload = configuration_generator.get_editor_parameters(framework, request.POST)

        return render(request, editor_name, payload)

    def get(self, request: HttpRequest) -> HttpResponse:
        # Wrap the request for safe access to required parameters
        request = utilities.RequestWrapper(request)
        return self._create(request)

    def post(self, request: HttpRequest):
        # Wrap the request for safe access to required parameters
        request = utilities.RequestWrapper(request)
        return self._create(request)
