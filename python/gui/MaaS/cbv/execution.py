"""
Defines a view that may be used to execute models on different frameworks
"""

import json
import logging

from typing import Dict
from typing import Tuple

from django.conf import settings

from django.http import HttpRequest
from django.http import JsonResponse

from rest_framework.views import APIView

from dmod.communication import ExternalRequestResponse

from .. import processors
from ..client import JobRequestClient

LOGGER = logging.getLogger("gui_log")


# A cache for JobRequestClients; key is (Framework, Address of endpoint)
CLIENTS: Dict[Tuple[str, str], JobRequestClient] = dict()


def get_client(framework: str, endpoint_uri: str = None) -> JobRequestClient:
    """
    Either get a preexisting JobRequestClient from the cache or create and add one.

    The key for the cache is (framework, endpoint_uri)

    Parameters
    ----------
    framework : str
        The name of the modelling framework to use
    endpoint_uri : str
        The optional endpoint to attempt to communicate with. The configured endpoint for the server will be used if
        one isn't specified

    Returns
    -------
    JobRequestClient
        A client through which jobs may be issued
    """
    if framework in CLIENTS:
        client = CLIENTS[(framework, endpoint_uri)]
    else:
        processor = processors.get_processor(framework)

        client = JobRequestClient(
            processor=processor,
            endpoint_uri=settings.GET_MAAS_ENDPOINT(framework) if endpoint_uri is None else endpoint_uri
        )
        CLIENTS[(framework, endpoint_uri)] = client

    return client


class Execute(APIView):
    """
    API view for executing a configured model on a specified framework
    """
    def post(self, request: HttpRequest):
        """
        The post handler

        Gets a client, forms a request based on it, issues said request, and returns metadata for said job

        Parameters
        ----------
        request
            The HttpRequest that called the API

        Returns
        -------
        JsonResponse
            JSON describing the state of the job that is run
        """
        # Output debugging information for development and diagnostics
        LOGGER.debug("Request for model run:")
        LOGGER.debug(json.dumps(request.POST, indent=4))

        # Get the appropriate framework that the configuration will be run on
        framework = request.POST.get("framework", None)

        # Nothing can be done if a framework isn't found, so go ahead and thrown an error
        if framework is None or framework == "":
            raise ValueError("No model type was passed into the configuration compiler")
        elif framework not in processors.get_processor_types():
            # Throw an error if there isn't a valid processor for the framework
            raise ValueError("'{}' is not a valid model framework".format(framework))

        # Grab the client that the model run will be routed through
        client = get_client(framework, request.POST.get("endpoint_uri", None))

        # Allow the caller to determine whether or not a new session should be created
        force_new_session = request.POST.get("force_new_session", False)

        # Issue the request
        response: ExternalRequestResponse = client.make_maas_request(request, force_new_session)

        # Throw an error if the request could not be successfully issued
        if response is None:
            raise Exception("A request could not be issued.")

        # Get the data from the response and wrap it in a response object that is easy for humans and applications to
        # parse
        http_response = JsonResponse(data=response.to_dict())

        # Set a cookie if a job was started and we have the id (rely on client to manage multiple job ids)
        if response is not None and 'job_id' in response.data:
            http_response.set_cookie('new_job_id', response.data['job_id'])

        # Set cookies if a new session was acquired
        if client.is_new_session:
            http_response.set_cookie('maas_session_id', client.session_id)
            http_response.set_cookie('maas_session_secret', client.session_secret)
            http_response.set_cookie('maas_session_created', client.session_created)

        return http_response
