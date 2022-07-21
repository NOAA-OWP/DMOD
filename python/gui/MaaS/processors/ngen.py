#!/usr/bin/env python

from typing import Union

from django.http import HttpRequest

from dmod.communication import ExternalRequest
from dmod.communication import get_request

from .processor import BaseProcessor

from .. import configuration as configuration_generator
from ..utilities import RequestWrapper

IS_PROCESSOR = True
FRIENDLY_NAME = "Next Generation Water Model Processor"


class Processor(BaseProcessor):
    def process_request(self, request: Union[HttpRequest, RequestWrapper]) -> ExternalRequest:
        configuration = configuration_generator.get_configuration('ngen', request)
        return get_request(model="ngen", parameters=configuration)


def create_processor(secret: str = None) -> BaseProcessor:
    return Processor(secret)
