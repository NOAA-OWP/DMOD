"""
Backends for IO that operate over some sort of network
"""
import os
import typing
import io

import requests

import dmod.core.common as common

from . import backend
from .. import util
from .. import specification

util.configure_logging()


class RESTBackend(backend.Backend):
    """
    A backend used to retrieve data by a GET request
    """
    @classmethod
    def get_backend_type(cls) -> str:
        return "rest"

    def __init__(self, definition: specification.BackendSpecification, cache_limit: int = None):
        super().__init__(definition, cache_limit)
        self._sources = [definition.address]

    @property
    def request_url(self) -> str:
        """
        Gets the URL that will be made in the request
        """
        url = self.address

        # Make sure that http or https is given in the request
        if not url.startswith("http"):
            if self.verify or self.cert:
                url = f"https://{url}"
            else:
                url = f"http://{url}"

        # Go ahead and return the URL if URL parameters are given explicitly in the definition
        if self.params:
            return url

        if not url.endswith("/"):
            url += "/"

        # Collect anything that might be a query parameter and attach it to the URL
        skip_parameters = ["verify", "cert", "headers", "params"]

        query_arguments = {
            f"{parameter_name}={value}"
            for parameter_name, value in self.definition.properties.items()
            if parameter_name not in skip_parameters
        }

        if query_arguments:
            query_string = "&".join(query_arguments)
            url = f"{url}?{query_string}"

        return url

    @property
    def verify(self):
        """
        Whether there should be SSL verification
        """
        if 'verify' in self.definition.properties:
            return common.is_true(self.definition.properties['verify'])
        return self.cert and os.path.exists(self.cert)

    @property
    def headers(self) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """
        An optional mapping of header parameters
        """
        return self.definition.properties.get('headers')

    @property
    def cert(self) -> typing.Optional[str]:
        """
        The optional path to a certificate for the REST service
        """
        return self.definition.properties.get('cert')

    @property
    def params(self) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """
        An optional mapping of explicit GET parameters
        """
        return self.definition.properties.get('params')

    def read(self, identifier: str, store_data: bool = None) -> bytes:
        """
        Loads data from either the cache or a REST service

        Args:
            identifier: The URL of the REST service
            store_data: Whether to save the data in the cache

        Returns:
            Raw byte data from the request
        """
        if identifier in self._raw_data:
            self._update_access_time(identifier)
            return self._raw_data[identifier][1]

        request_arguments = dict(
            url=self.request_url,
            params=self.params,
            headers=self.headers,
            verify=self.verify,
            cert=self.cert,
        )

        with requests.get(**request_arguments) as response:
            byte_data = response.content

            if store_data:
                self._add_to_cache(identifier, byte_data)

            return byte_data

    def read_stream(self, identifier: str, store_data: bool = None) -> typing.IO:
        """
        Retrieves data in the form of a stream

        Args:
            identifier: The URL of the rest server
            store_data: Whether to store the retrieved data in the cache

        Returns:
            An IO stream containing the loaded data
        """
        raw_data = self.read(identifier, store_data)

        stream = io.BytesIO()
        stream.write(raw_data)
        stream.seek(0)
        return stream
