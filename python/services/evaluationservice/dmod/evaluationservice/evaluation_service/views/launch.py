#!/usr/bin/env python3
import typing
import os
import json
import re

from django.views.generic import View
from django.shortcuts import render
from django.shortcuts import reverse

from django.http import HttpResponse
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.http import JsonResponse

from rest_framework.views import APIView

from datetime import datetime

import utilities


EVALUATION_ID_PATTERN = r"[a-zA-Z0-9\.\-_]+"
START_DELAY = os.environ.get('EVALUATION_START_DELAY', '5')
OUTPUT_VERBOSITY = os.environ.get("EVALUATION_OUTPUT_VERBOSITY", "ALL")


class LaunchEvaluation(APIView):
    def post(self, request, *args, **kwargs):
        evaluation_id = request.POST.get("evaluation_id")
        evaluation_id = evaluation_id.replace(" ", "_").replace(":", ".")
        instructions = request.POST.get("instructions")

        if 'HTTP_REFERER' in request.META:
            response_url = reverse("evaluation_service:Listen", kwargs={"channel_name": evaluation_id})
            response = HttpResponseRedirect(response_url)
        else:
            channel_key = utilities.get_channel_key(evaluation_id)
            data = {
                "channel_name": evaluation_id,
                "channel_key": channel_key,
                "channel_route": f"ws://{request.META['HTTP_HOST']}/evaluation_service/ws/channel/{channel_key}"
            }
            response = JsonResponse(data, json_dumps_params={"indent": 4})

        """
        worker_arguments = worker.Arguments(
            "-t",
            "--verbosity",
            OUTPUT_VERBOSITY,
            '-d',
            START_DELAY,
            '-n',
            evaluation_id,
            instructions
        )
        """

        launch_parameters = {
            "purpose": "launch",
            "evaluation_id": evaluation_id,
            "verbosity": OUTPUT_VERBOSITY,
            "start_delay": START_DELAY,
            "instructions": instructions
        }
        connection = utilities.get_redis_connection()
        connection.publish("evaluation_jobs", json.dumps(launch_parameters))
        """
        django_rq.get_queue(application_values.EVALUATION_QUEUE_NAME).enqueue(
            worker.evaluate,
            evaluation_id,
            instructions,
            worker_arguments
        )
        """
        return response


