import os

from datetime import datetime

from django.views.generic import View
from django.shortcuts import render

from django.http import HttpResponse
from django.http import HttpRequest

from service import application_values


EVALUATION_ID_PATTERN = r"[a-zA-Z0-9\.\-_]+"

EVALUATION_TEMPLATE_PATH = os.path.join(application_values.STATIC_RESOURCES_PATH, "evaluation_template.json")


class ReadyListenEvaluation(View):
    template = "maas/ready_evaluation.html"

    def get_evaluation_template(self) -> str:
        with open(EVALUATION_TEMPLATE_PATH, "r") as evaluation_template_file:
            return evaluation_template_file.read()

    def _generate_evaluation_id(self, request: HttpRequest) -> str:
        current_date = datetime.now()
        date_representation = current_date.strftime("%m-%d_%H.%M")
        evaluation_id = f"manual_evaluation_at_{date_representation}"
        return evaluation_id

    def get(self, request: HttpRequest) -> HttpResponse:
        context = {
            "evaluation_template": self.get_evaluation_template(),
            "launch_url": "/ws/launch",
            "generated_evaluation_id": self._generate_evaluation_id(request),
            "evaluation_id_pattern": EVALUATION_ID_PATTERN
        }
        return render(request, template_name=self.template, context=context)
