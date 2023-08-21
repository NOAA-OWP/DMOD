"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing
import abc

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator

from dmod.core.common import Status

class BaseResponse(BaseModel, abc.ABC):
    """
    Represents the response to a message
    """
    response_time: typing.Optional[datetime] = Field(
        default_factory=lambda _: datetime.now().astimezone(),
        description="When the response was formed"
    )

    errors: typing.Optional[typing.List[str]] = Field(
        default_factory=list,
        description="Any errors that were encountered"
    )

    status: typing.Optional[Status] = Field(
        default=Status.SUCCESS,
        description="Whether the original request encountered no errors"
    )

    status_code: typing.Optional[int] = Field(default=300, description="A matching HTTP code for the response")

    @root_validator
    def _assign_status_code(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        if "errors" in values and len(values['errors']) > 0 and not isinstance(values.get("status_code"), int):
            values['status_code'] = 500
        return values