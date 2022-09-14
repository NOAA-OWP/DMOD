import abc
import typing
from numbers import Number
from typing import Dict
from typing import Union

from dmod.core import decorators

from ..message import AbstractInitRequest
from ..message import MessageEventType
from .exceptions import RegistrationError


class Field:
    def __init__(
        self,
        member: str,
        key: str = None,
        required: bool = False,
        *args,
        **kwargs
    ):
        self.__key = key or member
        self.__member = member
        self.__required = bool(required)

    @property
    def key(self):
        return self.__key

    @property
    def member(self):
        return self.__member

    @property
    def required(self):
        return bool(self.__required)


class RegisteredMessage(AbstractInitRequest):
    event_type: MessageEventType = MessageEventType.INFORMATION_UPDATE

    def __init__(self, document: dict, *args, **kwargs):
        self.__message = document
        self.__field_values: typing.Dict[str, typing.Any] = dict()
        fields = self._get_fields()

        if len(fields) < 1:
            raise RegistrationError(
                f"There aren't enough fields in {self.__class__.__name__} for it to be considered a valid message type"
            )

        for field in fields:
            if field.key not in document and field.required:
                raise RegistrationError()
            value = document.get(field.key)
            setattr(self, field.member, value)
            self.__field_values[field.member] = value

    def __getitem__(self, member: str):
        if member not in self.__field_values:
            raise KeyError(f"There is no {member} field in a {self.__class__.__name__}")
        return self.__field_values[member]

    @classmethod
    @abc.abstractmethod
    def _get_fields(cls) -> typing.Collection[Field]:
        pass

    @property
    def original_message(self) -> dict:
        return {
            key: value
            for key, value in self.__message.items()
        }

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        all_fields_are_present = True
        required_fields = [field for field in cls._get_fields() if field.required]

        if len(required_fields) < 1:
            raise RegistrationError(
                f"There aren't required enough fields in {cls.__name__} for it to be considered a valid message type"
            )

        for field in required_fields:
            all_fields_are_present = all_fields_are_present and field.key in json_obj

        if all_fields_are_present:
            return cls(json_obj)
        return None

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        return self.original_message
