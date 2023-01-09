from abc import ABC

from ..message import Response
from .external_request import ExternalRequest


class ExternalRequestResponse(Response, ABC):

    response_to_type = ExternalRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
