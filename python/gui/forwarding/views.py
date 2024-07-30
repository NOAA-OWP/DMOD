"""
Defines a view used to send basic REST requests and response to and from another service
"""
import os
import typing
import pathlib
import ssl

import requests

from django.views.generic import View
from django.http.request import HttpRequest
from django.http.response import HttpResponse

from .configuration import ForwardingConfiguration


class ForwardingView(View):
    """
    A view that simply forwards requests to a view on another service via REST
    """

    @classmethod
    def view_from_configuration(
        cls,
        configuration: ForwardingConfiguration
    ) -> typing.Coroutine[typing.Any, typing.Any, None]:
        interface = cls.as_view(
            target_host_name=configuration.name,
            target_host_url=configuration.url,
            target_host_path=configuration.path,
            target_host_port=configuration.port,
            use_ssl=configuration.use_ssl,
            certificate_path=configuration.certificate_path
        )

        return interface

    def __init__(
        self,
        target_host_name: str,
        target_host_url: str,
        target_host_port: typing.Optional[typing.Union[str, int]],
        target_host_path: str = None,
        use_ssl: bool = False,
        certificate_path: typing.Union[str, pathlib.Path] = None,
        *args,
        **kwargs
    ):
        """
        Constructor

        Args:
            target_host_name: A helpful name for the target that this proxy leads to
            target_host_url: The URL to the target that this proxy leads to
            source_route: The registered route that may access this view
            target_host_port: The port for the target that this proxy leads to
            target_host_path: An additional path on the target service to the desired socket endpoint
            use_ssl: Whether to utilize SSL on the websocket connection
            certificate_path: The path to an SSL certificate to use if SSL is to be employed
        """
        super().__init__(*args, **kwargs)
        self.__target_host_name: str = target_host_name
        self.__target_host_url: str = target_host_url
        self.__target_host_port: typing.Optional[typing.Union[str, int]] = target_host_port
        self.__target_host_path: typing.Optional[str] = target_host_path or ""
        self.__use_ssl = use_ssl or False

        if target_host_url.startswith("https://"):
            self.__use_ssl = True

        self._certificate_path: str = str(certificate_path) if certificate_path else None
        self._ssl_context: typing.Optional[ssl.SSLContext] = None

    @property
    def target_host_name(self) -> str:
        """
        The name of the service to connect to
        """
        return self.__target_host_name

    @property
    def target_host_url(self) -> str:
        """
        The URL of the service to connect to
        """
        return self.__target_host_url

    @property
    def target_host_path(self):
        return self.__target_host_path

    @property
    def target_host_port(self) -> typing.Optional[typing.Union[str, int]]:
        """
        The port of the service to connect to
        """
        return self.__target_host_port

    @property
    def uses_ssl(self) -> bool:
        return self.__use_ssl

    @property
    def certificate_path(self) -> typing.Optional[str]:
        return self._certificate_path

    @property
    def target_connection_url(self) -> str:
        """
        The full URL for the target service to connect to
        """
        # No protocol has to be given if the target url already has it
        if self.__target_host_url.startswith("http://") or self.__target_host_url.startswith("https://"):
            protocol: str = ""
        else:
            protocol = "https://" if self.__use_ssl else "http://"

        # The port needs to be attached to the url like ":PORT_NUMBER", so add ":" if there is a port defined
        port = f":{self.__target_host_port}" if self.__target_host_port else ""

        # Remove the ending '/' if it's there
        if port and self.__target_host_url.endswith("/"):
            host_url = self.__target_host_url[:-1]
        else:
            host_url = self.__target_host_url

        # If a path is given, prepend it with a '/' if it's not there
        if self.__target_host_path and not self.__target_host_path.startswith("/"):
            path = f"/{self.__target_host_path}"
        else:
            path = self.__target_host_path

        url = f"{protocol}{host_url}{port}{path}"

        return url

    @property
    def use_ssl(self) -> bool:
        return self.__use_ssl

    @property
    def ssl_context(self) -> typing.Optional[ssl.SSLContext]:
        if not self.__use_ssl:
            return None

        if not self._ssl_context:
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if not self._certificate_path:
                raise ValueError(
                    f"An SSL certificate is required to connect to {self.__target_host_name} as configured, "
                    f"but none was given."
                )
            elif not os.path.exists(self._certificate_path):
                raise ValueError(
                    f"The SSL Certificate needed to connect to {self.__target_host_name} was not "
                    f"found at {self._certificate_path}"
                )
            elif os.path.isfile(self._certificate_path):
                self._ssl_context.load_verify_locations(cafile=self._certificate_path)
            else:
                self._ssl_context.load_verify_locations(capath=self._certificate_path)

        return self._ssl_context

    def _action(self, method: str, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # Can't use request.headers.copy because that'll prevent future mutation
        headers = {key: value for key, value in request.headers.items()}

        if "Content-Length" in headers and headers['Content-Length'] == "":
            headers['Content-Length'] = str(len(request.body))

        if "extra_path" in kwargs:
            url = os.path.join(self.target_connection_url, kwargs['extra_path'])
        else:
            url = self.target_connection_url

        forward_args = dict(
            method=method,
            url=url,
            data=request.body,
            headers=headers,
            cookies=request.COOKIES.copy(),
            verify=self.ssl_context
        )
        with requests.request(**forward_args) as response:
            forward_response = HttpResponse(
                content=response.content,
                status=response.status_code,
                headers=response.headers
            )
            return forward_response

    def get(self, request: HttpRequest, *args, **kwargs):
        return self._action("get", request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs):
        return self._action("post", request, *args, **kwargs)

    def delete(self, request: HttpRequest, *args, **kwargs):
        return self._action("delete", request, *args, **kwargs)

    def put(self, request: HttpRequest, *args, **kwargs):
        return self._action("put", request, *args, **kwargs)

    def options(self, request: HttpRequest, *args, **kwargs):
        return self._action("options", request, *args, **kwargs)

    def patch(self, request: HttpRequest, *args, **kwargs):
        return self._action("patch", request, *args, **kwargs)

    def head(self, request: HttpRequest, *args, **kwargs):
        return self._action("head", request, *args, **kwargs)

    def trace(self, request: HttpRequest, *args, **kwargs):
        return self._action("trace", request, *args, **kwargs)
