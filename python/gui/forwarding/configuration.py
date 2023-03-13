"""
Put a module wide description here
"""
import sys
import os
import typing
import pathlib
import json


PATTERN_PARAMETERS = [
    "(?P<extra_path>.+)"
]


# TODO: This is most likely a prime candidate for Pydantic
class ForwardingConfiguration:
    REQUIRED_PARAMETERS: typing.Final[typing.List[str]] = [
        "name",
        "route",
        "url"
    ]

    @classmethod
    def is_valid_configuration(cls, obj) -> bool:
        if isinstance(obj, typing.Mapping):
            missing_keys = [key not in obj.keys() for key in cls.REQUIRED_PARAMETERS]
            valid = sum(missing_keys) == 0
        elif isinstance(obj, typing.Iterable):
            inner_elements_are_invalid = [
                not cls.is_valid_configuration(inner_element)
                for inner_element in obj
            ]

            valid = sum(inner_elements_are_invalid) == 0
        else:
            valid = False

        return valid

    @classmethod
    def load(cls, path: typing.Union[pathlib.Path, str]) -> typing.Iterable["ForwardingConfiguration"]:
        path = str(path)

        configurations: typing.Iterable["ForwardingConfiguration"] = list()
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path) as configuration_file:
                    configurations = cls.load_from_file(configuration_file)
            except Exception as e:
                print(
                    f"Proxy configuration data could not be parsed - {str(e)}",
                    file=sys.stderr
                )
        elif os.path.exists(path) and os.path.isdir(path):
            print(
                f"Can't read proxy configurations from {path}; it is a directory, not a file",
                file=sys.stderr
            )
        else:
            print(
                f"Can't read proxy configurations from {path}; nothing can be read from there"
            )
        return configurations

    @classmethod
    def load_from_file(cls, fp) -> typing.Iterable["ForwardingConfiguration"]:
        configurations: typing.List["ForwardingConfiguration"] = list()
        configuration_data: typing.Optional[typing.Union[list, dict]] = None

        try:
            configuration_data = json.load(fp)
        except Exception as e:
            print(
                f"Proxy configuration data could not be read as valid JSON - {str(e)}",
                file=sys.stderr
            )

        if configuration_data is not None:
            if not cls.is_valid_configuration(configuration_data):
                print(
                    f"Given proxy configuration data is incorrectly formatted - please ensure the formatting is correct",
                    file=sys.stderr
                )
            elif isinstance(configuration_data, typing.Mapping):
                configurations.append(
                    cls(**configuration_data)
                )
            else:
                configurations = [
                    cls(**configuration)
                    for configuration in configuration_data
                ]
        return configurations

    def __init__(
        self,
        name: str,
        route: str,
        url: str,
        port: typing.Union[int, str] = None,
        path: str = None,
        use_ssl: bool = None,
        certificate_path: str = None,
        **kwargs
    ):
        self.__name = name
        self.__route = route
        self.__url = url
        self.__port = port
        self.__path = path
        self.__use_ssl = use_ssl or False
        self.__certificate_path = certificate_path

    @property
    def name(self) -> str:
        return self.__name

    @property
    def route(self) -> str:
        return self.__route

    @property
    def url(self) -> str:
        return self.__url

    @property
    def port(self) -> typing.Optional[typing.Union[int, str]]:
        return self.__port

    @property
    def use_ssl(self) -> bool:
        return self.__use_ssl

    @property
    def certificate_path(self) -> typing.Optional[str]:
        return self.__certificate_path

    @property
    def path(self) -> typing.Optional[str]:
        return self.__path

    @property
    def route_pattern(self) -> str:
        pattern = self.route

        if not pattern.endswith("/?"):
            pattern += "?" if pattern.endswith("/") else "/?"

        added_parameter = False
        for parameter in PATTERN_PARAMETERS:
            if parameter not in pattern:
                pattern += f"{'/' if added_parameter else ''}{parameter}"
                added_parameter = True

        if added_parameter:
            pattern += "?"

        return pattern

    @property
    def target_connection_url(self) -> str:
        """
        The full URL for the target service to connect to
        """
        # The port needs to be attached to the url like ":PORT_NUMBER", so add ":" if there is a port defined
        port = f":{self.port}" if self.port else ""

        # Remove the ending '/' if it's there
        if port and self.url.endswith("/"):
            host_url = self.url[:-1]
        else:
            host_url = self.url

        # If a path is given, prepend it with a '/' if it's not there
        if self.path and not self.path.startswith("/"):
            path = f"/{self.path}"
        else:
            path = self.path or ""

        url = f"{host_url}{port}{path}"

        return url

    def __str__(self):
        return f"[{self.name}]: Connect {self.route} to {self.target_connection_url}"

