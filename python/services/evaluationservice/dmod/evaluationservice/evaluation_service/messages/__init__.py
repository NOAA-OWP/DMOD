"""
Defines messages used to describe how to communicate with REST endpoints
"""
from __future__ import annotations

import typing

from pydantic import BaseModel
from pydantic import root_validator

from dmod.core.common import get_subclasses

from .base import BaseRequest
from .base import BaseResponse
from .base import ErrorResponse

from .definitions import DefinitionAction
from .definitions import SearchForDefinitionRequest
from .definitions import GetDefinitionRequest
from .definitions import SaveDefinitionRequest
from .definitions import ValidationMessage
from .definitions import ValidateDefinitionRequest

from .templates import TemplateAction
from .templates import GetTemplateSpecificationTypesRequest
from .templates import TemplateMetadata
from .templates import TemplateCollectionResponse
from .templates import SearchTemplatesRequest
from .templates import GetAllTemplatesRequest
from .templates import GetTemplateRequest
from .templates import SaveTemplateRequest
from .templates import GetTemplateByIDRequest


def _get_all_request_types() -> typing.Tuple[typing.Type[BaseRequest]]:
    return tuple([subclass for subclass in get_subclasses(BaseRequest)])


class MasterRequest(BaseModel):
    message: typing.Union[_get_all_request_types()]

    @root_validator
    def _ensure_action_is_defined(cls, values: dict) -> dict:
        action = values.get("action")

        if not action:
            raise ValueError(f"An action must be sent within the given message")

        if DefinitionAction.get(action) is None and TemplateAction.get(action) is None:
            raise ValueError(f"'{str(action)}' is not a valid action.")

        return values