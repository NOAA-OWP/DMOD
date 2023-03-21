#!/usr/bin/env python3
import os
import typing
import unittest
import abc
import json
import io
import pathlib

from ..evaluations import specification


def get_resource_directory() -> pathlib.Path:
    """
    Returns:
        The path to a directory containing non-code related files
    """
    relative_path = pathlib.Path(os.path.join(os.path.dirname(__file__), 'resources'))
    return relative_path.absolute()


def get_resource_path(resource_name: str) -> pathlib.Path:
    possible_matches: typing.Dict[str, pathlib.Path] = dict()

    for current_directory, contained_directories, contained_files in os.walk(get_resource_directory()):
        for contained_file in contained_files:
            if resource_name == contained_file:
                possible_matches[contained_file] = pathlib.Path(os.path.join(current_directory, contained_file)).absolute()
                continue

            full_name = os.path.join(current_directory, contained_file)

            if full_name.endswith(resource_name):
                possible_matches[contained_file] = pathlib.Path(full_name).absolute()
                continue

            absolute_full_name = os.path.join(*pathlib.Path(full_name).absolute().parts)

            if absolute_full_name.endswith(resource_name):
                possible_matches[contained_file] = pathlib.Path(absolute_full_name)

    if len(possible_matches) == 0:
        raise KeyError(f"There are no resources named '{resource_name}'")

    closest_file = None
    closest_difference: int = 0

    for filename in possible_matches:
        difference = len(filename.replace(resource_name, ""))

        if closest_file is None or difference < closest_difference:
            closest_file = filename
            closest_difference = difference

        if difference == 0:
            break

    return possible_matches[closest_file]


RESOURCE_DIRECTORY = get_resource_directory()
EPSILON = 0.00001


class ConstructionTest(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_model_to_construct(cls) -> typing.Type[specification.Specification]:
        pass

    @property
    @abc.abstractmethod
    def params(self) -> typing.Dict[str, typing.Any]:
        pass

    @property
    @abc.abstractmethod
    def param_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        pass

    def test_basic_construction(self):
        definition = self.get_model_to_construct().create(self.params)

        self.make_assertion_for_single_definition(self, self.params, definition)

    def test_string_construction(self):
        text_params = json.dumps(self.params)

        definition = self.get_model_to_construct().create(text_params)

        self.make_assertion_for_single_definition(self, self.params, definition)

    def test_bytes_construction(self):
        bytes_params = json.dumps(self.params).encode()

        definition = self.get_model_to_construct().create(bytes_params)

        self.make_assertion_for_single_definition(self, self.params, definition)

    def test_byte_buffer_construction(self):
        buffer = io.BytesIO()
        buffer.write(json.dumps(self.params).encode())
        buffer.seek(0)

        definition = self.get_model_to_construct().create(buffer)

        self.make_assertion_for_single_definition(self, self.params, definition)

    def test_string_buffer_construction(self):
        buffer = io.StringIO()
        buffer.write(json.dumps(self.params))
        buffer.seek(0)

        definition = self.get_model_to_construct().create(buffer)

        self.make_assertion_for_single_definition(self, self.params, definition)

    def test_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.param_list)

        self.make_assertions_for_multiple_definitions(self, definitions)

    def test_multiple_string_construction(self):
        text_params = json.dumps(self.param_list)

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(text_params)

        self.make_assertions_for_multiple_definitions(self, definitions)

    def test_multiple_bytes_construction(self):
        bytes_params = json.dumps(self.param_list).encode()

        definitions = self.get_model_to_construct().create(bytes_params)

        self.make_assertions_for_multiple_definitions(self, definitions)

    def test_multiple_byte_buffer_construction(self):
        bytes_params = json.dumps(self.param_list).encode()

        buffer = io.BytesIO()
        buffer.write(bytes_params)
        buffer.seek(0)

        definitions = self.get_model_to_construct().create(buffer)

        self.make_assertions_for_multiple_definitions(self, definitions)

    def test_multiple_string_buffer_construction(self):
        text_params = json.dumps(self.param_list)

        buffer = io.StringIO()
        buffer.write(text_params)
        buffer.seek(0)

        definitions = self.get_model_to_construct().create(buffer)

        self.make_assertions_for_multiple_definitions(self, definitions)

    @classmethod
    def make_assertions_for_multiple_definitions(
            cls,
            test: typing.Union["ConstructionTest", unittest.TestCase],
            definitions: typing.Sequence[specification.Specification],
            parameter_list: typing.Sequence[typing.Dict[str, typing.Any]] = None
    ):
        if parameter_list is None:
            parameter_list = test.param_list

        test.assertEqual(len(parameter_list), len(definitions))
        parameter_index = 0
        for definition in definitions:
            params = parameter_list[parameter_index]
            cls.make_assertion_for_single_definition(test, params, definition)
            parameter_index += 1

    @classmethod
    @abc.abstractmethod
    def make_assertion_for_single_definition(
            cls,
            test: "ConstructionTest",
            parameters: typing.Dict[str, typing.Any],
            definition: specification.Specification
    ):
        pass


class OuterConstructionTest(ConstructionTest, abc.ABC):
    @property
    @abc.abstractmethod
    def full_object_parameters(self) -> typing.Dict[str, typing.Any]:
        pass

    @property
    @abc.abstractmethod
    def partial_object_parameters(self) -> typing.Dict[str, typing.Any]:
        pass

    @property
    @abc.abstractmethod
    def full_object_parameter_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        pass

    @property
    @abc.abstractmethod
    def partial_object_parameter_list(self) -> typing.Sequence[typing.Dict[str, typing.Any]]:
        pass

    def test_full_object_basic_construction(self):
        definition = self.get_model_to_construct().create(self.full_object_parameters)

        self.make_assertion_for_single_definition(self, self.full_object_parameters, definition)

    def test_full_object_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.full_object_parameter_list)

        self.make_assertions_for_multiple_definitions(self, definitions, self.full_object_parameter_list)

    def test_partial_object_basic_construction(self):
        definition = self.get_model_to_construct().create(self.partial_object_parameters)

        self.make_assertion_for_single_definition(self, self.partial_object_parameters, definition)

    def test_partial_object_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.partial_object_parameter_list)

        self.make_assertions_for_multiple_definitions(self, definitions, self.partial_object_parameter_list)
