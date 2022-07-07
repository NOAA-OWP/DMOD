#!/usr/bin/env python3
import os
import pathlib


def get_resource_directory() -> pathlib.Path:
    """
    Returns:
        The path to a directory containing non-code related files
    """
    relative_path = pathlib.Path(os.path.join(os.path.dirname(__file__), 'resources'))
    return relative_path.absolute()


def get_resource_path(resource_name: str) -> pathlib.Path:
    for current_directory, contained_directories, contained_files in os.walk(get_resource_directory()):
        for contained_file in contained_files:
            if resource_name == contained_file:
                return pathlib.Path(os.path.join(current_directory, contained_file)).absolute()

            full_name = os.path.join(current_directory, contained_file)

            if full_name.endswith(resource_name):
                return pathlib.Path(full_name).absolute()

            absolute_full_name = os.path.join(*pathlib.Path(full_name).absolute().parts)

            if absolute_full_name.endswith(resource_name):
                return pathlib.Path(absolute_full_name)
    raise KeyError(f"There are no resources named '{resource_name}'")


RESOURCE_DIRECTORY = get_resource_directory()
EPSILON = 0.00001
