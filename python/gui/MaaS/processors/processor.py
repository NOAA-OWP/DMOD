#!/usr/bin/env python

from abc import ABC, abstractmethod
from typing import Union
from typing import List

from django.http import HttpRequest

from dmod.communication import ExternalRequest

from ..utilities import RequestWrapper


class BaseProcessor(object):
    def __init__(self, secret: str):
        self._errors: List[str] = list()
        self._warnings: List[str] = list()
        self._info: List[str] = list()
        self._maas_secret = secret

    @abstractmethod
    def process_request(self, request: Union[HttpRequest, RequestWrapper]) -> ExternalRequest:
        pass

    @property
    def errors(self) -> list:
        return self._errors

    @property
    def warnings(self) -> list:
        return self._warnings

    @property
    def info(self) -> list:
        return self._info
