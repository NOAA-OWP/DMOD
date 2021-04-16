import os
import json
import re
from pprint import pprint
from django.http import HttpRequest, HttpResponse, JsonResponse
from rest_framework.views import APIView
from django.shortcuts import render

import dmod.communication as communication
from .. import models

import logging
logger = logging.getLogger("gui_log")


def isolate_parameters(feature_key: str, total_parameters: dict, declared_formulations: dict, start_date: str, end_date: str) -> dict:
    isolated_parameters = {
        feature_key: {}
    }

    parameters = {
        key.replace(feature_key + "-", ""): value
        for key, value in total_parameters.items()
        if key.startswith(feature_key)
    }

    formulation_type_keys = [key for key in parameters.keys() if key.endswith("formulation-type")]

    if len(formulation_type_keys) == 0:
        raise ValueError("No formulation type was passed for {}".format(feature_key))

    type_key = formulation_type_keys[0]
    passed_formulation_type = parameters[type_key]

    if passed_formulation_type == "global":
        return {
            feature_key: {}
        }

    isolated_parameters[feature_key]['forcing'] = {
        "start_date": start_date,
        "end_date": end_date
    }

    forcing_paths = [value for key, value in parameters.items() if key == "forcing-path"]
    forcing_patterns = [value for key, value in parameters.items() if key == "forcing-pattern"]

    if len(forcing_paths) == 1 and forcing_paths[0] not in [""]:
        isolated_parameters[feature_key]['forcing']["path"] = forcing_paths[0]

        if len(forcing_patterns) == 1 and forcing_patterns[0] not in ["", "*"]:
            isolated_parameters[feature_key]['forcing']['file_pattern'] = forcing_patterns[0]

    clean_formulation_type = declared_formulations[passed_formulation_type]

    parameters = {
        key.replace(clean_formulation_type + "-", ""): value
        for key, value in parameters.items()
        if key.startswith(clean_formulation_type)
    }

    formulation = models.Formulation.objects.filter(pk=int(passed_formulation_type)).first()

    # Now separate out parameter groups
    grouped_parameters = dict()

    for field_name, field_value in parameters.items():
        possible_parameter = formulation.formulationparameter_set.filter(name=field_name)

        if possible_parameter.exists():
            parameter: models.FormulationParameter = possible_parameter

            if parameter.group is None or parameter.group == "":
                approved_value = field_value

                if parameter.is_list and parameter.value_type == "number":
                    approved_value = [float(value) for value in field_value.split(",")]
                elif parameter.value_type == "number":
                    approved_value = float(field_value)
                elif parameter.is_list:
                    approved_value = field_value.split(",")

                grouped_parameters[field_name] = approved_value
            else:
                if parameter.group not in grouped_parameters:
                    grouped_parameters[parameter.group] = dict()

                approved_value = field_value

                if parameter.is_list and parameter.value_type == "number":
                    approved_value = [float(value) for value in field_value.split(",")]
                elif parameter.value_type == "number":
                    approved_value = float(field_value)
                elif parameter.is_list:
                    approved_value = field_value.split(",")

                grouped_parameters[parameter.group][field_name] = approved_value

    isolated_parameters[feature_key][formulation.name] = grouped_parameters

    return isolated_parameters


def collect_form_configuration(request: HttpRequest) -> dict:
    collected_configuration = dict()

    feature_pattern = request.POST['features']
    if len(feature_pattern) > 0:
        feature_pattern += "|"
    feature_pattern += "global"
    parameters = {key: value for key, value in request.POST.items() if re.match(feature_pattern, key)}
    features = request.POST['features'].split("|")
    start_date = request.POST['start-time']
    end_date = request.POST['end-time']
    declared_formulations = json.loads(request.POST['formulations'])
    print("Now processing form configuration")

    global_configuration = isolate_parameters("global", parameters, declared_formulations, start_date, end_date)
    collected_configuration.update(global_configuration)

    for feature in features:
        if "catchments" not in collected_configuration:
            collected_configuration["catchments"] = dict()

        single_configuration = isolate_parameters(feature, parameters, declared_formulations)
        collected_configuration["catchments"].update(single_configuration)

    return collected_configuration


class CompileNGenConfiguration(APIView):
    def post(self, request: HttpRequest, *args, **kwargs):
        pprint(request.POST)
        configuration = collect_form_configuration(request)
        print("Form configuration gathered")
        return JsonResponse(configuration)