class ReadyEvaluation(View):
    template = "evaluation_service/ready_evaluation.html"

    def get_evaluation_template(self) -> str:
        template = {
            "observations": [
                {
                    "name": "Observations",
                    "value_field": "observation",
                    "value_selectors": [
                        {
                            "name": "observation",
                            "where": "value",
                            "path": ["values[*]", "value[*]", "value"],
                            "datatype": "float",
                            "origin": ["$", "value", "timeSeries[*]"],
                            "associated_fields": [
                                {
                                    "name":"value_date",
                                    "path": ["values[*]", "value[*]", "dateTime"],
                                    "datatype": "datetime"
                                },
                                {
                                    "name":"observation_location",
                                    "path": ["sourceInfo", "siteCode", "[0]", "value"],
                                    "datatype": "string"
                                },
                                {
                                    "name":"unit",
                                    "path": ["variable", "unit", "unitCode"],
                                    "datatype": "string"
                                }
                            ]
                        }
                    ],
                    "backend": {
                        "backend_type": "file",
                        "data_format": "json",
                        "address": "path/to/observations.json"
                    },
                    "locations": {
                        "identify": True,
                        "from_field": "value"
                    },
                    "unit": {
                        "field": "unit"
                    },
                    "x_axis": "value_date"
                }
            ],
            "predictions": [
                {
                    "name": "Predictions",
                    "value_field": "prediction",
                    "value_selectors": [
                        {
                            "name": "predicted",
                            "where": "column",
                            "associated_fields": [
                                {
                                    "name": "date",
                                    "datatype": "datetime"
                                }
                            ]
                        }
                    ],
                    "backend": {
                        "backend_type": "file",
                        "data_format": "csv",
                        "address": "path/to/cat.*cfs.csv",
                        "parse_dates": ["date"]
                    },
                    "locations": {
                        "identify": True,
                        "from_field": "filename",
                        "pattern": "cat-\\d\\d"
                    },
                    "field_mapping": [
                        {
                            "field": "prediction",
                            "map_type": "column",
                            "value": "predicted"
                        },
                        {
                            "field": "prediction_location",
                            "map_type": "column",
                            "value": "location"
                        },
                        {
                            "field": "value_date",
                            "map_type": "column",
                            "value": "date"
                        }
                    ],
                    "unit": {
                        "value": "ft^3/s"
                    },
                    "x_axis": "value_date"
                }
            ],
            "crosswalks": [
                {
                    "backend": {
                        "backend_type": "file",
                        "address": "path/to/crosswalk.json",
                        "data_format": "json"
                    },
                    "observation_field_name": "observation_location",
                    "prediction_field_name": "prediction_location",
                    "field": {
                        "name": "prediction_location",
                        "where": "key",
                        "path": ["* where site_no"],
                        "origin": "$",
                        "datatype": "string",
                        "associated_fields": [
                            {
                                "name": "observation_location",
                                "path": "site_no",
                                "datatype": "string"
                            }
                        ]
                    }
                }
            ],
            "thresholds": [
                {
                    "backend": {
                        "backend_type": "file",
                        "data_format": "rdb",
                        "address": "path/to/stat_thresholds.rdb"
                    },
                    "locations": {
                        "identify": True,
                        "from_field": "column",
                        "pattern": "site_no"
                    },
                    "application_rules": {
                        "threshold_field": {
                            "name": "threshold_day",
                            "path": [
                                "month_nu",
                                "day_nu"
                            ],
                            "datatype": "Day"
                        },
                        "observation_field": {
                            "name": "threshold_day",
                            "path": [
                                "value_date"
                            ],
                            "datatype": "Day"
                        }
                    },
                    "definitions": [
                        {
                            "name": "75th Percentile",
                            "field": "p75_va",
                            "weight": 10,
                            "unit": {
                                "value": "ft^3/s"
                            }
                        }
                    ]
                },
                {
                    "backend": {
                        "backend_type": "file",
                        "data_format": "json",
                        "address": "path/to/thresholds.json"
                    },
                    "locations": {
                        "identify": True,
                        "from_field": "value",
                        "pattern": "metadata/usgs_site_code"
                    },
                    "origin": "$.value_set[?(@.calc_flow_values.rating_curve.id_type == 'NWS Station')]",
                    "definitions": [
                        {
                            "name": "Action",
                            "field": "calc_flow_values/action",
                            "weight": 3,
                            "unit": {
                                "path": "metadata/calc_flow_units"
                            }
                        },
                        {
                            "name": "Flood",
                            "field": "calc_flow_values/flood",
                            "weight": 2,
                            "unit": {
                                "path": "metadata/calc_flow_units"
                            }
                        }
                    ]
                }
            ],
            "scheme": {
                "metrics": [
                    {
                        "name": "False Alarm Ratio",
                        "weight": 10
                    },
                    {
                        "name": "Probability of Detection",
                        "weight": 10
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "weight": 15
                    },
                    {
                        "name": "Normalized Nash-Sutcliffe Efficiency",
                        "weight": 15
                    },
                    {
                        "name": "Pearson Correlation Coefficient",
                        "weight": 18
                    }
                ]
            }
        }
        return json.dumps(template, indent=4)

    def _generate_evaluation_id(self, request: HttpRequest) -> str:
        current_date = datetime.now()
        date_representation = current_date.strftime("%m-%d_%H.%M")
        evaluation_id = f"manual_evaluation_at_{date_representation}"
        return evaluation_id

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "evaluation_template": self.get_evaluation_template(),
            "launch_url": "/evaluation_service/launch",
            "generated_evaluation_id": self._generate_evaluation_id(request),
            "evaluation_id_pattern": EVALUATION_ID_PATTERN
        }
        return render(request, template_name=self.template, context=context)

