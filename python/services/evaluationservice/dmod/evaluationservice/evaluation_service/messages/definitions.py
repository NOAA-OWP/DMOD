"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing

from pydantic import BaseModel
from pydantic import validator
from pydantic.fields import Json
from pydantic import Field
from pydantic import root_validator

from dmod.evaluations.specification import EvaluationSpecification
from dmod.core.common import Status

from .response import BaseResponse

class DefinitionMetadata(BaseModel):
    """
    Metadata defining information like an evaluation specifications ID and its author
    """
    definition_id: int
    author: str
    title: str
    description: str


class SearchForDefinitionMessage(BaseModel):
    """
    A message that asks for metadata for all definitions that have the indicated author and/or title
    """
    author: typing.Optional[str] = Field(default=None, description="The name of the author of the definitions to look for")
    title: typing.Optional[str] = Field(default=None, description="A pattern that might match on evaluations to look for")

    class Response(BaseResponse):
        """
        A response bearing metadata for all found definitions
        """
        definitions: typing.List[DefinitionMetadata]


class GetSavedDefinitionMessage(BaseModel):
    """
    A message that returns a full evaluation specification based on the given ID
    """
    definition_id: int = Field(description="The ID of the stored definition")

    class Response(BaseResponse):
        """
        A response containing the definition that matches the
        """
        definition: typing.Optional[EvaluationSpecification]


class SaveDefinitionMessage(DefinitionMetadata):
    definition: EvaluationSpecification = Field(description="The evaluation definition to store")

    class Response(BaseResponse, DefinitionMetadata):
        ...


class ValidationMessage(BaseModel):
    message: str
    level: Status

    @validator
    def _transform_level(cls, value: typing.Union[Status, str, int]) -> Status:
        return Status.get(value)

    def __eq__(self, other: ValidationMessage):
        return self.message == other.message and self.level == other.level

class ValidateDefinitionMessage(BaseModel):
    definition_id: typing.Optional[int]
    definition: typing.Optional[EvaluationSpecification]

    class Response(BaseResponse):
        messages: typing.List[ValidationMessage]

        def add_message(self, message: str, level: typing.Union[Status, int, str]):
            level = Status.get(level)
            validation = ValidationMessage(message=message, level=level)

            if validation in self.messages:
                return

            self.messages.append(ValidationMessage(message=message, level=level))

            if level == Status.ERROR:
                self.errors.append(message)

            if level > self.status:
                self.status = level

        @root_validator
        def _interpret_success(cls, values: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
            received_messages: typing.List[ValidationMessage] = values.get("messages", list())
            current_status: Status = values.get("status") or cls.__fields__.get("status").default or Status.default()

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

            values['status'] = current_status
            return values
