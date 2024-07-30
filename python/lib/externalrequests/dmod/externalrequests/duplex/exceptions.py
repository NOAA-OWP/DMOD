"""
Define common exceptions for duplex handlers
"""
import typing


class InitializationError(Exception):
    """
    Exception thrown when the initialization of a class was not performed
    """
    def __init__(self, klazz: typing.Any):
        if isinstance(klazz, str):
            name = klazz
        elif isinstance(klazz, type):
            name = klazz.__name__
        else:
            name = klazz.__class__.__name__

        message = f"{name} was not properly initialized. Make sure __init__ was called. __init__ is only called " \
                  f"automatically on the first parent class in the list."

        super().__init__(message)


class OperationComplete(BaseException):
    """
    Indicates that an operation has completed and that a cycle needs to stop
    """
