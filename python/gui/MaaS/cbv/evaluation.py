from datetime import datetime
import os
import typing

from django.views.generic import View
from django.shortcuts import render

from django.http import HttpResponse
from django.http import HttpRequest

from dmod.core import common

from maas_experiment import application_values
import maas_experiment.forwarding as forwarding

from utilities import CodeViews
from utilities import Payload
from utilities import Notifier


EVALUATION_ID_PATTERN = r"[a-zA-Z0-9\.\-_]+"

EVALUATION_TEMPLATE_PATH = application_values.STATIC_RESOURCE_DIRECTORY / "evaluation_template.json"


class EvaluationListing(View):
    template = "maas/evaluation_listing.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "listing_url": os.path.join(forwarding.get_forward_rest_route("EvaluationService"), "details"),
            "table_name": "accessible-evaluations",
        }
        return render(request, template_name=self.template, context=context)


def _generate_evaluation_id() -> str:
    current_date = datetime.now()
    date_representation = current_date.strftime("%m-%d_%H.%M")
    evaluation_id = f"manual_evaluation_at_{date_representation}"
    return evaluation_id


def get_evaluation_template() -> str:
    with open(EVALUATION_TEMPLATE_PATH, "r") as evaluation_template_file:
        return evaluation_template_file.read()


class ReadyListenEvaluation(View):
    template = "maas/ready_evaluation.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        page_identifier = common.generate_identifier()
        page_key = common.generate_key()

        editors = CodeViews()

        editors.add(
            name="editor",
            tab="edit-div",
            container="editor-content",
            textarea="#instructions",
            config={
                "mode": "javascript",
                "lint": {
                    "esversion": 2022
                },
                "json": True,
                "allowDropFileTypes": ['application/json'],
            }
        )

        editors.add(
            name="messages",
            tab="message-div",
            container="message-area",
            textarea="#messages",
            config={
                "mode": "javascript",
                "json": True,
                "readOnly": True,
                "gutters": ["CodeMirror-foldgutter"]
            }
        )

        editors.add(
            name="digest",
            tab="digest-div",
            container="digest-area",
            textarea="#digest-text",
            config={
                "mode": "javascript",
                "json": True,
                "readOnly": True,
                "gutters": ["CodeMirror-foldgutter"]
            }
        )

        editors.add(
            name="template-preview",
            tab=None,
            container="template-preview",
            textarea="#template-preview-text",
            config={
                "mode": "javascript",
                "json": True,
                "readOnly": True,
                "gutters": ['CodeMirror-foldgutter']
            }
        )

        notifiers: typing.List[Notifier] = list()

        notifiers.append(
            Notifier("notifier-popup", "Notifications", "/ws/notifications")
        )

        context = {
            "evaluation_template": get_evaluation_template(),
            "launch_url": f'/{forwarding.get_forward_socket_route("EvaluationService")}',
            "metrics_url": f'/{forwarding.get_forward_rest_route("EvaluationService", "metrics")}',
            "geometry_url": f'/{forwarding.get_forward_rest_route("EvaluationService", "geometry")}',
            "generated_evaluation_id": _generate_evaluation_id(),
            "evaluation_id_pattern": EVALUATION_ID_PATTERN,
            "page_identifier": page_identifier,
            "page_key": page_key,
            "code_views": editors.to_json(),
            "notifiers": notifiers
        }

        payload = Payload(request, **context)

        page_response = render(request, template_name=self.template, context=payload.to_dict())
        page_response["page_identifier"] = page_identifier
        page_response['page_key'] = page_key

        return page_response
