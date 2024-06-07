"""
Common type hinting protocols to use throughout the code base
"""
from __future__ import annotations

import concurrent.futures
import typing

from typing_extensions import Self

T = typing.TypeVar("T")
_CLASS_TYPE = typing.TypeVar("_CLASS_TYPE")

Message = typing.Union[Exception, str, dict]

@typing.runtime_checkable
class KeyedObjectProtocol(typing.Protocol):
    """
    Represents a class that defines its own key that defines its own uniqueness
    """
    @classmethod
    def get_key_fields(cls) -> typing.List[str]:
        """
        Get the list of all fields on the object that represent the parameters for uniqueness
        """

    def get_key_values(self) -> typing.Dict[str, typing.Any]:
        """
        Gets all values from the object representing the key
        """
        ...

    def matches(self, other: object) -> bool:
        ...


@typing.runtime_checkable
class CombinableObjectProtocol(typing.Protocol[_CLASS_TYPE]):
    """
    Represents a class that may be explicitly combined with another of its same type either through a class level
    'combine' function or through the '+' operator
    """
    @classmethod
    def combine(cls, first: _CLASS_TYPE, second: _CLASS_TYPE) -> _CLASS_TYPE:
        """
        Combines two instances of this class to form a brand new one
        """

    def __add__(self, other: _CLASS_TYPE) -> _CLASS_TYPE:
        ...


@typing.runtime_checkable
class DescribableProtocol(typing.Protocol):
    """
    Represents an object that has a 'description' attribute
    """
    description: str


@typing.runtime_checkable
class JobResultProtocol(typing.Protocol[T]):
    """
    Represents the value of an action that has not yet been completed
    """
    def cancel(self) -> bool:
        """
        Attempt to cancel the call. If the call is currently being executed or finished running and cannot be
        cancelled then the method will return False, otherwise the call will be cancelled and the method will
        return True.

        Returns:
            False if the call is being executed or is finished and can't be cancelled, returns False, otherwise True
        """

    def cancelled(self) -> bool:
        """
        True if the call was successfully cancelled
        """

    def running(self) -> bool:
        """
        True if the call is currently being executed and cannot be cancelled.
        """

    def done(self) -> bool:
        """
        True if the call was successfully cancelled or finished running.
        """

    def result(self, timeout: typing.Union[int, float] = None) -> T:
        """
        Return the value returned by the call. If the call hasn’t yet completed then this method will wait up to
        timeout seconds. If the call hasn’t completed in timeout seconds, then a concurrent.futures.TimeoutError
        will be raised. timeout can be an int or float. If timeout is not specified or None, there is no limit to the
        wait time.

        If the future is cancelled before completing then CancelledError will be raised.

        If the call raised, this method will raise the same exception.

        Args:
            timeout: The number of seconds to wait for a result

        Returns:
            The result of the call
        """

    def exception(self, timeout: typing.Union[int, float] = None) -> typing.Optional[BaseException]:
        """
        Return the exception raised by the call. If the call hasn’t yet completed then this method will wait up to
        timeout seconds. If the call hasn’t completed in timeout seconds, then a TimeoutError will
        be raised. timeout can be an int or float. If timeout is not specified or None, there is no limit to the wait
        time.

        If the future is cancelled before completing then CancelledError will be raised.

        If the call completed without raising, None is returned.

        Args:
            timeout: The number of seconds to wait

        Returns:
            An exception that was raised by the call, if one was raised, else None
        """

    def add_done_callback(self, fn: typing.Callable[[Self], typing.Any]):
        """
        Attaches the callable fn to the future. fn will be called, with the future as its only argument, when the
        job is cancelled or finishes running.

        Added callables are called in the order that they were added and are always called in a thread belonging to the
        process that added them. If the callable raises an Exception subclass, it will be logged and ignored. If the
        callable raises a BaseException subclass, the behavior is undefined.

        If the job has already completed or been cancelled, fn will be called immediately.

        Args:
            fn: The function to call when the job is done
        """


