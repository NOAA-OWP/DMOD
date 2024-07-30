"""
Defines a view that may be used to configure a MaaS request
"""

import re
import os
import typing
import importlib
from pprint import pprint
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic.base import View
from django.shortcuts import render
from django.conf import settings
from rest_framework.views import APIView
PROJECT_ROOT = settings.BASE_DIR
import json
from pathlib import Path
from .. import datapane
from .. import configuration

import logging
logger = logging.getLogger("gui_log")

_resolution_regex = re.compile("(.+) \((.+)\)")

def _build_fabric_path(fabric, type):
    """
        build a qualified path from the hydrofabric name and type
    """
    resolution_match = _resolution_regex.search(fabric)

    if resolution_match:
        name = resolution_match.group(1)
        resolution = resolution_match.group(2)
    else:
        name = fabric
        resolution=''

    path = Path(PROJECT_ROOT, 'static', 'ngen', 'hydrofabric', name, resolution, type+'_data.geojson')
    return path

class Fabrics(APIView):
    def get(self, request: HttpRequest, fabric: str = None) -> typing.Optional[JsonResponse]:
        if fabric is None:
            fabric = 'example'
        type = request.GET.get('fabric_type', 'catchment')
        if not type:
            type="catchment"

        path = _build_fabric_path(fabric, type)

        if path is None:
            return None

        with open(path) as fp:
            data = json.load(fp)
            return JsonResponse(data)

class FabricNames(APIView):
    _fabric_dir = Path(PROJECT_ROOT, 'static', 'ngen', 'hydrofabric')

    def get(self, request: HttpRequest) -> JsonResponse:
        names = []
        for f_name in self._fabric_dir.iterdir():
            if f_name.is_dir():
                #Check for sub dirs/resolution
                sub = False
                for r_name in f_name.iterdir():
                    if r_name.is_dir():
                        names.append( '{} ({})'.format(f_name.name, r_name.name))
                        sub = True
                if not sub:
                    names.append( '{}'.format(f_name.name) )
        return JsonResponse(data={
            "fabric_names": names
        })

class FabricTypes(APIView):
    def get(self, rquest: HttpRequest) -> JsonResponse:
        return JsonResponse( data={
            "fabric_types": ['catchment', 'flowpath', 'nexus']
            })

class ConnectedFeatures(APIView):
    def get(self, request: HttpRequest) -> JsonResponse:
        # TODO: Insert the logic for finding the connected locations
        location_id = request.GET['id']
        return JsonResponse(data={
            "location": location_id,
            "connected_locations": []
        })


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

        framework_selector = datapane.Input("framework", "select", "The framework within which to run models")
        for editor in configuration.get_editors():
            framework_selector.add_choice(editor['name'], editor['description'], editor['friendly_name'])

        pprint(framework_selector.__dict__)

        # Package everything up to be rendered for the client
        payload = {
            'errors': errors,
            'info': info,
            'warnings': warnings,
            'pane_inputs': [framework_selector]
        }

        # Return the rendered page
        return render(request, 'maas/map.html', payload)
