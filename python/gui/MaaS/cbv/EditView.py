"""
Defines a view that may be used to configure a MaaS request
"""

from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render

import logging
logger = logging.getLogger("gui_log")

import dmod.communication as communication
from dmod.communication import maas_request
from pathlib import Path

from .DMODProxy import DMODMixin
from .utils import extract_log_data

class EditView(View, DMODMixin):

    """
    A view used to configure a MaaS request
    """
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'get' requests.  This will render the 'edit.html' template with all models, all
        possible model outputs, the parameters that are configurable on each model, distribution types
        that may be used on each, and any sort of necessary messages

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """
        errors, warnings, info = extract_log_data(kwargs)

        # Define a function that will make words friendlier towards humans. Text like 'hydro_whatsit' will
        # become 'Hydro Whatsit'
        def humanize(words: str) -> str:
            split = words.split("_")
            return " ".join(split).title()

        models = list(communication.get_available_models().keys())
        domains = ['example-domain-A', 'example-domain-B'] #FIXME map this from supported domains
        #outputs = list()
        #distribution_types = list()

        ### Note that these are now broken, and also probably no longer applicable
        #
        # # Create a mapping between each output type and a friendly representation of it
        # for output in maas_request.get_available_outputs():
        #     output_definition = dict()
        #     output_definition['name'] = humanize(output)
        #     output_definition['value'] = output
        #     outputs.append(output_definition)
        #
        # # Create a mapping between each distribution type and a friendly representation of it
        # for distribution_type in maas_request.get_distribution_types():
        #     type_definition = dict()
        #     type_definition['name'] = humanize(distribution_type)
        #     type_definition['value'] = distribution_type
        #     distribution_types.append(type_definition)

        # Package everything up to be rendered for the client
        payload = {
            'models': models,
            'domains': domains,
            #'outputs': outputs,
            #'parameters': maas_request.get_parameters(),
            #'distribution_types': distribution_types,
            'errors': errors,
            'info': info,
            'warnings': warnings
        }

        # Return the rendered page
        return render(request, 'maas/edit.html', payload)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests. This will attempt to submit the request and rerender the page
        like a 'get' request.

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """
        #TODO move the entire post method to the proxy mixin???
        client, session_data, maas_response = self.forward_request(request, communication.MessageEventType.MODEL_EXEC_REQUEST)
        #logger.info("EditView.post: making job request")

        # TODO: putting this here for now (moving after changing forward_request function) but may not need it
        # Set data if a job was started and we have the id (rely on client to manage multiple job ids)
        # TODO might be worth using DJango session to save this to (can serialize a json list of ids?)
        # Might also be worth saving to a "user" database table with "active jobs"?
        if maas_response is not None and 'job_id' in maas_response.data:
            session_data['new_job_id'] = maas_response.data['job_id']

        http_response = self.get(request=request, errors=client.errors, warnings=client.warnings,
                                 info=client.info, *args, **kwargs)

        # TODO: may need to handle here how to get data back from job, or may need that to be somewhere else
        # TODO: (we'll have the job_id as a cookie if a job started, so this should be doable)

        for k, v in session_data.items():
            http_response.set_cookie(k, v)

        return http_response
