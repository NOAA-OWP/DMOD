#!/usr/bin/env python3
import typing
import os
import json
import re

from django.views.generic import View
from django.shortcuts import render
from django.shortcuts import reverse
from django.shortcuts import get_object_or_404

from django.http import HttpResponse
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.http import HttpResponseServerError

from rest_framework.views import APIView

from datetime import datetime

import geopandas

import utilities
from service import application_values
from evaluation_service import models
from evaluation_service import choices


EVALUATION_ID_PATTERN = r"[a-zA-Z0-9\.\-_]+"

EVALUATION_TEMPLATE_PATH = os.path.join(application_values.STATIC_RESOURCES_PATH, "evaluation_template.json")


BBOX_PATTERN = re.compile(r"(?<=(\[|\())? *-?\d+(\.\d*)? *, *-?\d+(\.\d*)? *, *-?\d+(\.\d*)? *, *-?\d+(\.\d*)? *(?=(\)|\]|))")
"""
Pattern matching for bounding boxes

This will match on strings like:

    - "(1.231 ,321.1213, -1231, 3.)"
    - "(1.231 ,321.1213, -1231, 3.]"
    - "[1.231 ,321.1213, -1231, 3.)"
    - "[1.231 ,321.1213, -1231, 3.]"
    - "(1.231 ,321.1213, -1231, 3."
    - "1.231 ,321.1213, -1231, 3."
"""


class GetGeometry(APIView):
    def _find_geometry(
        self,
        query: typing.Dict,
        dataset_id: int,
        geometry_name: str = None
    ) -> typing.Union[geopandas.GeoDataFrame, HttpResponse]:
        dataset = get_object_or_404(models.StoredDataset, pk=dataset_id)

        if not os.path.exists(dataset.path):
            return HttpResponseServerError(f"The data for {dataset.name} is not available")

        bounding_box = None
        if query.get("bbox") is not None:
            bounding_box_match = BBOX_PATTERN.search(query.get("bbox"))

            if bounding_box_match:
                bounding_box = [float(val.strip()) for val in bounding_box_match.group().split(",")]

        geometry = geopandas.read_file(filename=dataset.path, bbox=bounding_box)

        pertinent_columns = [
            column_name
            for column_name in geometry.keys()
            if column_name.lower() in ("name", "geometry")
               or column_name.lower().endswith("id")
        ]

        geometry = geometry[pertinent_columns]

        for query_key, query_value in query.items():
            if query_key == "geometry":
                continue

            if query_key in pertinent_columns:
                if query_value is None or query_value.lower().strip() in ("nan", "null", "na", "none"):
                    geometry = geometry[geometry[query_key].isnull()]
                elif pertinent_columns[query_key].dtype == int:
                    value = int(float(query_value))
                    geometry = geometry[geometry[query_key] == value]
                elif pertinent_columns[query_key].dtype == float:
                    value = float(query_value)
                    geometry = geometry[geometry[query_key] == value]
                else:
                    geometry = geometry[geometry[query_key] == query_value]

        if "id" in geometry:
            geometry.set_index("id", inplace=True)
        elif "name" in geometry:
            geometry.set_index("name", inplace=True)

        if geometry_name:
            geometry = geometry.filter(items=[geometry_name], axis=0)

        return geometry.copy()

    def get(self, request: HttpRequest, dataset_id: int, geometry_name: str = None) -> HttpResponse:
        data = self._find_geometry(request.GET, dataset_id, geometry_name)
        if isinstance(data, HttpResponse):
            return data

        return HttpResponse(data.to_json().encode(), headers={"Content-Type": "application/json"})

    def post(self, request: HttpRequest, dataset_id: int, geometry_name: str = None) -> HttpResponse:
        data = self._find_geometry(request.POST, dataset_id, geometry_name)
        if isinstance(data, HttpResponse):
            return data

        return HttpResponse(data.to_json().encode(), headers={"Content-Type": "application/json"})


class GetGeometryDatasets(APIView):
    @staticmethod
    def _load_geometry_names() -> typing.List[typing.Dict[str, typing.Union[str, int]]]:
        geometry_names: typing.List[typing.Dict[str, typing.Union[str, int]]] = list()

        for dataset in models.StoredDataset.objects.all():  # type: models.StoredDataset
            if dataset.dataset_type == choices.StoredDatasetType.geometry():
                geometry_names.append({
                    "value": dataset.pk,
                    "name": dataset.name
                })

        return geometry_names

    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(self._load_geometry_names(), safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse(self._load_geometry_names(), safe=False)
