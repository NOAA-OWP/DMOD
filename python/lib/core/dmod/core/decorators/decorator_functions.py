"""
Defines common decorators
"""
import typing
from warnings import warn
from functools import wraps

from .decorator_constants import *


def is_a(decorator_name: str):
    """
    Adds a function to a function that indicates if a function is a certain type of decorator

    This enables checks like 'initializer.is_a(function)` in order to find if a function is an initializer

    Args:
        decorator_name: The name of the decorator that indicates that the function is a decorated version

    Returns:
        A function with an inner function that indicates that a function is a member of the first function
    """
    def checker(function: typing.Callable):
        """
        Checks to make sure if the function has been decorated with the required attribute and its value is true

        Args:
            function: The function to check

        Returns:
            Whether the given function is has been decorated as desired
        """
        return hasattr(function, decorator_name) and getattr(function, decorator_name)

    def add_checker(function: typing.Callable):
        """
        Adds the checker function to the given function

        Args:
            function: The function to add 'checker' to

        Returns:
            The function with 'checker' added to it as 'is_a'
        """
        setattr(function, "is_a", checker)
        return function

    return add_checker


@is_a(INITIALIZER_ATTRIBUTE)
def initializer(function):
    """
    Adds an attribute to a function indicating that it can be used as an 'initializer' within its context

    Args:
        function: The function to add the attribute to

    Returns:
        The function with the "initializer" attribute
    """
    if not hasattr(function, INITIALIZER_ATTRIBUTE):
        setattr(function, INITIALIZER_ATTRIBUTE, True)
    return function


@is_a(ADDITIONAL_PARAMETER_ATTRIBUTE)
def additional_parameter(function):
    """
    Adds an attribute to a function indicating that it produces an additional keyword argument to be used
    within its context

    Args:
        function: The function to add the attribute to

    Returns:
        The function with the "additional_parameter" attribute
    """
    if not hasattr(function, ADDITIONAL_PARAMETER_ATTRIBUTE):
        setattr(function, ADDITIONAL_PARAMETER_ATTRIBUTE, True)
    return function


def describe(description: str):
    """
    Adds a description to an object
    """
    def add_description(obj):
        setattr(obj, DESCRIPTION_ATTRIBUTE, description)
        return obj

    return add_description


def deprecated(deprecation_message: str):
    def function_to_deprecate(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):
            warn(deprecation_message, DeprecationWarning)
            return fn(*args, **kwargs)

        return wrapper

    return function_to_deprecate


