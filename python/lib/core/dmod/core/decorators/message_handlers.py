"""
Provides decorators pertaining specifically to message handling
"""
import typing
import inspect

from .decorator_functions import is_a
from .decorator_constants import *


@is_a(SERVER_MESSAGE_HANDLER_ATTRIBUTE)
def server_message_handler(action: str = None, message_type = None):
    """
    Indicates that the function should operate on messages from a server that it listens to

    Args:
        action: What sort of action this handler performs
        message_type: The type of message that this handler consumes

    Returns:
        The function with the added handler metadata
    """
    def set_server_handler_attributes(function: typing.Callable):
        if not inspect.iscoroutinefunction(function):
            raise ValueError(
                "A synchronous function was flagged as a message handler; only asynchronous functions "
                "(marked as `async`) may be considered as message handlers."
            )

        if not hasattr(function, SERVER_MESSAGE_HANDLER_ATTRIBUTE):
            setattr(function, SERVER_MESSAGE_HANDLER_ATTRIBUTE, True)

        if action and not hasattr(function, HANDLER_ACTION_ATTRIBUTE):
            setattr(function, HANDLER_ACTION_ATTRIBUTE, action)
        if message_type and not hasattr(function, MESSAGE_TYPE_ATTRIBUTE):
            setattr(function, MESSAGE_TYPE_ATTRIBUTE, message_type)

        return function

    return set_server_handler_attributes


@is_a(CLIENT_MESSAGE_HANDLER_ATTRIBUTE)
def client_message_handler(action: str = None, message_type = None):
    """
    Indicates that the function should operate on messages from a client that it listens to

    Args:
        action: What sort of action this handler performs
        message_type: The type of message that this handler consumes

    Returns:
        The function with the added handler metadata
    """
    def set_client_handler_attributes(function: typing.Callable):
        if not inspect.iscoroutinefunction(function):
            raise ValueError(
                "A synchronous function was flagged as a message handler; only asynchronous functions "
                "(marked as `async`) may be considered as message handlers."
            )

        if not hasattr(function, CLIENT_MESSAGE_HANDLER_ATTRIBUTE):
            setattr(function, CLIENT_MESSAGE_HANDLER_ATTRIBUTE, True)

        if not hasattr(function, HANDLER_ACTION_ATTRIBUTE):
            setattr(function, HANDLER_ACTION_ATTRIBUTE, action)
        if not hasattr(function, MESSAGE_TYPE_ATTRIBUTE):
            setattr(function, MESSAGE_TYPE_ATTRIBUTE, message_type)

        return function

    return set_client_handler_attributes


@is_a(PRODUCER_MESSAGE_HANDLER_ATTRIBUTE)
def producer_message_handler(function: typing.Callable):
    """
    Indicates that the function should operate on messages from a client that it listens to

    Args:
        function: The function to decorate

    Returns:
        The function with the added flag
    """
    if not inspect.iscoroutinefunction(function):
        raise ValueError(
            "An synchronous function was flagged as a message handler; only asynchronous functions "
            "(marked as `async`) may be considered as message producers."
        )

    if not hasattr(function, PRODUCER_MESSAGE_HANDLER_ATTRIBUTE):
        setattr(function, PRODUCER_MESSAGE_HANDLER_ATTRIBUTE, True)

    return function


@is_a(SOCKET_HANDLER_ATTRIBUTE)
def socket_handler(**kwargs):
    """
    Adds an attribute to a function indicating that it should be used to handle socket communication

    Args:
        **kwargs: key-value arguments to add to the object

    Returns:
        The passed in function with updated metadata
    """

    def handler_with_attributes(function: typing.Callable):
        """
        Add the attributed event type to the socket handler

        Args:
            function: The function to decorate

        Returns:
            The updated function with the specified attributes
        """
        if not hasattr(function, SOCKET_HANDLER_ATTRIBUTE):
            setattr(function, SOCKET_HANDLER_ATTRIBUTE, True)

        if MESSAGE_TYPE_ATTRIBUTE not in kwargs:
            raise ValueError(
                f"An attribute stating what sort of message should be assigned to this handler was no passed into a "
                f"variable named '{MESSAGE_TYPE_ATTRIBUTE}'. The given function cannot be flagged as a socket handler."
            )

        for key, value in kwargs.items():
            key = str(key)
            if not hasattr(function, key):
                setattr(function, key, value)

        return function

    return handler_with_attributes
