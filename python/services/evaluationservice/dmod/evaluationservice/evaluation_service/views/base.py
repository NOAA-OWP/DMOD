"""
Defines base objects used to dictate how subclassed views should behave
"""
from __future__ import annotations

import os
import typing
import abc
from datetime import datetime

from typing_extensions import ParamSpec
from typing_extensions import Concatenate

from http import HTTPStatus

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import JsonResponse
from django.urls import re_path
from dmod.core.common import Status
from rest_framework.authentication import BasicAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView

from service import COMMON_DATETIME_FORMAT
from ..messages.base import BaseResponse
from ..messages.base import BaseRequest

_REQUEST_TYPE = typing.TypeVar("_REQUEST_TYPE", bound=BaseRequest, covariant=True)
_RESPONSE_TYPE = typing.TypeVar("_RESPONSE_TYPE", bound=BaseResponse, covariant=True)

ARGS_AND_KWARGS = ParamSpec("ARGS_AND_KWARGS")

VIEW_FUNCTION = typing.Callable[
    Concatenate[HttpRequest, ARGS_AND_KWARGS],
    typing.Union[
        typing.Coroutine[typing.Any, typing.Any, HttpResponseNotAllowed],
        HttpResponseNotAllowed
    ]
]


class MessageView(APIView, typing.Generic[_REQUEST_TYPE, _RESPONSE_TYPE]):
    authentication_classes = [TokenAuthentication, BasicAuthentication]

    @classmethod
    def add_url(
        cls,
        url_patterns: typing.MutableSequence,
        application_name: str,
        path: str,
        name: str,
        *,
        schema_args: typing.Mapping = None,
        **init_kwargs
    ) -> typing.MutableSequence:
        if schema_args is None:
            schema_args = dict()

        if path.endswith("$"):
            path = path[:-1]

        if path.endswith("/?"):
            path = path[:-2]

        view_path = re_path(f"{path}/?$", cls.as_view(**init_kwargs), name=name)

        schema_view: VIEW_FUNCTION = cls.schema_view(
            application_name=application_name,
            path=path,
            name=name,
            **schema_args
        )

        schema_path = re_path(f"{path}/schema/?$", schema_view, name=f"{name}_Schema")

        url_patterns.append(view_path)
        url_patterns.append(schema_path)

        return url_patterns

    @classmethod
    def schema(cls) -> dict:
        schema_data = {
            "response_time": datetime.now().astimezone().strftime(COMMON_DATETIME_FORMAT),
            cls.__name__: {
                "request": cls.get_request_type().schema(),
                "response": cls.get_request_type().get_response_type().schema()
            }
        }
        return schema_data

    @classmethod
    def schema_view(
        cls,
        application_name: str,
        path: str,
        name: str,
        **initkwargs
    ) -> VIEW_FUNCTION:
        return cls.SchemaView.as_view(
            request_class=cls.get_request_type(),
            application_name=application_name,
            path=path,
            name=name,
            **initkwargs
        )

    class SchemaView(APIView):
        def __init__(
            self,
            request_class: typing.Type[_REQUEST_TYPE],
            application_name: str,
            path: str,
            name: str,
            *args,
            **kwargs
        ):
            super().__init__(*args, **kwargs)
            self.__application_name = application_name
            self.__request_class = request_class
            self.__name = name
            path = path[1:] if path.startswith("^") else path
            self.__path = "/" + os.path.join(application_name, path)

        def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
            schema_data = dict()
            schema_data['response_time'] = datetime.now().astimezone().strftime(COMMON_DATETIME_FORMAT)
            schema_data['path'] = self.path
            schema_data['action'] = self.name
            schema_data['request'] = self.request_class.schema()
            schema_data['response'] = self.request_class.get_response_type().schema()
            response = JsonResponse(data=schema_data)

            response.status_code = HTTPStatus.OK

            return response

        @property
        def application_name(self) -> str:
            return self.__application_name

        @property
        def request_class(self):
            return self.__request_class

        @property
        def name(self):
            return self.__name

        @property
        def path(self):
            return self.__path

    @classmethod
    @abc.abstractmethod
    def get_request_type(cls) -> typing.Type[_REQUEST_TYPE]:
        """
        Get the type of Request that this view should accept
        """
        ...

    @abc.abstractmethod
    def handle_message(self, message: _REQUEST_TYPE, **path_parameters) -> _RESPONSE_TYPE:
        pass

    @classmethod
    def deserialize_message(cls, message: typing.Mapping) -> _REQUEST_TYPE:
        return cls.get_request_type().parse_obj(message)

    def process(self, request: HttpRequest, query:  typing.Mapping[str, typing.Any], **path_parameters) -> HttpResponse:

        query = {key: value for key, value in query.items()}

        if "request_id" not in query and "request_id" in request.headers:
            query['request_id'] = request.headers['request_id']

        if 'session_id' not in query and 'session_id' in request.headers:
            query['session_id'] = request.headers['session_id']

        if 'api_token' not in query and 'api_token' in request.headers:
            query['api_token'] = request.headers['api_token']

        query_is_valid = True

        for parameter_name, parameter_value in path_parameters.items():
            if not (parameter_value and parameter_name in self.get_request_type().__fields__):
                continue

            if not query.get(parameter_name):
                query[parameter_name] = parameter_value
            elif query[parameter_name] != parameter_value:
                query_is_valid = False

        deserialized_message: _REQUEST_TYPE = self.deserialize_message(query)

        if query_is_valid:
            try:
                response = self.handle_message(
                    message=deserialized_message,
                    **path_parameters
                )
            except BaseException as exception:
                response = deserialized_message.make_error(
                    message=str(exception),
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    status=Status.ERROR
                )
        else:
            response = deserialized_message.make_error(
                message="Post and path parameters conflict - request cannot be created",
                status_code=HTTPStatus.BAD_REQUEST,
                status=Status.ERROR
            )

        data: dict = response.dict()

        extra_header = dict()

        if "request_id" in data:
            extra_header['request_id'] = data.pop("request_id")

        if "session_id" in data:
            extra_header['session_id'] = data.pop("session_id")

        status_code = data.pop("status_code")

        http_response = JsonResponse(data=data, json_dumps_params={"indent": 4})

        for key, value in extra_header.items():
            http_response.headers[key] = value

        http_response.status_code = status_code

        return http_response

    def get(self, request: HttpRequest, **path_parameters) -> HttpResponse:
        return self.process(request, request.GET, **path_parameters)

    def post(self, request: HttpRequest, **path_parameters) -> HttpResponse:
        return self.process(request, request.POST, **path_parameters)
