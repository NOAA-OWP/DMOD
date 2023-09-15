"""
Base Classes for how request and response messages should be formed
"""
from __future__ import annotations

import typing
import inspect
import abc
import uuid

from http import HTTPStatus

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator
from pydantic import validator

from dmod.core.common import Status
from dmod.core.enum import PydanticEnum


class RequestTrackingMixin:
    request_id: typing.Optional[str] = Field(
        default_factory=uuid.uuid1,
        description="An optional ID used to track the request"
    )


class SessionTrackingMixin:
    session_id: typing.Union[str, int, None] = Field(
        default=None,
        description="An optional ID used to track session information"
    )


class TokenMixin:
    token: typing.Union[str, bytes, None] = Field(
        default=None,
        description="An optional token used to identify a caller's ability to interact with the server"
    )


class BaseResponse(BaseModel, abc.ABC):
    """
    Represents the response to a message
    """
    response_to: str = Field(description="The action that this is a response to")

    response_time: typing.Optional[datetime] = Field(
        default_factory=lambda: datetime.now().astimezone(),
        description="When the response was formed"
    )

    errors: typing.Optional[typing.Union[str, typing.List[str]]] = Field(
        default_factory=list,
        description="Any errors that were encountered"
    )

    result: typing.Optional[Status] = Field(
        default=Status.SUCCESS,
        description="Whether the original request encountered no errors"
    )

    # The default response status code is '201' to help ensure that GET requests
    # won't be stored when new data might be provided
    status_code: typing.Union[int, None] = Field(
        default=HTTPStatus.CREATED,
        description="A matching HTTP code for the response"
    )

    @validator("errors", always=True)
    def _list_errors(cls, value: typing.Union[str, typing.List[str]]) -> typing.List[str]:
        if not isinstance(value, typing.Sequence):
            if value:
                value = [value]
            else:
                value = list()

        return value

    @validator("result", always=True)
    def _set_result(cls, value: typing.Union[str, int, Status, None]) -> Status:
        """
        Ensure that the value passed as a status is an actual status object
        """
        if value is None:
            value = Status.UNKNOWN
        elif isinstance(value, (int, HTTPStatus)) and HTTPStatus.OK <= value < HTTPStatus.BAD_REQUEST:
            value = Status.SUCCESS
        elif isinstance(value, (int, HTTPStatus)) and value >= HTTPStatus.BAD_REQUEST:
            value = Status.ERROR
        else:
            value = Status.get(value)

        return value

    @root_validator
    def _assign_status_code(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Ensure that a status code lies on the object if one wasn't passed

        Args:
            values: The data that will be used to instantiate this response

        Returns:
            The updated data used to construct this response
        """
        has_status_code = isinstance(values.get("status_code"), int)
        has_status = values.get("result", Status.UNKNOWN) is not Status.UNKNOWN

        if values['errors'] and not isinstance(values['errors'], typing.Sequence):
            values['errors'] = [values['errors']]

        if has_status_code and not has_status:
            if values.get("status_code", HTTPStatus.OK) >= HTTPStatus.BAD_REQUEST:
                values['result'] = Status.ERROR
            else:
                values['result'] = Status.SUCCESS
        elif "errors" in values and len(values['errors']) > 0 and not has_status_code:
            values['status_code'] = HTTPStatus.BAD_REQUEST
        elif not has_status_code:
            values['status_code'] = HTTPStatus.OK

        if values.get("errors") and values.get("result", Status.UNKNOWN) < Status.ERROR:
            values['result'] = Status.ERROR

        if values.get("result", Status.UNKNOWN) is Status.UNKNOWN:
            values['result'] = Status.SUCCESS if values.get("status_code") < HTTPStatus.BAD_REQUEST else Status.ERROR
        return values


class ErrorResponse(BaseResponse):
    """
    A message response that represents an error that occurred
    """
    @validator("result", always=True)
    def _ensure_error_status(cls, value: typing.Union[str, int, Status, None]) -> Status:
        if value is None:
            value = Status.ERROR
        else:
            value = Status.get(value)

        if value < Status.ERROR:
            raise ValueError(
                f"Error messages can only have a status of '{Status.ERROR}' - received '{str(value)}' instead."
            )

        return value

    @validator("status_code", always=True)
    def _ensure_error_status_code(cls, value: int) -> int:
        if value is None:
            value = HTTPStatus.INTERNAL_SERVER_ERROR
        elif value < HTTPStatus.BAD_REQUEST or value > max(HTTPStatus):
            raise ValueError(f"'{value}' is not a valid error status code")
        return value


RESPONSE_TYPE = typing.TypeVar("RESPONSE_TYPE", bound=BaseResponse, covariant=True)
ACTION = typing.TypeVar("ACTION", bound=PydanticEnum, covariant=True)


class BaseRequest(BaseModel, abc.ABC, typing.Generic[RESPONSE_TYPE, ACTION]):
    """
    Represents a request for a REST endpoint
    """
    class Config:
        extra = 'allow'

    action: ACTION

    @classmethod
    @abc.abstractmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        """
        Get the class type that is appropriate for a response
        """
        ...

    def make_response(self, **kwargs) -> RESPONSE_TYPE:
        """
        Create a response to this message
        """
        if "response_to" not in kwargs:
            kwargs['response_to'] = self.action

        return self.__class__.get_response_type()(**kwargs)

    def make_error(
        self,
        message: str,
        status: typing.Optional[Status] = None,
        status_code: typing.Optional[int] = None,
        **kwargs
    ) -> ErrorResponse:
        if status is None:
            status = Status.ERROR

        if status_code is None:
            status_code = HTTPStatus.INTERNAL_SERVER_ERROR

        if not message:
            raise ValueError(f"An error message is required in order to create an error response")

        if status < Status.ERROR:
            raise ValueError(f"Errors cannot have a status less than '{Status.ERROR}' - received '{status}'")

        if status_code < HTTPStatus.BAD_REQUEST or status_code >= max(HTTPStatus):
            raise ValueError(f"Error status codes range from [400, {max(HTTPStatus)}] - received '{status_code}'")

        if "response_to" not in kwargs:
            kwargs['response_to'] = self.action

        errors = kwargs.get("errors")

        if isinstance(errors, str):
            kwargs['errors'] = [errors, message]
        elif isinstance(errors, typing.Sequence):
            kwargs['errors'] = [existing_message for existing_message in kwargs['errors']] + [message]
        elif errors:
            kwargs['errors'] = [errors, message]
        else:
            kwargs['errors'] = [message]

        return ErrorResponse(result=status, status_code=status_code, **kwargs)