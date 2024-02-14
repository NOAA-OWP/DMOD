"""
Defines Collections modeled via Pydantic
"""
from __future__ import annotations

import typing

import pydantic
from pydantic.generics import GenericModel

from .base_models import EventfulMap
from .base_models import BaseEventfulSequence

from .constants import CollectionEvent
from .constants import KeyType
from .constants import ValueType
from .constants import EntryType


HANDLER_MAP = typing.Dict[CollectionEvent, typing.List[typing.Callable]]


class MapModel(GenericModel, EventfulMap[KeyType, ValueType], typing.Generic[KeyType, ValueType]):
    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    def inner_map(self) -> typing.MutableMapping[KeyType, ValueType]:
        return self.__root__

    __root__: typing.Dict[KeyType, ValueType]
    _handlers: HANDLER_MAP = pydantic.PrivateAttr(default_factory=dict)


class SequenceModel(GenericModel, BaseEventfulSequence[EntryType], typing.Generic[EntryType]):
    @property
    def _inner_sequence(self) -> typing.MutableSequence[EntryType]:
        return self.__root__

    def _get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    __root__: typing.List[EntryType] = pydantic.Field(default_factory=list)
    _handlers: HANDLER_MAP = pydantic.PrivateAttr(default_factory=dict)