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
from dmod.modeldata.hydrofabric import GeoPackageHydrofabric

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
        resolution = ''

    hyfab_data_dir = Path(PROJECT_ROOT, 'static', 'ngen', 'hydrofabric', name, resolution)

    geojson_file = hyfab_data_dir.joinpath(f"{type}_data.geojson")
    if geojson_file.exists():
        return geojson_file

    if hyfab_data_dir.joinpath("hydrofabric.gpkg").exists():
        geopackage_file = hyfab_data_dir.joinpath("hydrofabric.gpkg")
    elif hyfab_data_dir.joinpath(f"{name}.gpkg").exists():
        geopackage_file = hyfab_data_dir.joinpath(f"{name}.gpkg")
    else:
        logger.error(f"Can't build fabric path: can't find hydrofabric data file in directory {hyfab_data_dir!s}")
        return None

    return geopackage_file


class Fabrics(APIView):
    def get(self, request: HttpRequest, fabric: str = None) -> typing.Optional[JsonResponse]:
        if fabric is None:
            fabric = 'example_fabric_name'
        type = request.GET.get('fabric_type', 'catchment')
        if not type:
            type = "catchment"

        id_only = request.GET.get("id_only", "false")
        if isinstance(id_only, str):
            id_only = id_only.strip().lower() == "true"
        else:
            id_only = bool(id_only)

        path = _build_fabric_path(fabric, type)

        if path is None:
            return None
        elif path.name == f"{type}_data.geojson":
            with open(path) as fp:
                data = json.load(fp)
                if id_only:
                    return JsonResponse(sorted([feature["id"] for feature in data["features"]]), safe=False)
                else:
                    return JsonResponse(data)
        elif path.name[-5:] == ".gpkg":
            hf = GeoPackageHydrofabric.from_file(geopackage_file=path)
            if id_only:
                if type == "catchment":
                    return JsonResponse(sorted(hf.get_all_catchment_ids()), safe=False)
                elif type == "nexus":
                    return JsonResponse(sorted(hf.get_all_nexus_ids()), safe=False)
                else:
                    logger.error(f"Unsupported fabric type '{type}' for id_only geopackage in Fabrics API view")
                    return None
            else:
                if type == "catchment":
                    df = hf._dataframes[hf._DIVIDES_LAYER_NAME]
                elif type == "nexus":
                    df = hf._dataframes[hf._NEXUS_LAYER_NAME]
                else:
                    logger.error(f"Unsupported fabric type '{type}' for geopackage in Fabrics API view")
                    return None
                return JsonResponse(json.loads(df.to_json()))
        else:
            logger.error(f"Can't make API request for hydrofabric '{fabric!s}'")
            return None


class FabricNames(APIView):
    _fabrics_root_dir = Path(PROJECT_ROOT, 'static', 'ngen', 'hydrofabric')

    def get(self, request: HttpRequest) -> JsonResponse:
        names = []
        for fabric_subdir in self._fabrics_root_dir.iterdir():
            if fabric_subdir.is_dir():
                #Check for sub dirs/resolution
                sub = False
                for r_name in fabric_subdir.iterdir():
                    if r_name.is_dir():
                        names.append(f'{fabric_subdir.name} ({r_name.name})')
                        sub = True
                if not sub:
                    names.append(f'{fabric_subdir.name}')
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


class DomainView(View):

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
        return render(request, 'maas/domain.html', payload)