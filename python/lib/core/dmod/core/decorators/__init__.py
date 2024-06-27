"""
Provides functions and constants to provide common decorators
"""
import typing
import inspect

from .decorator_constants import *

from .decorator_functions import initializer
from .decorator_functions import additional_parameter
from .decorator_functions import describe
from .decorator_functions import deprecated
from .decorator_functions import version_range

from .message_handlers import socket_handler
from .message_handlers import client_message_handler
from .message_handlers import server_message_handler
from .message_handlers import producer_message_handler


def function_has_decorator(
    function_to_check: object,
    decorator_function: typing.Callable,
    fail_if_not_is_a: bool = None
) -> bool:
    """
    Check to see if the function to check has been decorated with the given decorator function

    Set `fail_if_not_is_a` to `True` to throw an error if the decorator function is missing the expected 'is_a'
    function. Otherwise 'False` will be returned

    Args:
        function_to_check: The function to check if decorated
        decorator_function: The function that might have decorated the first
        fail_if_not_is_a: Whether to throw an error if the decorator is missing the `has_a` function

    Returns:
        Whether the given function has been decorated with the given decorator
    """
    fail_if_not_is_a = bool(fail_if_not_is_a)

    if function_to_check is None or function_to_check is None:
        return False

    if not isinstance(function_to_check, typing.Callable) and not inspect.iscoroutinefunction(function_to_check):
        raise ValueError(f"Cannot check if {str(function_to_check)} is a decorator - it isn't a callable")

    if not isinstance(decorator_function, typing.Callable) and not inspect.isawaitable(decorator_function):
        raise ValueError(f"Cannot check if function is decorated - {str(decorator_function)} is not a decorator")

    checker: typing.Optional[typing.Callable[[typing.Callable], bool]] = getattr(decorator_function, "is_a", None)

    if not checker and fail_if_not_is_a:
        raise ValueError(
            f"Cannot check if '{str(function_to_check)}' has been decorated with '{str(decorator_function)}; "
            f"'{str(decorator_function)}' is missing the `is_a` function"
        )
    if not checker:
        return False

    return checker(function_to_check)


def find_functions_by_decorator(
    source: object,
    decorator: typing.Callable,
    predicate: typing.Callable[[typing.Callable], bool] = None
) -> typing.Sequence[typing.Callable]:
    """
    Searches a source object for functions that match a given decorator a passes a predicate (if given)

    Only functions with decorators themselves decorated by 'is_a' will be found

    Args:
        source: An object to search
        decorator: The decorator function to look for
        predicate: A function to further filter results

    Returns:
        A list of all functions on the object (synchronous and asynchronous) that are decorated with the given decorator
    """
    def default_predicate(*args, **kwargs):
        """
        Returns:
            True
        """
        return True

    # The predicate should be ignored if none is given, so just assign it to a function that returns True
    if not predicate:
        predicate = default_predicate

    def has_decorator(member: object) -> bool:
        """
        Checks to see if the member has the given decorator and fits the given predicate

        Args:
            member: The member to check

        Returns:
            Whether the given member has been decorated with the correct decorator and
        """
        # We're only interested in objects that can be called, so go ahead and ignore anything that doesn't count,
        # like `__dict__`
        if not inspect.isroutine(member) and not inspect.iscoroutinefunction(member):
            return False

        is_candidate = function_has_decorator(member, decorator)

        return is_candidate and predicate(member)

    functions_with_decorator = [
        function
        for name, function in inspect.getmembers(source, predicate=has_decorator)
    ]

    return functions_with_decorator


def find_functions_by_attributes(
    source: object,
    decorator_name: str,
    required_attributes: typing.Collection[str] = None,
    excluded_attributes: typing.Collection[str] = None
) -> typing.Dict[str, typing.Callable]:
    """
    Gets all functions within this instance bearing the given decorator, with all required attributes and missing
    all excluded attributes.

    Args:
        source: The object to check for attributes
        decorator_name: The name of the primary attribute on functions to look for
        required_attributes: A list of additional attributes that must be on the function to be included
        excluded_attributes: All attributes that indicate a function to ignore

    Returns:
        A dictionary containing all found functions mapping the name of the function to the function itself
    """
    if required_attributes is None:
        required_attributes = list()
    elif not isinstance(required_attributes, typing.Sequence) or isinstance(required_attributes, (bytes, str)):
        required_attributes = [required_attributes]

    if excluded_attributes is None:
        excluded_attributes = list()
    elif not isinstance(excluded_attributes, typing.Sequence) or isinstance(excluded_attributes, (bytes, str)):
        required_attributes = [required_attributes]

    def is_method_and_has_decorator(member) -> bool:
        """
        A filter dictating whether an encountered member is a method with a specific decorator and required
        attributes

        Args:
            member: The instance member to check

        Returns:
            True if the encountered member meets the specified requirements
        """
        has_decorator = hasattr(member, decorator_name)
        is_method = inspect.ismethod(member) or inspect.iscoroutinefunction(member)

        for required_attribute in required_attributes:
            if not hasattr(member, required_attribute):
                return False

        for excluded_attribute in excluded_attributes:
            if hasattr(member, excluded_attribute):
                return False

        return has_decorator and is_method

    # Collect all functions within this class that have the correct decorator and meet the attribute requirements
    functions: typing.Dict[str, typing.Callable] = {
        function_name: function
        for function_name, function in inspect.getmembers(source, predicate=is_method_and_has_decorator)
    }

    return functions


def decorate(**kwargs):
    """
    Provides a function that will decorate another function with an arbitrary collection of attributes

    NOTE: It is advised that attribute names be stored as a constant in a central location for referencing -
    this will avoid issues where typing or casing are variable, such as giving 'Action' instead of 'action' or
    'actions' instead of 'action'

    Args:
        **kwargs: Key value pairs indicating what attributes to add

    Returns:
        A function that will decorate a function with the given key-value pairs
    """
    def add_attributes(function: typing.Callable):
        """
        Add all attributes to the passed function

        Args:
            function: A function to decorate

        Returns:
            The decorated function
        """
        if len(kwargs) == 0:
            raise ValueError(f"No attributes were passed to add to {function.__name__}")

        for attribute_name, attribute_value in kwargs:
            setattr(function, attribute_name, attribute_value)

        return function

    return add_attributes
