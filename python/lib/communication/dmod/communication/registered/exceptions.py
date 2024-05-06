"""
Provides specialized exceptions for registered handlers and socket interfaces
"""


class MissingSessionException(Exception):
    """
    Represents an exception that occurs when attempting to access session data that has not been initialized yet
    """
    def __init__(self, message: str = None):
        if message is None:
            message = "A session has not been initialized for this websocket"
        super().__init__(message)


class MissingHandlerException(Exception):
    """
    An exception for when a request handler does not exist
    """


class RegistrationError(Exception):
    """
    An error that occurs during registration
    """
