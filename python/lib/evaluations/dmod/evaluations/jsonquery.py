#!/usr/bin/env python3
import os
import typing
import json

from . import util

RESULT_VALUE = typing.Union[str, int, typing.Sequence, typing.Dict[str, typing.Any], None, typing.Tuple[str, typing.Any]]

clause_separator: typing.Final[str] = "/"

WILDCARDS = ("", "#", "*")


class _DocumentElement:
    def __init__(self, data: RESULT_VALUE = None, parent: "_DocumentElement" = None):
        self.__data = data
        self.__parent = parent

    @property
    def value(self) -> RESULT_VALUE:
        return self.__data

    @property
    def parent(self) -> typing.Optional["_DocumentElement"]:
        return self.__parent

    def _query_array(self, first: str, next_query: typing.Sequence[str]) -> typing.Optional["_DocumentElement"]:
        matching_children = list()
        if first in WILDCARDS:
            matching_children.extend(self.__data)
        elif first.isdigit():
            index = int(first)

            if index > len(self.__data):
                raise IndexError(f"Index {index} is out of range - there are only {len(self.__data)} items available")

            matching_children.append(self.__data[index])
        else:
            return _DocumentElement(parent=self)

        child_elements = list()

        for child in matching_children:
            child_results = _DocumentElement(child, parent=self).query(next_query)
            if child_results is None or not child_results.value:
                continue
            if util.is_arraytype(child_results.value):
                child_elements.extend([result for result in child_results.value])
            else:
                child_elements.append(child_results.value)

        return _DocumentElement(child_elements, parent=self)

    def _query_object(self, first: str, next_query: typing.Sequence[str] = None) -> typing.Optional["_DocumentElement"]:
        if first in WILDCARDS:
            child_results = list()

            for value in self.__data.values():
                if value is not None:
                    child_result: _DocumentElement = _DocumentElement(value, parent=self).query(next_query)

                    if util.is_arraytype(child_result.value):
                        child_results.extend([child for child in child_result.value])
                    else:
                        child_results.append(child_result.value)

            return _DocumentElement(child_results, parent=self)

        if first in self.__data:
            return _DocumentElement(self.__data[first], parent=self).query(next_query)
        elif hasattr(self.__data, first):
            return _DocumentElement(getattr(self.__data, first), parent=self).query(next_query)

        return _DocumentElement(parent=self)

    def query(self, recipe: typing.Union[str, typing.Sequence[str]]) -> typing.Optional["_DocumentElement"]:
        if recipe is None:
            return self

        parts = recipe.split(clause_separator) if isinstance(recipe, str) else recipe

        if not parts:
            return self

        first = parts[0]
        next_query = parts[1:] if len(parts) > 1 else list()

        if first == "..":
            if self.__parent is None:
                raise ValueError(f"Cannot follow '{'/'.join(parts)}'; no parent is available")
            return self.__parent.query(next_query)
        if isinstance(self.__data, dict):
            return self._query_object(first, next_query)
        elif util.is_arraytype(self.__data):
            return self._query_array(first, next_query)

        return _DocumentElement(parent=self)

    def __repr__(self):
        return str(self.__data)

    def __str__(self):
        return str(self.__data)

class Document:
    def __init__(self, data: typing.Union[str, typing.Dict[str, typing.Any], typing.IO, bytes]):
        if hasattr(data, 'read'):
            data: typing.Union[str, bytes] = data.read()

        if isinstance(data, bytes):
            data: str = data.decode()

        if isinstance(data, str):
            data: typing.Dict[str, typing.Any] = json.loads(data)

        self.__data: _DocumentElement = _DocumentElement(data.copy())

    @property
    def data(self):
        return self.__data.value

    def query(self, instructions: typing.Union[str, typing.Sequence[str]]) -> RESULT_VALUE:
        if len(instructions) == 0 or (len(instructions) == 1 and instructions[0] in WILDCARDS):
            return self.__data.value

        result = self.__data.query(instructions).value

        if util.is_arraytype(result):
            if len(result) == 1:
                return result[0]
            elif len(result) == 0:
                return None

        return result

    def __str__(self):
        return str(self.__data)

    def __repr__(self):
        return str(self.__data)
