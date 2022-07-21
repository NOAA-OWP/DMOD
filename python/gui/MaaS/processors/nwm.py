#!/usr/bin/env python

from typing import Union

from django.http import HttpRequest

from dmod.communication import ExternalRequest
from dmod.communication import get_request

from .processor import BaseProcessor

from .. import configuration as configuration_generator
from ..utilities import RequestWrapper

IS_PROCESSOR = True
FRIENDLY_NAME = "National Water Model Processor"


class Processor(BaseProcessor):
    def process_request(self, request: Union[HttpRequest, RequestWrapper]) -> ExternalRequest:
        # Ensure that the request is a request wrapper; this will ensure that both GET and POST are
        # honored correctly
        if not isinstance(request, RequestWrapper):
            request = RequestWrapper(request)

        return get_request(
            model=request.POST['model'],
            version=float(request.POST['version']),
            output=request.POST['output'],
            domain=request.POST['domain'],
            parameters=configuration_generator.get_configuration("nwm", request),
            session_secret=self._maas_secret
        )


def create_processor(secret: str = None) -> BaseProcessor:
    return Processor(secret)
