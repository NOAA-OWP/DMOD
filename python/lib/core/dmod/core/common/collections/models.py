"""
Defines Collections modeled via Pydantic
"""
from __future__ import annotations

import typing

import pydantic
from pydantic.generics import GenericModel

from .eventful_collections import BaseEventfulMap
from .eventful_collections import BaseEventfulSequence

from .event_types import CollectionEvent
from .event_types import KeyType
from .event_types import ValueType
from .event_types import EntryType


HandlerMap = typing.Dict[CollectionEvent, typing.List[typing.Callable]]
TaskList = typing.List[typing.Awaitable]


class MapModel(GenericModel, BaseEventfulMap[KeyType, ValueType], typing.Generic[KeyType, ValueType]):
    def get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    def inner_map(self) -> typing.MutableMapping[KeyType, ValueType]:
        return self.__root__

    def _get_leftover_tasks(self) -> TaskList:
        return self._leftover_tasks

    __root__: typing.Dict[KeyType, ValueType]
    _handlers: HandlerMap = pydantic.PrivateAttr(default_factory=dict)
    _leftover_tasks: TaskList = pydantic.PrivateAttr(default_factory=list)


class SequenceModel(GenericModel, BaseEventfulSequence[EntryType], typing.Generic[EntryType]):
    @property
    def _inner_sequence(self) -> typing.MutableSequence[EntryType]:
        return self.__root__

    def _get_handlers(self) -> typing.Dict[CollectionEvent, typing.MutableSequence[typing.Callable]]:
        return self._handlers

    __root__: typing.List[EntryType] = pydantic.Field(default_factory=list)
    _handlers: HandlerMap = pydantic.PrivateAttr(default_factory=dict)