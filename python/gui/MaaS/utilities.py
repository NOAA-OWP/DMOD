"""
A collection of helper functions and classes
"""

import os
import typing
import types
import importlib
import logging

from abc import ABC
from abc import abstractmethod

from django.http import HttpRequest
from rest_framework.request import Request

import redis


class ObjectWrapper(ABC):
    """
    Abstract class that allows for objects to be overridden dynamically at runtime

    The wrapper will have references to all attributes from the passed in object aside from those explicitly
    set to not override
    """
    # Attributes that shouldn't be overridden
    do_not_override = ('__module__', '__dict__', '__doc__')

    @abstractmethod
    def get_overridden_attributes(self) -> typing.Union[typing.List, typing.Tuple]:
        """
        Get attributes that should not be overridden if they exist

        Returns
        -------
        collection
            A collection of attribute names that should not be overridden
        """
        pass

    def __init__(self, object_to_wrap):
        # Store a reference to the object being wrapped
        self._wrapped_object = object_to_wrap

        # Collect all attributes that should be attached from the passed object
        attributes_to_add = [
            (key, value)
            for key, value in self._wrapped_object.__dict__.items()
            if key not in self.do_not_override and key not in self.get_overridden_attributes()
        ]

        # Add all approved attributes to this instance
        for attribute_name, attribute_value in attributes_to_add:
            setattr(self, attribute_name, attribute_value)


class RequestWrapper(ObjectWrapper):
    """
    Wraps the Django HttpRequest to ensure that GET and POST both return the correct values according to the
    method of the request instance
    """
    def get_overridden_attributes(self):
        """
        Don't override the GET and POST properties

        Returns
        -------
        tuple
            ("POST", "GET")
        """
        return "POST", "GET"

    def __init__(self, request: HttpRequest):
        # Make sure that the passed in object is an HttpRequest
        if not isinstance(request, HttpRequest) and not isinstance(request, Request):
            raise ValueError(
                "RequestWrapper must be created with an HttpRequest or DRF Request, not a {}".format(type(HttpRequest))
            )

        super().__init__(request)

    @property
    def POST(self):
        """
        Returns
        -------
        The correct collection of request parameters based on the requests method attribute
        """
        if self._wrapped_object.method == "POST":
            return self._wrapped_object.POST
        else:
            return self._wrapped_object.GET

    @property
    def GET(self):
        """
        Returns
        -------
        The correct collection of request parameters based on the requests method attribute
        """
        if self._wrapped_object.method == "POST":
            return self._wrapped_object.POST
        else:
            return self._wrapped_object.GET


def get_neighbor_modules(
        file_name: str,
        package_name: str,
        required_members_and_values: typing.Union[typing.Dict[str, typing.Any], typing.List[str]] = None,
        required_functions: typing.List[str] = None,
        required_member_types: typing.Dict[str, typing.TypeVar] = None,
        logger: logging.Logger = None
) -> typing.Dict[str, types.ModuleType]:
    """
    Gets references to all appropriate modules within the given package

    Parameters
    ----------
    file_name
        The path to a file within the package of interest

    package_name
        The name of the package that is of interest

    required_members_and_values
        A dictionary or list of members that the encountered module must contain

    required_functions
        A list of functions that must be within the encountered module

    required_member_types
        A mapping of strict types that a members must be (required members NOT within this collection can be of any type)

    logger
        The appropriate logger to write any log messages to

    Returns
    -------
    A mapping between the name of a module and its reference
    """
    if logger is None:
        logger = logging.getLogger()

    def is_valid(module: types.ModuleType) -> bool:
        """
        Checks to ensure that the passed in module adheres to the callers parameters

        Args:
            module:
                A reference to the module that needs to be examined
        Returns:
            Whether or not the module should be added to the collection
        """
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
    """
    Converts a string into a more human-readable and friendly form

    Parameters
    ----------
    words : str
        The string to be cleaned up

    Returns
    -------
    str
        A friendlier representation of the passed in word
    """
    split = words.strip().split("_")
    return " ".join(split).title()
