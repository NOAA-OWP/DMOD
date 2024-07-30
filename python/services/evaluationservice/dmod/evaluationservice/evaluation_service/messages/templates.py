"""
Defines messages used to communicate with endpoints for specification templates
"""
from __future__ import annotations

import typing
from collections import defaultdict

from dmod.core.common.types import TEXT_VALUE_DICT_LIST
from dmod.evaluations.specification import TemplateDetails
from pydantic import BaseModel
from pydantic import Json
from pydantic import Field

from dmod.core.common import CommonEnum
from dmod.core.common import TEXT_VALUE_COLLECTION

from .base import BaseRequest
from .base import BaseResponse
from .base import RESPONSE_TYPE


class TemplateAction(str, CommonEnum):
    GET_SPECIFICATION_TYPES = "GET_SPECIFICATION_TYPES"
    SEARCH_TEMPLATES = "SEARCH_TEMPLATES"
    GET_ALL_TEMPLATES = "GET_ALL_TEMPLATES"
    GET_TEMPLATE = "GET_TEMPLATE"
    GET_TEMPLATE_BY_ID = "GET_TEMPLATE_BY_ID"
    SAVE_TEMPLATE = "SAVE_TEMPLATE"

    @classmethod
    def default(cls):
        raise ValueError(f"Cannot form a default {cls.__name__}; There is no default action")


class GetTemplateSpecificationTypesRequest(BaseRequest):
    """
    Message type used to get data about what all can be made or read as a template
    """
    class Response(BaseResponse):
        specification_types: TEXT_VALUE_DICT_LIST

    action: typing.Optional[typing.Literal[TemplateAction.GET_SPECIFICATION_TYPES]] = Field(default=TemplateAction.GET_SPECIFICATION_TYPES)

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response


class TemplateMetadata(BaseModel):
    """
    Metadata describing a template
    """
    description: str
    name: str
    specification_type: str
    id: typing.Optional[int] = Field(
        default=None,
        description="The unique ID of the template"
    )
    author: typing.Optional[str] = Field(
        default=None,
        description="The author of the template"
    )

    @classmethod
    def from_details(cls, template: TemplateDetails) -> TemplateMetadata:
        metadata: TemplateMetadata = TemplateMetadata(
            name=template.name,
            description=template.description,
            specification_type=template.specification_type,
            author=str(template.author) if hasattr(template, "author") else None,
            id=template.id if hasattr(template, "id") else None
        )
        return metadata


class TemplateCollectionResponse(BaseResponse):
    templates: typing.Optional[typing.Dict[str, typing.List[TemplateMetadata]]] = Field(
        default_factory=lambda: defaultdict(list)
    )

    def add_template_metadata(self, metadata: TemplateMetadata):
        if not self.has_metadata(metadata=metadata):
            self.templates[metadata.specification_type].append(metadata)

    def has_metadata(self, metadata: TemplateMetadata) -> bool:
        return metadata.specification_type in self.templates \
            and metadata in self.templates[metadata.specification_type]

    def add_template_details(self, details: typing.Union[TemplateDetails, typing.Sequence[TemplateDetails]]):
        if isinstance(details, TemplateDetails):
            details = [details]

        for template_details in details:
            metadata: TemplateMetadata = TemplateMetadata.from_details(template_details)
            self.add_template_metadata(metadata)

    def add_template_data(
        self,
        identifier: int,
        name: str,
        description: str,
        specification_type: str,
        author: str
    ):
        metadata = TemplateMetadata(
            id=identifier,
            name=name,
            description=description,
            specification_type=specification_type,
            author=author
        )
        self.add_template_metadata(metadata)


class SearchTemplatesRequest(BaseRequest):
    """
    Message type used to search templates
    """
    action: typing.Optional[typing.Literal[TemplateAction.SEARCH_TEMPLATES]] = Field(
        default=TemplateAction.SEARCH_TEMPLATES
    )
    specification_type: typing.Optional[str] = Field(default=None)
    author: typing.Optional[str] = Field(default=None)
    name: typing.Optional[str] = Field(default=None)

    @property
    def has_query(self) -> bool:
        return self.specification_type is not None \
            or self.author is not None \
            or self.name is not None

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return TemplateCollectionResponse


class GetAllTemplatesRequest(BaseRequest):
    """
    Message type used to fetch all available templates
    """
    action: typing.Optional[typing.Literal[TemplateAction.GET_ALL_TEMPLATES]] = Field(
        default=TemplateAction.GET_ALL_TEMPLATES
    )

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return TemplateCollectionResponse


class GetTemplateRequest(BaseRequest):
    """
    Message type used to fetch a template based on the type, its name, and who wrote it
    """
    action: typing.Optional[typing.Literal[TemplateAction.GET_TEMPLATE]] = Field(default=TemplateAction.GET_TEMPLATE)
    specification_type: str
    name: str
    author: str

    class Response(BaseResponse):
        template: typing.Optional[typing.Union[str, Json, dict]] = Field(default=None)

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response


class SaveTemplateRequest(BaseRequest):
    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response

    action: typing.Optional[typing.Literal[TemplateAction.SAVE_TEMPLATE]] = Field(default=TemplateAction.SAVE_TEMPLATE)
    specification_type: str
    name: str
    author: str
    description: str
    template: typing.Union[str, Json, dict]
    template_id: typing.Optional[int]

    class Response(BaseResponse):
        specification_type: str
        description: str
        name: str
        author: str
        template_id: int
        created: bool


class GetTemplateByIDRequest(BaseRequest):
    """
    Message type used to fetch a template based on a specific ID
    """
    action: typing.Optional[typing.Literal[TemplateAction.GET_TEMPLATE_BY_ID]] = Field(
        default=TemplateAction.GET_TEMPLATE_BY_ID
    )
    template_id: int

    class Response(BaseResponse):
        template: typing.Optional[typing.Union[str, Json, dict]] = Field(default=None)

    @classmethod
    def get_response_type(cls) -> typing.Type[RESPONSE_TYPE]:
        return cls.Response
