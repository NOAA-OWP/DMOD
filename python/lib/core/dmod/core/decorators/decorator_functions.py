"""
Defines common decorators
"""
import logging
import platform
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


def version_range(
    level: int = logging.WARNING,
    maximum_version: typing.Union[str, typing.Tuple[int, int, int]] = None,
    minimum_version: typing.Union[str, typing.Tuple[int, int, int]] = None,
    message: str = None,
    minimum_version_message: str = None,
    maximum_version_message: str = None,
    logger = None
):
    """
    Define a python version range for a function or class

    Include '{obj}' in a given message to reference the object

    Args:
        level: The log level for the message
        maximum_version: The maximum version to which this object is safe
        minimum_version: The minimum version to which this object is safe
        message: A general message to output
        minimum_version_message: A specific message for when current python version is less than the minimum
        maximum_version_message: A specific message for when the current python version is greater than the maximum
        logger: An optional logger
    """
    if not minimum_version and not maximum_version:
        raise ValueError("Cannot define a version range without any version bounds")

    if logger is None:
        logger = logging.getLogger()

    if not minimum_version:
        minimum_version = (3, 6, 0)
    elif isinstance(minimum_version, str):
        minimum_version = minimum_version.split(".")

    minimum_version = tuple(
        int(minimum_version[index]) if index < len(minimum_version) else 0
        for index in range(3)
    )

    if not maximum_version:
        maximum_version = (99, 99, 99)
    elif isinstance(maximum_version, str):
        maximum_version = maximum_version.split(".")

    maximum_version = tuple(
        int(maximum_version[index]) if index < len(maximum_version) else 99
        for index in range(3)
    )

    if message and not minimum_version_message:
        minimum_version_message = message
    elif not minimum_version_message:
        minimum_version_message = "{obj} "
        minimum_version_message += (
            f" is below the accepted version "
            f"(minimum={'.'.join(str(version_number) for version_number in minimum_version)}). "
            f"Functionality may not perform as expected."
        )

    if message and not maximum_version_message:
        maximum_version_message = message
    elif not maximum_version_message:
        maximum_version_message = "{obj} "
        maximum_version_message += (
            f" is above the accepted version range "
            f"(maximum={'.'.join(str(version_number) for version_number in maximum_version)}). "
            f"Functionality may not perform as expected."
        )

    def alert_if_outside_version_bounds(function):
        """
        Raise an alert if the function was defined in a version of python outside the scope of the version bounds

        Args:
            function: The object being defined

        Returns:
            The object that was defined
        """
        @wraps(function)
        def wrapper(*args, **kwargs):
            current_python_version = tuple(int(value) for value in platform.python_version_tuple())

            if current_python_version < minimum_version:
                if level == logging.ERROR:
                    raise AttributeError(minimum_version_message.format(obj=str(function)))
                logger.log(level=level, msg=minimum_version_message.format(obj=str(function)))

            if current_python_version > maximum_version:
                if level == logging.ERROR:
                    raise AttributeError(maximum_version_message.format(obj=str(function)))
                logger.log(level=level, msg=maximum_version_message.format(obj=str(function)))

            return function(*args, **kwargs)
        return wrapper

    return alert_if_outside_version_bounds


def deprecated(deprecation_message: str):
    def function_to_deprecate(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):
            warn(deprecation_message, DeprecationWarning)
            return fn(*args, **kwargs)

        return wrapper

    return function_to_deprecate
