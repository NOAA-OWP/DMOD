"""
Define messages used to communicate with definition endpoints
"""
from __future__ import annotations

import json
import typing

from dmod.core.common import CommonEnum
from pydantic import BaseModel
from pydantic import validator
from pydantic import Field
from pydantic import root_validator

from dmod.core.common import Status

from .base import BaseRequest
from .base import BaseResponse
from .base import RESPONSE_TYPE


class DefinitionAction(str, CommonEnum):
    SEARCH = "SEARCH_FOR_DEFINITION"
    GET_DEFINITION = "GET_DEFINITION"
    SAVE_DEFINITION = "SAVE_DEFINITION"
    VALIDATE = "VALIDATE_DEFINITION"

    @classmethod
    def default(cls):
        raise ValueError(f"Cannot form a default {cls.__name__}; There is no default action")


class DefinitionMetadata(BaseModel):
    """
    Metadata defining information like an evaluation specifications ID and its author
    """
    author: str
    title: str
    description: str
    definition_id: typing.Optional[int] = Field(default=None)


class SearchForDefinitionRequest(BaseRequest):
    """
    A message that asks for metadata for all definitions that have the indicated author and/or title
    """
    action: typing.Optional[typing.Literal[DefinitionAction.SEARCH]] = Field(default=DefinitionAction.SEARCH)
    author: typing.Optional[str] = Field(
        default=None,
        description="The name of the author of the definitions to look for"
    )
    title: typing.Optional[str] = Field(
        default=None,
        description="A pattern that might match on evaluations to look for"
    )

    class Response(BaseResponse):
        """
        A response bearing metadata for all found definitions
        """
        definitions: typing.Optional[typing.List[DefinitionMetadata]] = Field(default_factory=list)

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response


class GetDefinitionRequest(BaseRequest):
    """
    A message that returns a full evaluation specification based on the given ID
    """
    definition_id: int = Field(description="The ID of the stored definition")
    action: typing.Optional[typing.Literal[DefinitionAction.GET_DEFINITION]] = Field(default=DefinitionAction.GET_DEFINITION)

    class Response(BaseResponse, DefinitionMetadata):
        """
        A response containing the definition that matches the
        """
        definition: str

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response


class SaveDefinitionRequest(BaseRequest, DefinitionMetadata):
    action: typing.Optional[typing.Literal[DefinitionAction.SAVE_DEFINITION]] = Field(default=DefinitionAction.SAVE_DEFINITION)
    definition: str = Field(description="The evaluation definition to store")

    class Response(BaseResponse, DefinitionMetadata):
        created: bool

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response


class ValidationMessage(BaseModel):
    message: str
    level: Status

    @validator("level")
    def _transform_level(cls, value: typing.Union[Status, str, int]) -> Status:
        return Status.get(value)

    def __eq__(self, other: ValidationMessage):
        return self.message == other.message and self.level == other.level


class ValidateDefinitionRequest(BaseRequest):
    action: typing.Optional[typing.Literal[DefinitionAction.VALIDATE]] = Field(default=DefinitionAction.VALIDATE)
    definition: typing.Union[str, typing.Dict[str, typing.Any]]

    @validator("definition")
    def _ensure_definition_is_dict(
        cls,
        value: typing.Union[str, typing.Dict[str, typing.Any]]
    ) -> typing.Dict[str, typing.Any]:
        if isinstance(value, str):
            value = json.loads(value)

        return value

    class Response(BaseResponse):
        messages: typing.Optional[typing.List[ValidationMessage]] = Field(
            default_factory=list,
            description="Any messages generated during the validation process"
        )

        def add_message(self, message: str, level: typing.Union[Status, int, str]):
            level = Status.get(level)
            validation = ValidationMessage(message=message, level=level)

            if validation in self.messages:
                return

            self.messages.append(ValidationMessage(message=message, level=level))

            if level == Status.ERROR:
                self.errors.append(message)

            if level > self.result:
                self.result = level

        @root_validator
        def _interpret_success(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
            received_messages: typing.List[ValidationMessage] = values.get("messages", list())
            current_status: Status = values.get("result") or cls.__fields__.get("result").default or Status.default()

            error_messages = [message for message in received_messages if message.level == Status.ERROR]
            warning_messages = [message for message in received_messages if message.level == Status.WARNING]

            for message in error_messages:
                if current_status != Status.ERROR:
                    current_status = Status.ERROR

                if 'errors' not in values:
                    values['errors'] = list()

                values['errors'].append(message.message)

            if warning_messages and current_status < Status.WARNING:
                current_status = Status.WARNING

            values['result'] = current_status
            return values

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response
