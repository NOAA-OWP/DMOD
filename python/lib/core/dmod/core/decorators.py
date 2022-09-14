"""
Defines common decorators
"""
import typing
import inspect

INITIALIZER_ATTRIBUTE = "initializer"
"""The name of the attribute stating that the owner should be used for initialization"""

ADDITIONAL_PARAMETER_ATTRIBUTE = "additional_parameter"
"""
The name of the attribute stating that the owner should be used to determine additional parameters for services 
to send to handlers
"""

SOCKET_HANDLER_ATTRIBUTE = "socket_handler"
"""
The name of the attribute stating that a service should be able to use the owner to consume new websocket connections
"""

MESSAGE_HANDLER_ATTRIBUTE = "message_handler"
"""
The name of the attribute stating that the owner can consume messages that come through a websocket
"""

PRODUCER_MESSAGE_HANDLER_ATTRIBUTE = "producer_handler"
"""
The name of the attribute stating that the owner can produce messages on its on and send results through a socket
"""

SERVER_MESSAGE_HANDLER_ATTRIBUTE = "server_handler"
"""
The name of the attribute stating the the owner should consume messages from a websocket server
"""

CLIENT_MESSAGE_HANDLER_ATTRIBUTE = "client_handler"
"""
The name of the attribute stating that the owner should consume messages from a websocket client
"""

MESSAGE_TYPE_ATTRIBUTE = "message_type"
"""
Attribute indicating what sort of message a socket handler should be able to consume
"""

MESSAGE_MEMBER_ATTRIBUTE = "message_member"

MESSAGE_MEMBER_KEY_ATTRIBUTE = 'json_key'

MESSAGE_MEMBER_MEMBER_ATTRIBUTE = 'member'

MESSAGE_MEMBER_DATA_TYPE_ATTRIBUTE = 'data_type'

MESSAGE_MEMBER_PATH_ATTRIBUTE = 'path'


def message_member(json_key: str, member: str, path: str = None, data_type: typing.Type = None, *args, **kwargs):
    """
    Flag an object as a member of an object that should be considered as an attribute that can be read off of a
    JSON document

    Args:
        json_key:
        member:
        path:
        data_type:
        *args:
        **kwargs:

    Returns:

    """

    def decorate_function(function):
        if not isinstance(function, property):
            raise ValueError(
                f"Only properties may be considered as message_members; this is a {type(function).__name__}"
            )

        setattr(function, MESSAGE_MEMBER_ATTRIBUTE, True)
        setattr(function, MESSAGE_MEMBER_KEY_ATTRIBUTE, json_key)
        setattr(function, MESSAGE_MEMBER_MEMBER_ATTRIBUTE, member)
        setattr(function, MESSAGE_MEMBER_PATH_ATTRIBUTE, path)
        setattr(function, MESSAGE_MEMBER_DATA_TYPE_ATTRIBUTE, data_type)

        for key, value in kwargs.items():
            setattr(function, key, value)

        return function

    return decorate_function


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


def server_message_handler(function: typing.Callable):
    """
    Indicates that the function should operate on messages from a server that it listens to

    Args:
        function: The function to decorate

    Returns:
        The function with an added flag
    """
    if not inspect.iscoroutinefunction(function):
        raise ValueError(
            f"A synchronous function was flagged as a message handler; only asynchronous functions "
            f"(marked as `async`) may be considered as message handlers."
        )

    if not hasattr(function, SERVER_MESSAGE_HANDLER_ATTRIBUTE):
        setattr(function, SERVER_MESSAGE_HANDLER_ATTRIBUTE, True)

    return function


def client_message_handler(function: typing.Callable):
    """
    Indicates that the function should operate on messages from a client that it listens to

    Args:
        function: The function to decorate

    Returns:
        The function with the added flag
    """
    if not inspect.iscoroutinefunction(function):
        raise ValueError(
            f"A synchronous function was flagged as a message handler; only asynchronous functions "
            f"(marked as `async`) may be considered as message handlers."
        )

    if not hasattr(function, CLIENT_MESSAGE_HANDLER_ATTRIBUTE):
        setattr(function, CLIENT_MESSAGE_HANDLER_ATTRIBUTE, True)

    return function


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
            f"An synchronous function was flagged as a message handler; only asynchronous functions "
            f"(marked as `async`) may be considered as message producers."
        )

    if not hasattr(function, PRODUCER_MESSAGE_HANDLER_ATTRIBUTE):
        setattr(function, PRODUCER_MESSAGE_HANDLER_ATTRIBUTE, True)

    return function


def socket_handler(*args, **kwargs):
    """
    Adds an attribute to a function indicating that it should be used to handle socket communication

    Args:
        function: The function to decorate

    Returns:
        The passed in function with updated metadata
    """

    def handler_with_attributes(function):
        """
        Add the attributed event type to the socket handler

        Args:
            **kwargs: key-value arguments to add to the object

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
