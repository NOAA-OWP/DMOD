#!/usr/bin/env python

import os
import typing
import types
import importlib
import logging


def get_neighbor_modules(
        file_name: str,
        package_name: str,
        required_members_and_values: typing.Union[typing.Dict[str, typing.Any], typing.List[str]] = None,
        required_functions: typing.List[str] = None,
        required_member_types: typing.Dict[str, typing.TypeVar] = None,
        logger: logging.Logger = None
) -> typing.Dict[str, types.ModuleType]:
    if logger is None:
        logger = logging.getLogger()

    def is_valid(module: types.ModuleType) -> bool:
        valid = True

        if required_members_and_values:
            if isinstance(required_members_and_values, dict):
                missing_members = [
                    member
                    for member, value in required_members_and_values.items()
                    if not hasattr(module, member)
                       or getattr(module, member) != value
                ]
            else:
                missing_members = [
                    member
                    for member in required_members_and_values
                    if not hasattr(module, member)
                ]
            valid = len(missing_members) == 0

        if valid and required_member_types:
            wrong_types = [
                member
                for member, member_type in required_member_types.items()
                if not hasattr(module, member) or
                   not isinstance(getattr(module, member), member_type)
            ]
            valid = len(wrong_types) == 0

        if valid and required_functions:
            missing_functions = [
                func
                for func in required_functions
                if not hasattr(module, func)
                   or not isinstance(getattr(module, func), types.FunctionType)
            ]
            valid = len(missing_functions) == 0

        return valid

    modules: typing.Dict[str, types.ModuleType] = dict()

    this_filename = os.path.basename(file_name)
    directory = os.path.dirname(file_name)
    files = [
        name.replace(".py", "")
        for name in os.listdir(directory)
        if name.endswith(".py")
           and name != this_filename
           and not name.startswith("_")
    ]
    module_names = [package_name + "." + name for name in files]

    for file_name, module_name in zip(files, module_names):
        try:
            module = importlib.import_module(module_name)
            if is_valid(module):
                modules[file_name] = module
                logger.debug("{} loaded as a dynamic module".format(file_name))
            else:
                print("{} is not a valid dynamic module and could not be loaded".format(file_name))
        except ImportError as error:
            logging.error(
                "The {} module could not be loaded and bound to {} because of {}".format(
                    file_name,
                    module_name,
                    error
                )
            )

    return modules


def humanize(words: str) -> str:
    split = words.split("_")
    return " ".join(split).title()