@typing.runtime_checkable
class JobLauncherProtocol(typing.Protocol):
    """
    Represents an object that may launch actions outside of the current thread and process
    """
    def submit(self, fn: typing.Callable, *args, **kwargs) -> JobResultProtocol:
        """
        Schedules the callable, fn, to be executed as fn(*args **kwargs) and returns a JobResultProtocol object
        representing the execution of the callable.

        Args:
            fn: The function to call
            *args: positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            A JobResultProtocol object representing the result of the function
        """

    def map(
        self,
        *iterables,
        timeout: typing.Union[int, float] = None,
        chunksize: int = 1
    ) -> typing.Iterable[JobResultProtocol]:
        """
        Similar to map(func, *iterables) except:

            - the iterables are collected immediately rather than lazily;

            - func is executed asynchronously and several calls to func may be made concurrently.

        The returned iterator raises a TimeoutError if __next__() is called and the result isn’t
        available after timeout seconds from the original call to JobLauncherProtocol.map(). timeout can be an int or
        a float. If timeout is not specified or None, there is no limit to the wait time.

        If a func call raises an exception, then that exception will be raised when its value is retrieved
        from the iterator.

        Args:
            *iterables: Iterables of positional arguments to feed to the function
            timeout: The number of seconds to wait for results before throwing an error
            chunksize: The number of functions to call in each batch if the launcher supports batching

        Returns:
            An iterable of results from the function
        """

    def __enter__(self):
        pass

    def __exit__(self):
        pass


@typing.runtime_checkable
class LoggerProtocol(typing.Protocol):
    """
    A protocol for a logger-like object
    """
    def info(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
        """

    def warning(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=1)
        """

    def warn(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=1)
        """

    def error(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.error("Houston, we have a %s", "major problem", exc_info=1)
        """

    def debug(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """

    def log(self, level, msg, *args, **kwargs):
        """
        Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=1)
        """


if typing.TYPE_CHECKING:
    from _typeshed.dbapi import DBAPIConnection
    from _typeshed.dbapi import DBAPICursor
    from _typeshed.dbapi import DBAPIColumnDescription
else:
    # The following are copied from `_typeshed.dbapi
    #   That library isn't always available at runtime, so this is here as a guard
    DBAPITypeCode: typing.TypeAlias = typing.Optional[typing.Any]

    # Strictly speaking, this should be a Sequence, but the type system does
    # not support fixed-length sequences.
    DBAPIColumnDescription: typing.TypeAlias = typing.Tuple[
        str,
        DBAPITypeCode,
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int],
        typing.Optional[int]
    ]


    @typing.runtime_checkable
    class DBAPIConnection(typing.Protocol):
        def close(self) -> object: ...
        def commit(self) -> object: ...
        # optional:
        # def rollback(self) -> Any: ...
        def cursor(self) -> DBAPICursor: ...


    @typing.runtime_checkable
    class DBAPICursor(typing.Protocol):
        @property
        def description(self) -> typing.Optional[typing.Sequence[DBAPIColumnDescription]]:
            return None

        @property
        def rowcount(self) -> int:
            return -1

        def close(self) -> object: ...
        def execute(self, __operation: str, __parameters: typing.Sequence[typing.Any] | typing.Mapping[str, typing.Any] = ...) -> object: ...
        def executemany(self, __operation: str, __seq_of_parameters: typing.Sequence[typing.Sequence[typing.Any]]) -> object: ...
        def fetchone(self) -> typing.Sequence[typing.Any] | None: ...
        def fetchmany(self, __size: int = ...) -> typing.Sequence[typing.Sequence[typing.Any]]: ...
        def fetchall(self) -> typing.Sequence[typing.Sequence[typing.Any]]: ...

        arraysize: int
        def setinputsizes(self, __sizes: typing.Sequence[DBAPITypeCode | int | None]) -> object: ...
        def setoutputsize(self, __size: int, __column: int = ...) -> object: ...