import dataclasses
import os
import typing
from http import HTTPStatus
from collections import namedtuple

from django.http import HttpRequest
from django.urls import re_path
from dmod.core.common import get_subclasses
from rest_framework.views import APIView
from django.http import JsonResponse

from .evaluations import EvaluationList
from .evaluations import EvaluationDetails
from .status import EvaluationStatus
from .listen import Listen
from .launch import LaunchEvaluation
from .launch import ReadyListenEvaluation
from .helpers import Clean
from .helpers import Metrics
from .helpers import Schema
from .geometry import GetGeometry
from .geometry import GetGeometryDatasets
from .library import GetLibrary
from .library import GetLibraryOptions
from .library import LibrarySelector

from .base import BaseRequest
from .base import MessageView
from .definitions import GetDefinition
from .definitions import SaveDefinition
from .definitions import SearchForDefinition
from .definitions import ValidateDefinition

from .templates import GetAllTemplates
from .templates import GetTemplateByID
from .templates import GetTemplate
from .templates import GetTemplateSpecificationTypes
from .templates import SaveTemplate
from .templates import SearchTemplates


def get_message_schema() -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    message_views = {
        view.__name__: dict(schema=view.schema())
        for view in get_subclasses(BaseRequest)
    }
    return message_views


class ViewPath:
    def __init__(
        self,
        view: typing.Type[MessageView],
        path: str,
        *,
        name: str = None,
        schema_kwargs: typing.Dict[str, typing.Any] = None,
        **kwargs
    ):
        if not view and not path:
            raise ValueError("A View Path cannot be created - it is missing both a view and a path")
        elif not path:
            raise ValueError(f"The '{name or view.__name__}' view path cannot be created - the path is missing")
        elif not view:
            raise ValueError(f"The view at '' cannot be created - it is missing a view type")

        self.view = view
        self.path = path
        self.name = name or view.__name__
        self.schema_kwargs = schema_kwargs or dict()
        self.kwargs = kwargs

    def __hash__(self):
        return hash((self.view.__name__, self.path, self.name, str(self.schema_kwargs), str(self.kwargs)))


MASTER_SCHEMA_PATH = "^master/schema/?$"

ViewTypeAndPath = typing.Tuple[typing.Type[MessageView], str]
ViewTypePathAndName = typing.Tuple[typing.Type[MessageView], str, str]

ViewPaths = typing.Union[ViewPath, ViewTypeAndPath, ViewTypePathAndName]

def to_view_path(possible_view_path: ViewPaths):
    if isinstance(possible_view_path, ViewPath):
        return possible_view_path
    elif isinstance(possible_view_path, typing.Tuple) and len(possible_view_path) == 2:
        return ViewPath(*possible_view_path)
    elif isinstance(possible_view_path, typing.Tuple) and len(possible_view_path) == 3:
        return ViewPath(view=possible_view_path[0], path=possible_view_path[1], name=possible_view_path[2])

    raise TypeError(f"'{str(possible_view_path)}' cannot be used as a View Path")


def normalize_view_paths(*paths: ViewPaths) -> typing.Sequence[ViewPath]:
    return [
        to_view_path(path)
        for path in paths
    ]

class MasterSchema(APIView):
    @classmethod
    def assign_message_views(
        cls,
        url_patterns: typing.List[re_path],
        application_name: str,
        *view_path: ViewPaths,
        **kwargs
    ):
        view_paths = normalize_view_paths(*view_path)
        for view_data in view_paths:
            view = view_data.view.as_view(**view_data.kwargs)

            path = view_data.path
            name = view_data.name

            if path.endswith("$"):
                path = path[:-1]

            if path.endswith("/?"):
                path = path[:-2]

            schema_view = view_data.view.schema_view(
                application_name=application_name,
                path=path,
                name=name,
                **view_data.schema_kwargs
            )

            url_patterns.append(
                re_path(f"{path}/?$", view, name=name)
            )

            url_patterns.append(
                re_path(f"{path}/schema/?$", schema_view, name=f"{name}Schema")
            )

        url_patterns.append(
            re_path(
                MASTER_SCHEMA_PATH,
                cls.as_view(application_name=application_name, view_paths=view_paths, **kwargs),
                name="MasterSchema"
            )
        )

    def __init__(self, application_name: str, view_paths: typing.Iterable[ViewPath], **kwargs):
        super().__init__(**kwargs)
        self.__application_name = application_name
        self.__view_paths = [path for path in view_paths]

    @property
    def application_name(self) -> str:
        return self.__application_name

    @property
    def view_paths(self) -> typing.Sequence[ViewPath]:
        return self.__view_paths

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        schema = dict()

        for view_data in self.view_paths:
            name = view_data.name
            path = view_data.path

            if path.startswith("^"):
                path = path[1:]

            path = "/" + os.path.join(self.application_name, path)

            view_data = {
                "path": path,
                "name": name,
                "request": view_data.view.get_request_type().schema(),
                "response": view_data.view.get_request_type().get_response_type().schema()
            }

            schema[name] = view_data

        response = JsonResponse(data=schema)
        response.status_code = HTTPStatus.CREATED
        return response