from abc import ABC

from ..message import AbstractInitRequest, Response
from .external_request import ExternalRequest

from typing import ClassVar, Type


class ExternalRequestResponse(Response, ABC):

    response_to_type: ClassVar[Type[AbstractInitRequest]] = ExternalRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""
