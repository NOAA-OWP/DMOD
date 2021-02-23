"""
Defines a view that may be used to configure a MaaS request
"""

import os
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.shortcuts import render
from django.conf import settings
PROJECT_ROOT = settings.BASE_DIR
import json
from pathlib import Path

import logging
logger = logging.getLogger("gui_log")


class MapView(View):

    """
    A view used to render the map
    """
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'get' requests.  This will render the 'map.html' template

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """
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

        catchment_data_file = Path(PROJECT_ROOT)/'static'/'ngen'/'catchment_data.geojson'
        with open(catchment_data_file) as fp:
            catchments = json.load(fp)
        # Package everything up to be rendered for the client
        payload = {
            'errors': errors,
            'info': info,
            'warnings': warnings,
            'catchments': json.dumps(catchments)
        }

        # Return the rendered page
        return render(request, 'maas/map.html', payload)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The handler for 'post' requests. This will attempt to submit the request and rerender the page
        like a 'get' request

        :param HttpRequest request: The request asking to render this page
        :param args: An ordered list of arguments
        :param kwargs: A dictionary of named arguments
        :return: A rendered page
        """

        return None
