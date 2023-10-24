#!/usr/bin/env python3
import os
import typing
import unittest
import abc
import json
import io
import pathlib
import re
import shutil

from datetime import datetime
from datetime import timedelta

from ..evaluations import specification


OLD_AGE: typing.Final[timedelta] = timedelta(hours=4)
"""The default maximum acceptable age for an output directory"""

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
"""A pattern matching a date such as '2023-10-20'"""


def get_resource_directory() -> pathlib.Path:
    """
    Returns:
        The path to a directory containing non-code related files
    """
    relative_path = pathlib.Path(os.path.join(os.path.dirname(__file__), 'resources'))
    return relative_path.absolute()


def directory_is_old(current_time: datetime, directory: pathlib.Path, maximum_age: timedelta = None) -> bool:
    """
    Determine if an identified directory is too old

    Args:
        current_time: What date to compare to file dates
        directory: The directory to search through
        maximum_age: The oldest a directory is allowed to be

    Returns:
        True if all entries in the directory are older than the maximum age
    """
    if maximum_age is None:
        maximum_age = OLD_AGE

    # Step through each file recursively to find the date and time of the most recently modified file
    #   We know if this directory is old if the amount of time between now and it the modified date of the most
    #   recently modified file is greater than the maximum age
    for file in directory.rglob("*"):
        # Only files are reflective of how recent the data is so only consider skip this entry if it
        # isn't a file
        if not file.is_file():
            continue

        # file.stat will yield the metadata including the times the file was created and modified
        file_stat: os.stat_result = file.stat()

        # The modified time is stored in `st_mtime` as a timestamp number, so load that into a datetime to
        # get a value to work with
        modified_time = datetime.fromtimestamp(file_stat.st_mtime)

        # We can short circuit if we automatically know that this most recent file is young enough to stay
        if current_time - modified_time <= maximum_age:
            return False

    # We only reach this code if no file old enough to stay was found, so go ahead and declare that this directory
    # is too old
    return True


def purge_output(maximum_age: timedelta = None):
    """
    Remove test output deemed old enough to clean up
    """
    if maximum_age is None:
        maximum_age = OLD_AGE

    # Get the current date and time to use for age comparison
    current_time = datetime.now()

    # Get the correct base output directory to search within
    output_directory = get_output_directory()

    # Gather all subdirectories in the output directory that is signed by their creation day and whose most recent
    # content is deemed too old
    old_subdirectories = [
        directory
        for directory in output_directory.glob("*")
        if directory.is_dir()
           and DATE_PATTERN.search(directory.name) is not None
           and directory_is_old(current_time=current_time, directory=directory, maximum_age=maximum_age)
    ]

    # Remove all directories that have been identified as being too old
    for directory in old_subdirectories:
        # Actually delete once it's confirmed that source won't be deleted
        shutil.rmtree(directory, ignore_errors=True)


def get_output_directory() -> pathlib.Path:
    """
    Returns:
        The path to where outputs should be written
    """
    directory = get_resource_directory() / "output"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def allocate_output_directory(purpose: str) -> pathlib.Path:
    """
    Create a directory where test output might be written

    Examples:
        >>> path = allocate_output_directory('template-export')
        >>> print(path)
        resources/output/2023-10-20/template-export-1697829800

    Args:
        purpose: Why the output directory is being created

    Returns:
        The path to the output directory
    """
    # Attempt to clean up
    purge_output()

    # Create directory based on today's date - this will help with later cleanup
    now = datetime.now().astimezone()
    date_path = get_output_directory() / now.strftime("%Y-%m-%d")

    # Create a directory related to the purpose of the directory
    #   Attach the timestamp to prevent conflicts
    output_name = f"{purpose.replace(' ', '_')}-{int(now.timestamp())}"
    output_path = date_path / output_name
    output_path.mkdir(parents=True)

    return output_path


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


def create_model_permutation_pairs(
    models: typing.Sequence[specification.Specification]
) -> typing.Sequence[typing.Tuple[specification.Specification, specification.Specification]]:
    permutations: typing.List[typing.Tuple[specification.Specification, specification.Specification]] = list()

    for left_model_index in range(len(models)):
        for right_model_index in range(len(models)):
            if left_model_index == right_model_index:
                continue

            permutations.append(
                (models[left_model_index], models[right_model_index])
            )

    return permutations


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
        self.check_equality_for_one(definition)

    def test_string_construction(self):
        text_params = json.dumps(self.params)

        definition = self.get_model_to_construct().create(text_params)

        self.make_assertion_for_single_definition(self, self.params, definition)
        self.check_equality_for_one(definition)

    def test_bytes_construction(self):
        bytes_params = json.dumps(self.params).encode()

        definition = self.get_model_to_construct().create(bytes_params)

        self.make_assertion_for_single_definition(self, self.params, definition)
        self.check_equality_for_one(definition)

    def test_byte_buffer_construction(self):
        buffer = io.BytesIO()
        buffer.write(json.dumps(self.params).encode())
        buffer.seek(0)

        definition = self.get_model_to_construct().create(buffer)

        self.make_assertion_for_single_definition(self, self.params, definition)
        self.check_equality_for_one(definition)

    def test_string_buffer_construction(self):
        buffer = io.StringIO()
        buffer.write(json.dumps(self.params))
        buffer.seek(0)

        definition = self.get_model_to_construct().create(buffer)

        self.make_assertion_for_single_definition(self, self.params, definition)
        self.check_equality_for_one(definition)

    def test_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.param_list)

        self.make_assertions_for_multiple_definitions(self, definitions)

    def test_multiple_string_construction(self):
        text_params = json.dumps(self.param_list, indent=4)

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

    @abc.abstractmethod
    def test_extract_fields(self):
        pass

    @abc.abstractmethod
    def check_equality_for_one(self, model: specification.Specification):
        pass

    @abc.abstractmethod
    def check_equality_among_many(self, models: typing.Sequence[specification.Specification]):
        pass

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
            test.check_equality_for_one(definition)
            parameter_index += 1

        test.check_equality_among_many(definitions)

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
        self.check_equality_for_one(definition)

    def test_full_object_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.full_object_parameter_list)

        self.make_assertions_for_multiple_definitions(self, definitions, self.full_object_parameter_list)

    def test_partial_object_basic_construction(self):
        definition = self.get_model_to_construct().create(self.partial_object_parameters)

        self.make_assertion_for_single_definition(self, self.partial_object_parameters, definition)
        self.check_equality_for_one(definition)

    def test_partial_object_multiple_basic_construction(self):

        definitions: typing.List[specification.Specification] = self.get_model_to_construct().create(self.partial_object_parameter_list)

        self.make_assertions_for_multiple_definitions(self, definitions, self.partial_object_parameter_list)
