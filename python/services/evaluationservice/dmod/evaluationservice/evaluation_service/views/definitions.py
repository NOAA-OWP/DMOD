"""
Defines REST views for Evaluation Definitions
"""
from __future__ import annotations

import typing

from http import HTTPStatus

from rest_framework.exceptions import PermissionDenied


from django.db.models import QuerySet
from django.contrib.auth.models import User
from dmod.core.common import Status
from dmod.evaluations.specification import EvaluationSpecification
from rest_framework.permissions import IsAuthenticated

from .base import MessageView
from ..messages import definitions
from ..messages.definitions import DefinitionMetadata
from ..messages.definitions import ValidationMessage
from ..models import EvaluationDefinition
from ..models import EvaluationDefinitionCommunicator
from ..specification import SpecificationTemplateManager


class SearchForDefinition(MessageView[definitions.SearchForDefinitionRequest, definitions.SearchForDefinitionRequest.Response]):
    @classmethod
    def get_request_type(cls) -> typing.Type[definitions.SearchForDefinitionRequest]:
        return definitions.SearchForDefinitionRequest

    def handle_message(
        self,
        message: definitions.SearchForDefinitionRequest,
        *args,
        **kwargs
    ) -> definitions.SearchForDefinitionRequest.Response:
        filter_parameters = dict()

        if message.author:
            filter_parameters["author__icontains"] = message.author

        if message.title:
            filter_parameters["name__icontains"] = message.title

        saved_definitions: typing.Sequence[EvaluationDefinition] = EvaluationDefinition.objects.filter(
            **filter_parameters
        )

        definitions_to_return = [
            DefinitionMetadata(
                definition_id=definition.id,
                author=definition.author,
                title=definition.name,
                description=definition.description
            )
            for definition in saved_definitions
        ]

        return message.make_response(
            definitions=definitions_to_return
        )


class GetDefinition(MessageView[definitions.GetDefinitionRequest, definitions.GetDefinitionRequest.Response]):
    @classmethod
    def get_request_type(cls) -> typing.Type[definitions.GetDefinitionRequest]:
        return definitions.GetDefinitionRequest

    def handle_message(
        self,
        message: definitions.GetDefinitionRequest,
        *args,
        **kwargs
    ) -> definitions.GetDefinitionRequest.Response:
        possible_definition: QuerySet[EvaluationDefinition] = EvaluationDefinition.objects.filter(
            pk=message.definition_id
        )

        if possible_definition:
            configuration: EvaluationDefinition = possible_definition.get()
            code: int = HTTPStatus.OK
            author = configuration.author
            title = configuration.name
            description = configuration.description
            definition = configuration.definition
            definition_id = configuration.pk

            response = message.make_response(
                definition_id=definition_id,
                definition=definition,
                status_code=code,
                author=author,
                title=title,
                description=description,
            )
        else:
            code: int = HTTPStatus.NOT_FOUND
            response = message.make_error(
                message=f"No definitions with an id of '{message.definition_id}' could be found.",
                status_code=code
            )

        return response


class SaveDefinition(MessageView[definitions.SaveDefinitionRequest, definitions.SaveDefinitionRequest.Response]):
    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    @classmethod
    def get_request_type(cls) -> typing.Type[definitions.SaveDefinitionRequest]:
        return definitions.SaveDefinitionRequest

    def handle_message(
        self,
        message: definitions.SaveDefinitionRequest,
        *args,
        **kwargs
    ) -> definitions.SaveDefinitionRequest.Response:
        user: User = self.request.user

        if user.is_anonymous:
            raise PermissionDenied("You must be authenticated to edit this evaluation definition")

        definitions_matching_id = EvaluationDefinitionCommunicator.filter(pk=message.definition_id)
        definitions_matching_user_and_name = EvaluationDefinitionCommunicator.filter(
            owner=user,
            name__icontains=message.title
        )

        if definitions_matching_id:
            record: EvaluationDefinition = definitions_matching_id[0]

            if user != record.owner and not user.is_superuser:
                raise PermissionDenied("You cannot edit definitions that you do not own.")

            record.title = message.title
            record.author = message.author if user.is_superuser else user.username
            record.description = message.description
            record.definition = message.definition
            record.save()
            record.refresh_from_db()
            was_created = False
        elif definitions_matching_user_and_name:
            record = definitions_matching_user_and_name[0]
            record.author = message.author if user.is_superuser else user.username
            record.description = message.description
            record.definition = message.definition
            record.save()
            record.refresh_from_db()
            was_created = False
        else:
            record = EvaluationDefinitionCommunicator.create(
                name=message.title,
                description=message.description,
                author=message.author,
                definition=message.definition,
                owner=user
            )
            was_created = True

        response = message.make_response(
            definition=record.definition,
            definition_id=record.pk,
            created=was_created,
            title=record.name,
            author=record.author,
            description=record.description
        )

        return response


class ValidateDefinition(MessageView[definitions.ValidateDefinitionRequest, definitions.ValidateDefinitionRequest.Response]):
    http_method_names = ["post"]

    @classmethod
    def get_request_type(cls) -> typing.Type[definitions.ValidateDefinitionRequest]:
        return definitions.ValidateDefinitionRequest

    def handle_message(
        self,
        message: definitions.ValidateDefinitionRequest,
        *args,
        **kwargs
    ) -> definitions.ValidateDefinitionRequest.Response:
        messages: typing.List[str] = list()

        try:
            EvaluationSpecification.create(
                data=message.definition,
                template_manager=SpecificationTemplateManager(),
                validate=True,
                messages=messages
            )
        except Exception as exception:
            messages.append(str(exception))

        return message.make_response(messages=[
            ValidationMessage(
                message=validation_message,
                level=Status.ERROR
            )
            for validation_message in messages
        ])