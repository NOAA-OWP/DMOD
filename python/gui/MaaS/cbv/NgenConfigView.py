"""
Defines a view that may be used to configure a MaaS request
"""

import os
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render

import logging
logger = logging.getLogger("gui_log")

from pathlib import Path


class NgenConfigView(View):

    @property
    def maas_endpoint_uri(self):
        """ FIXME if enviorn isn't found, throws error.  Should maybe move to superclass/interface?
        if not hasattr(self, '_maas_endpoint_uri') or self._maas_endpoint_uri is None:
            self._maas_endpoint_uri = 'wss://' + os.environ.get('MAAS_ENDPOINT_HOST') + ':'
            self._maas_endpoint_uri += os.environ.get('MAAS_ENDPOINT_PORT')
        return self._maas_endpoint_uri
        """
        return

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

        if request.GET.get('cat-id', ''):
            return self.ngen_config(request)
        # If a list of error messages wasn't passed, create one
        if 'errors' not in kwargs:
            errors = list()
        else:
            # Otherwise continue to use the passed in list
            errors = kwargs['errors']  # type: list

        # If a list of warning messages wasn't passed create one
        if 'warnings' not in kwargs:
            warnings = list()
        else:
            # Otherwise continue to use the passed in list
            warnings = kwargs['warnings']  # type: list

        # If a list of basic messages wasn't passed, create one
        if 'info' not in kwargs:
            info = list()
        else:
            # Otherwise continue to us the passed in list
            info = kwargs['info']  # type: list

        # Define a function that will make words friendlier towards humans. Text like 'hydro_whatsit' will
        # become 'Hydro Whatsit'
        def humanize(words: str) -> str:
            split = words.split("_")
            return " ".join(split).title()

        models = list(get_available_models().keys())
        domains = ['example-domain-A', 'example-domain-B', 'croton_NY'] #FIXME map this from supported domains
        outputs = list()
        distribution_types = list()

        # Create a mapping between each output type and a friendly representation of it
        for output in get_available_outputs():
            output_definition = dict()
            output_definition['name'] = humanize(output)
            output_definition['value'] = output
            outputs.append(output_definition)

        # Create a mapping between each distribution type and a friendly representation of it
        for distribution_type in MaaSRequest.get_distribution_types():
            type_definition = dict()
            type_definition['name'] = humanize(distribution_type)
            type_definition['value'] = distribution_type
            distribution_types.append(type_definition)

        # Package everything up to be rendered for the client
        payload = {
            'models': models,
            'domains': domains,
            'outputs': outputs,
            'parameters': get_parameters(),
            'distribution_types': distribution_types,
            'errors': errors,
            'info': info,
            'warnings': warnings
        }

        # Return the rendered page
        return render(request, 'maas/edit.html', payload)

    def ngen_config(self, request: HttpRequest) -> HttpResponse:
        """
            Process ngen-config form
        """
        catchment = request.POST.get('cat-id')

        formulations = list()

        #Add formulations to list
        formulations.append("CFE")
        formulations.append("Simple_Lumped")

        payload = {
           'formulations': formulations,
           'catchment': catchment	          
        }

        return render(request, 'maas/ngen_edit.html', payload)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests. This will attempt to submit the request and rerender the page
        like a 'get' request

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """

        if request.POST.get('cat-id', ''):
            #render the configure view
            return self.ngen_config(request)
        else:
            return request
            request_client = PostFormJobRequestClient(endpoint_uri=self.maas_endpoint_uri, http_request=request)
            logger.info("EditView.post: making job request")
            response = request_client.make_job_request(maas_job_request=request_client._init_maas_job_request(),
                                                       force_new_session=False)

            http_response = self.get(request=request, errors=request_client.errors, warnings=request_client.warnings,
                                     info=request_client.info, *args, **kwargs)

            # TODO: may need to handle here how to get data back from job, or may need that to be somewhere else
            # TODO: (we'll have the job_id as a cookie if a job started, so this should be doable)

            # Set cookies if a new session was acquired
            if request_client.is_new_session:
                http_response.set_cookie('maas_session_id', request_client.session_id)
                http_response.set_cookie('maas_session_secret', request_client.session_secret)
                http_response.set_cookie('maas_session_created', request_client.session_created)
            # Set a cookie if a job was started and we have the id (rely on client to manage multiple job ids)
            if response is not None and 'job_id' in response.data:
                http_response.set_cookie('new_job_id', response.data['job_id'])
            return http_response
