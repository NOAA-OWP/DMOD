"""
Views for CRUD operations on Specification Templates
"""
from __future__ import annotations

import json
import typing
import abc
from http import HTTPStatus

from django.contrib.auth.models import User
from dmod.core.common import Status
from dmod.evaluations.specification import TemplateDetails
from rest_framework.authentication import BasicAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from typing_extensions import ParamSpec
from typing_extensions import Concatenate

from dmod.core.common import on_each
from dmod.core.common.helper_functions import intersects

from dmod.evaluations.specification import TemplateManager

from evaluation_service.models import SpecificationTemplateCommunicator

from .base import MessageView
from .base import _REQUEST_TYPE
from .base import _RESPONSE_TYPE
from ..messages import ErrorResponse
from ..messages import templates
from ..models import SpecificationTemplate
from ..specification import SpecificationTemplateManager


GENERIC_PARAMETERS = ParamSpec("GENERIC_PARAMETERS")
ManagerFactory = typing.Callable[
    [Concatenate[GENERIC_PARAMETERS]],
    TemplateManager
]


class TemplateView(MessageView[_REQUEST_TYPE, _RESPONSE_TYPE], abc.ABC, typing.Generic[_REQUEST_TYPE, _RESPONSE_TYPE]):
    """
    A view used for manipulating templates
    """
    @classmethod
    def default_manager_factory(cls, *args, **kwargs) -> TemplateManager:
        return SpecificationTemplateManager(*args, **kwargs)

    def __init__(self, *args, manager_factory: ManagerFactory = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_factory = manager_factory or self.__class__.default_manager_factory
    
    @abc.abstractmethod
    def process_templates(self, manager: TemplateManager, message: _REQUEST_TYPE, **path_parameters) -> _RESPONSE_TYPE:
        ...
    
    def handle_message(
        self,
        message: _REQUEST_TYPE,
        **path_parameters
    ) -> _RESPONSE_TYPE:
        return self.process_templates(
            self.manager_factory(),
            message=message,
            **path_parameters
        )        


class GetTemplateSpecificationTypes(
    TemplateView[
        templates.GetTemplateSpecificationTypesRequest,
        templates.GetTemplateSpecificationTypesRequest.Response
    ]
):
    @classmethod
    def get_request_type(cls) -> typing.Type[templates.GetTemplateSpecificationTypesRequest]:
        return templates.GetTemplateSpecificationTypesRequest
    
    def process_templates(
        self,
        manager: TemplateManager,
        message: templates.GetTemplateSpecificationTypesRequest,
        **path_parameters
    ) -> typing.Union[templates.GetTemplateSpecificationTypesRequest.Response, ErrorResponse]:
        specification_types = [
            {
                "value": specification_type[0],
                "text": specification_type[1]
            }
            for specification_type in manager.get_specification_types()
        ]
        response = message.make_response(
            specification_types=specification_types
        )
        return response


class SearchTemplates(
    TemplateView[
        templates.SearchTemplatesRequest,
        templates.TemplateCollectionResponse
    ]
):
    @classmethod
    def get_request_type(cls) -> typing.Type[templates.SearchTemplatesRequest]:
        return templates.SearchTemplatesRequest
    
    def process_templates(
        self,
        manager: TemplateManager,
        message: templates.SearchTemplatesRequest,
        **path_parameters
    ) -> typing.Union[templates.TemplateCollectionResponse, ErrorResponse]:
        response: templates.TemplateCollectionResponse = message.make_response()

        found_templates: typing.Mapping[str, typing.Sequence[TemplateDetails]] = manager.search(
            specification_type=message.specification_type,
            name=message.name,
            author=message.author
        )
        """Each found template organized under its specification type"""

        # Each found template should be added to the response, irrespective of the specification type,
        # so add the details from each specification type to its
        on_each(
            response.add_template_details,
            found_templates.values()
        )

        return response


class GetAllTemplates(
    TemplateView[
        templates.GetAllTemplatesRequest,
        templates.TemplateCollectionResponse
    ]
):
    @classmethod
    def get_request_type(cls) -> typing.Type[templates.GetAllTemplatesRequest]:
        return templates.GetAllTemplatesRequest
    
    def process_templates(
        self,
        manager: TemplateManager,
        message: templates.GetAllTemplatesRequest,
        **path_parameters
    ) -> typing.Union[templates.TemplateCollectionResponse, ErrorResponse]:
        response = message.make_response()

        on_each(
            lambda found_templates: on_each(response.add_template_details, found_templates),
            manager.get_all_templates().values()
        )

        return response


class GetTemplate(
    TemplateView[
        templates.GetTemplateRequest,
        templates.GetTemplateRequest.Response
    ]
):
    @classmethod
    def get_request_type(cls) -> typing.Type[templates.GetTemplateRequest]:
        return templates.GetTemplateRequest
    
    def process_templates(
        self,
        manager: TemplateManager,
        message: templates.GetTemplateRequest,
        **path_parameters
    ) -> typing.Union[templates.GetTemplateRequest.Response, ErrorResponse]:
        template = manager.get_template(
            specification_type=message.specification_type,
            name=message.name,
            author=message.author
        )

        if template:
            return message.make_response(template=template)
        else:
            return message.make_error(
                f"There are no templates created by '{message.author}' of type '{message.specification_type}' "
                f"named '{message.name}'.",
                status_code=HTTPStatus.NOT_FOUND,
                status=Status.ERROR
            )


class GetTemplateByID(
    TemplateView[
        templates.GetTemplateByIDRequest,
        templates.GetTemplateByIDRequest.Response
    ]
):
    @classmethod
    def get_request_type(cls) -> typing.Type[templates.GetTemplateByIDRequest]:
        return templates.GetTemplateByIDRequest
    
    def process_templates(
        self,
        manager: TemplateManager,
        message: templates.GetTemplateByIDRequest,
        **path_parameters
    ) -> typing.Union[templates.GetTemplateByIDRequest.Response, ErrorResponse]:
        possible_specification_template = SpecificationTemplateCommunicator.filter(pk=message.template_id)

        if possible_specification_template:
            return message.make_response(
                template=possible_specification_template[0].template_configuration
            )

        return message.make_error(
            message=f"There are no templates with an ID of {message.template_id}",
            status=Status.ERROR,
            status_code=HTTPStatus.NOT_FOUND
        )


class SaveTemplate(MessageView[templates.SaveTemplateRequest, templates.SaveTemplateRequest.Response]):
    """
    A view used for saving templates
    """
    authentication_classes = [TokenAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    allowed_methods = ["post"]

    @classmethod
    def get_request_type(cls) -> typing.Type[templates.SaveTemplateRequest]:
        return templates.SaveTemplateRequest

    def handle_message(
        self,
        message: templates.SaveTemplateRequest,
        *args,
        **kwargs
    ) -> typing.Union[templates.SaveTemplateRequest.Response, ErrorResponse]:
        try:
            if isinstance(message.template, str):
                json.loads(message.template)
        except BaseException as e:
            raise ValidationError("Cannot save template - it is not valid JSON") from e

        user: User = self.request.user

        if user.is_anonymous:
            raise PermissionDenied("You must be authenticated to edit this specification template")

        if message.template_id and SpecificationTemplateCommunicator.filter(pk=message.template_id):
            record: SpecificationTemplate = SpecificationTemplateCommunicator.filter(pk=message.template_id)[0]

            if record.author != user and not user.is_superuser:
                raise PermissionDenied("You cannot edit specifications that you do not own")

            record.template_configuration = message.template
            record.template_description = message.description
            record.template_name = message.name
            record.template_specification_type = message.specification_type
            record.save()
            record.refresh_from_db()
            was_created = False
        else:
            possible_record = SpecificationTemplateCommunicator.filter(
                author=user,
                template_specification_type=message.specification_type,
                template_name__icontains=message.name
            )

            if possible_record:
                record = possible_record[0]
                record.template_description = message.description
                record.template_configuration = message.template
                record.save()
                record.refresh_from_db()
                was_created = False
            else:
                record = SpecificationTemplateCommunicator.create(
                    author=user,
                    template_name=message.name,
                    template_description=message.description,
                    template_configuration=message.template,
                    template_specification_type=message.specification_type
                )
                was_created = True

        response = message.make_response(
            specification_type=record.template_specification_type,
            name=record.template_name,
            author=user.username,
            template_id=record.pk,
            description=record.description,
            created=was_created
        )

        return response