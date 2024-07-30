"""
Defines a view that may be used to configure a MaaS request
"""

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
import re
from pathlib import Path
from .. import datapane
from .. import configuration

import logging
logger = logging.getLogger("gui_log")


_resolution_regex = re.compile("(.+) \((.+)\)")

def _build_fabric_path(fabric, type=""):
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

    logger.debug("fabric path:", fabric, name, resolution)
    path = Path(PROJECT_ROOT, 'static', 'ngen', 'hydrofabric', name, resolution, type+'crosswalk.json')
    if (path == None):
        return JsonResponse({})
    return path


class Crosswalk(APIView):
    def get(self, request: HttpRequest, crosswalk: str = None) -> typing.Optional[JsonResponse]:
        logger.debug("crosswalk path:", crosswalk)
        if crosswalk is None:
            return JsonResponse({})

        logger.debug("crosswalk path:", crosswalk)
        path = _build_fabric_path(crosswalk)

        if path is None:
            return None

        try:
            with open(path) as fp:
                data = json.load(fp)
                return JsonResponse(data)
        except:
            return JsonResponse({})
