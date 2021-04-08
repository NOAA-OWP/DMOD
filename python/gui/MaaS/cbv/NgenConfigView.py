"""
Defines a view that may be used to configure a MaaS request
"""

import os
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render

import dmod.communication as communication

import logging
logger = logging.getLogger("gui_log")

from pathlib import Path

from .DMODProxy import DMODMixin
from .utils import extract_log_data

class NgenConfigView(View, DMODMixin):

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

        if request.GET.get('feature_ids', ''):
            return self.ngen_config(request)

        # Return the rendered page
        return render(request, 'maas/edit.html', payload)

    def ngen_config(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
            Process ngen-config form
        """
        erros, warnings, info = extract_log_data(kwargs)

        catchments = request.POST.get('feature-ids', None)

        if catchments is not None:
            catchments = catchments.split("|")

        formulations = list()

        #Add formulations to list
        formulations.append("CFE")
        formulations.append("Simple_Lumped")

        payload = {
           'formulations': formulations,
           'catchments': catchments,
           'errors': errors,
           'info': info,
           'warnings': warnings
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

        if request.POST.get('feature-ids', ''):
            #render the configure view
            return self.ngen_config(request)
        else:
            """
            #Can do custom handling of the post/form here or push that back on the proxy...
            #TODO move the entire post method to the proxy mixin???
            client, session_data = self.forward_request(request)#PostFormJobRequestClient(endpoint_uri=self.maas_endpoint_uri, http_request=request)
            #logger.info("EditView.post: making job request")

            http_response = self.get(request=request, errors=client.errors, warnings=client.warnings,
                                     info=client.info, *args, **kwargs)

            # TODO: may need to handle here how to get data back from job, or may need that to be somewhere else
            # TODO: (we'll have the job_id as a cookie if a job started, so this should be doable)

            for k, v in session_data.items():
                http_response.set_cookie(k, v)

            return http_response
            """
            return HttpResponse("Not Yet Implemented.")
