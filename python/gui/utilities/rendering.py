"""
Defines classes used to send common data to template renderers for
common functionality from the master template
"""
import typing
import json

from django.http import QueryDict
from django.http import HttpRequest

from maas_experiment import application_values


class Notifier:
    def __init__(self, id: str, title: str, url: str):
        self.__id = id
        self.__title = title
        self.__url = url

    @property
    def id(self) -> str:
        return self.__id

    @property
    def title(self) -> str:
        return self.__title

    @property
    def url(self) -> str:
        return self.__url


class Payload:
    def __init__(
        self,
        request: HttpRequest = None,
        context: QueryDict = None,
        notifier_url: str = None,
        style_variables: typing.Dict[str, str] = None,
        notifiers: typing.List[Notifier] = None,
        **kwargs
    ):
        self.__style_variables: typing.Dict[str, str] = style_variables or dict()
        self.__notifier_url: typing.Optional[str] = notifier_url
        self.__context: typing.Dict[str, typing.Any] = dict()
        self.__shared_state: typing.Dict[str, typing.Any] = dict()
        self.__request = request
        self.__notifiers: typing.List[Notifier] = notifiers or list()

        if context:
            for key, value in context.items():
                if "csrf" not in key and "password" not in key:
                    self.__shared_state[key] = value

        # TODO: Add possible user data from the request to the context

        for key, value in kwargs.items():
            self.__context[key] = value
            if not hasattr(self, key):
                setattr(self, key, value)

    @property
    def style_variables(self) -> typing.Dict[str, str]:
        return self.__style_variables.copy()

    @property
    def notifier_url(self) -> typing.Optional[str]:
        return self.__notifier_url

    @property
    def notification_channel(self) -> str:
        return application_values.NOTIFICATION_CHANNEL

    @property
    def shared_state(self) -> typing.Dict[str, typing.Any]:
        return self.__shared_state.copy()

    @property
    def context(self) -> typing.Dict[str, typing.Any]:
        return self.__context.copy()

    @property
    def debug(self):
        return application_values.DEBUG

    @property
    def production(self):
        return not self.debug

    @property
    def notifiers(self):
        return self.__notifiers.copy()

    def set_shared_value(self, key: str, value: typing.Any):
        self.__shared_state[key] = value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4, allow_nan=True)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        dictionary = {
            "style_variables": self.style_variables,
            "notifier_url": self.notifier_url,
            "shared_state": self.shared_state,
            "debug": self.debug,
            "production": self.production,
            "notifiers": self.notifiers
        }

        for key, value in self.context.items():
            dictionary[key] = value

        return dictionary

    def add_style_variable(self, variable_name: str, variable_value: str):
        if not variable_name.startswith("--"):
            variable_name = "--" + variable_name

        self.style_variables[variable_name] = variable_value

    def __setitem__(self, key: str, value: typing.Any):
        self.__context[key] = value
        setattr(self, key, value)

    def __getitem__(self, key: str, default: typing.Any = None):
        return self.__context.get(key, default)

    def items(self) -> typing.ItemsView[str, typing.Any]:
        return self.__context.items()

    def keys(self) -> typing.Iterable[str]:
        return self.__context.keys()

    def values(self) -> typing.Iterable[typing.Any]:
        return self.__shared_state.values()