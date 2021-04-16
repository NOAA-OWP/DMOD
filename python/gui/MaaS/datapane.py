#!/usr/bin/env python

import typing
from . import utilities

class Choice(object):
    def __init__(self, value: str, description: str = None, name: str = None):
        if name is None:
            name = utilities.humanize(value)

        if description is None:
            description = ""

        self.name = name.strip()
        self.value = value
        self.description = description.strip()

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self.__dict__)


class Input(object):
    def __init__(self, input_id: str, input_type: str, description: str = None, name: str = None):
        if description is None:
            description = ""

        if name is None:
            name = utilities.humanize(input_id)

        self.id = input_id
        self.name = name
        self.input_type = input_type
        self.description = description.strip()
        self.attributes: typing.Dict[str, str] = dict()
        self.choices: typing.List[Choice] = list()

    def add_choice(self, value: str, description: str = None, name: str = None):
        self.choices.append(Choice(value, description, name))

    def set_attribute(self, key: str, value: str):
        self.attributes[key] = value

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self.__dict__)
