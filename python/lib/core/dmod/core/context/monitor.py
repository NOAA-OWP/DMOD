"""
Provides a mechanism for tracking the execution of processes and their consumption of shared objects
"""
from __future__ import annotations

import enum
import os
import typing
import threading
import queue
import logging

from concurrent import futures
from datetime import timedelta
from time import sleep

from .base import T
from .base import ObjectManagerScope
from ..common.helper_functions import is_float_string
from ..common.protocols import LoggerProtocol
from ..common.helper_functions import parse_duration

Seconds = typing.Union[float, int]
"""Alias to indicate that the value is supposed to be seconds represented by a floating point number"""

SHORT_TIMEOUT_THRESHOLD: typing.Final[Seconds] = timedelta(seconds=10).seconds
"""The amount of time considered dangerously short for the monitor timeout in seconds"""


SECONDS_TO_WAIT_ON_KILL: typing.Final[Seconds] = 15
"""The number of seconds to wait for threads to terminate when the monitor is killed"""


def get_default_monitor_timeout() -> Seconds:
    """
    Determine how long the FutureMonitor should wait for an update before it decides that it has been abandoned

    Returns:
        The number of seconds a FutureMonitor should wait if not told otherwise
    """
    configured_monitor_timeout = os.environ.get("FUTURE_MONITOR_TIMEOUT")

    if configured_monitor_timeout:
        configured_monitor_timeout = configured_monitor_timeout.strip()

        if is_float_string(configured_monitor_timeout):
            return float(configured_monitor_timeout)

        monitor_timeout = parse_duration(configured_monitor_timeout)
        if monitor_timeout.total_seconds() < 1:
            raise ValueError(
                "The 'FUTURE_MONITOR_TIMEOUT' environment variable is invalid. "
                f"It must be at least 1 second but {monitor_timeout.total_seconds()} seconds was given."
            )

        return monitor_timeout.total_seconds()

    # Default to 4 minutes if not configured. Five minutes should be long enough to detect a lack of writing,
    # but short enough that the monitor doesn't live for too long
    return timedelta(minutes=4).total_seconds()


DEFAULT_MONITOR_TIMEOUT: typing.Final[Seconds] = get_default_monitor_timeout()
"""The default amount of time to wait for an update within a future monitor in seconds"""


class MonitorSignal(enum.Enum):
    """
    Signals that a monitor may receive to alter its behavior outside the scope of a message
    """
    STOP = enum.auto()
    """Indicates that the monitor should stop"""
    PING = enum.auto()
    """Indicates that the timer used to find something to check should be reset"""
    KILL = enum.auto()
    """Indicates that the monitor and the processes it monitors should be forcefully killed immediately"""

    @classmethod
    def values(cls) -> typing.List[MonitorSignal]:
        """
        All MonitorSignal values in a representation that makes it easy to check for membership without errors
        """
        return list(cls)


class FutureMonitor:
    """
    Iterates over future objects to see when it is ok to end the extended scope for shared values
    """
    _DEFAULT_POLL_INTERVAL: float = 1.0
    """The number of seconds to wait before polling for the internal queue"""

    @property
    def class_name(self) -> str:
        """
        A helpful property used to get the name of the current class
        """
        return self.__class__.__name__

    def __init__(
        self,
        callback: typing.Callable[[T], typing.Any] = None,
        on_error: typing.Callable[[BaseException], typing.Any] = None,
        timeout: typing.Union[Seconds, timedelta] = None,
        poll_interval: typing.Union[float, timedelta] = None,
        logger: LoggerProtocol = None
    ):
        if not timeout:
            timeout = DEFAULT_MONITOR_TIMEOUT
        elif isinstance(timeout, timedelta):
            timeout = timeout.total_seconds()

        self._queue: queue.Queue[futures.Future] = queue.Queue()
        self.__size: int = 0
        self.__scopes: typing.List[typing.Tuple[ObjectManagerScope, futures.Future]] = []
        """A list of scopes and the task that marks them as complete"""

        self._callback = callback
        self._on_error = on_error
        self._timeout = timeout
        self.__thread: typing.Optional[threading.Thread] = None
        self.__lock: threading.RLock = threading.RLock()
        self.__killed: bool = False
        self.__stopping: bool = False
        self.__logger: LoggerProtocol = logger or logging.getLogger()

        if poll_interval is None:
            poll_interval = self._DEFAULT_POLL_INTERVAL
        elif isinstance(poll_interval, timedelta):
            poll_interval = poll_interval.total_seconds()
        elif not isinstance(poll_interval, (int, float)):
            raise TypeError(
                f"Cannot set the poll interval for a {self.class_name} to {poll_interval} - "
                f"it must be a float, integer, or timedelta"
            )

        self.__poll_interval = float(poll_interval)

        if self._timeout < SHORT_TIMEOUT_THRESHOLD:
            self.logger.warning(
                f"A timeout of {self._timeout} seconds is very low. "
                f"There is a heightened risk of timing out while transfering objects"
            )

    @property
    def monitor_should_be_killed(self) -> bool:
        """
        Whether the monitor should be stopped dead in its tracks
        """
        with self.__lock:
            return self.__killed

    @property
    def accepting_futures(self) -> bool:
        """
        Whether the monitor is accepting new things to watch
        """
        with self.__lock:
            # This should be accepting new futures to watch if there is a running thread, its not in a kill state,
            # and its not in the middle of stopping
            has_running_thread = self.__thread and self.__thread.is_alive()
            return has_running_thread and not self.monitor_should_be_killed and not self.__stopping

    @property
    def logger(self) -> LoggerProtocol:
        return self.__logger

    @logger.setter
    def logger(self, logger: LoggerProtocol) -> None:
        self.__logger = logger

    @property
    def size(self) -> int:
        return self.__size

    def __len__(self):
        return self.size

    @property
    def __should_be_monitoring(self) -> bool:
        """
        Whether the monitor should still be polling

        This should monitor if it's either accepting items to monitor or it has items left to iterate through
        """
        with self.__lock:
            return self.accepting_futures or self._queue.qsize() != 0

    def _monitor(self) -> bool:
        """
        Loop through the job results in the queue and delete them when processing has completed

        Returns:
            True if the function ended with no issues
        """
        monitoring_succeeded: bool = True

        while self.__should_be_monitoring:
            try:
                # Block to check if the loop should be exitted based on a current kill state
                with self.__lock:
                    if self.monitor_should_be_killed:
                        monitoring_succeeded = False
                        break

                    future_result: typing.Union[futures.Future, object] = self._queue.get(
                        timeout=self._timeout
                    )
                    self.__size -= 1

                if future_result in MonitorSignal.values():
                    if future_result == MonitorSignal.KILL:
                        monitoring_succeeded = False
                        self.__killed = True
                        break

                    if future_result == MonitorSignal.STOP:
                        self.__stopping = True

                    continue

                # This is just junk if it isn't a job result, so acknowledge it and move to the next item
                if not isinstance(future_result, futures.Future):
                    self.logger.error(
                        f"Found an invalid value in a {self.class_name}:"
                        f"{future_result} must be either a future or one of "
                        f"{', '.join(str(value) for value in MonitorSignal)}, "
                        f"but received a {type(future_result)}"
                    )
                    continue

                # If the process is done, fetch the result, call the callback if it didn't error,
                #   record the error if it did, and clean up any associated scope information
                if future_result.done():
                    scope = self.find_scope(future_result)

                    try:
                        value = future_result.result()
                        if self._callback:
                            try:
                                self._callback(value)
                            except BaseException as e:
                                self.logger.error(
                                    f"Encountered an error when executing the callback "
                                    f"'{self._callback.__qualname__}' with a process result in a {self.class_name}",
                                    exc_info=e
                                )
                    except BaseException as e:
                        # An error here indicates that the operation that spawned the Future threw an exception.
                        #   This will record the error from within that operation instead of breaking the loop
                        if scope:
                            self.logger.error(f"Encountered error within the {scope} scope:")

                        self.logger.error(msg=str(e), exc_info=e)

                        if scope:
                            # Add information about the scope to help identify what the operation failed on
                            self.logger.error(f"Scope '{scope.name}' created at:{os.linesep}{scope.started_at}")

                    # Failure or not, we want to remove any sort of scope information
                    self.end_scope(future_result=future_result)
                else:
                    # Otherwise put the process data back in the queue to check again later
                    self._queue.put_nowait(future_result)
                    self.__size += 1
            except queue.Empty:
                # Receiving the empty exception here means that it's been a while since anything was added,
                # meaning that it might be left hanging after other operations have ended. End everything here to
                # make sure there aren't orphanned operations
                self.logger.warning(f"A {self.class_name} is no longer being written to. Ending monitoring")
                monitoring_succeeded = False
                break
            except BaseException as exception:
                self.logger.error(msg="Error Encountered while monitoring shared values", exc_info=exception)
                monitoring_succeeded = False
                break

            # Wait a little bit before polling again to allow for work to continue
            sleep(self.__poll_interval)

        self.__cleanup()
        return monitoring_succeeded

    def find_scope(self, future_result: futures.Future) -> typing.Optional[ObjectManagerScope]:
        """
        Find the scope that belongs with the given output

        Args:
            future_result: The future result of the given scope

        Returns:
            A scope that belongs to the given job
        """
        with self.__lock:
            for scope, result in self.__scopes:
                if result == future_result:
                    return scope

        return None

    def end_scope(self, future_result: futures.Future):
        """
        Remove the reference to the scope and set it up for destruction

        Args:
            future_result: The Future result that belongs to a scope
        """
        with self.__lock:
            for index, (scope, result) in enumerate(self.__scopes):
                if result == future_result:
                    self.__scopes.pop(index)
                    scope.end_scope()
                    break

    def start(self):
        """
        Start monitoring
        """
        self.logger.info("Attempting to start a monitoring thread...")

        if self.monitor_should_be_killed:
            message = (f"Cannot start monitoring through {self.__class__.__name__} - "
                       f"this instance has been forcibly killed")
            self.logger.error(message)
            raise RuntimeError(message)

        with self.__lock:
            if self.__thread is not None and self.__thread.is_alive():
                self.logger.warning(f"This {self.__class__.__name__} instance is already monitoring")
                return

            self.__thread = threading.Thread(target=self._monitor)

            self.logger.debug("Starting monitoring thread...")
            self.__thread.start()
            self.logger.debug("The monitoring thread has started")

    def stop(self):
        """
        Stop monitoring processes and wait for them to complete
        """
        if not self.__thread:
            return

        if self.__thread.is_alive():
            self.__stopping = True
            self.add(None, MonitorSignal.STOP)

        self.__thread.join()
        old_thread = self.__thread
        self.__thread = None
        del old_thread

        self.__stopping = False

    def kill(self, wait_seconds: float = None):
        """
        Cease all operations immediately

        Args:
            wait_seconds: The number of seconds to wait
        """
        self.__killed = True
        self.__size = 0

        if not self.__thread:
            return

        if self.__thread.is_alive():
            if not isinstance(wait_seconds, (float, int)):
                wait_seconds = SECONDS_TO_WAIT_ON_KILL

            self.add(None, MonitorSignal.KILL)
            self.logger.error(
                f"Killing {self.class_name} #{id(self)}. Waiting {wait_seconds} seconds for the thread to stop"
            )
            self.__thread.join(wait_seconds)

        old_thread = self.__thread
        self.__thread = None
        del old_thread
        self.logger.error(
            f"{self.class_name} #{id(self)} has been killed."
        )

    def add(self, scope: typing.Optional[ObjectManagerScope], value: typing.Union[futures.Future, object]):
        """
        Add a process result to monitor

        Args:
            scope: The scope that the result is attributed to
            value: The result of the process using the scope
        """
        if not self.__thread or not self.__thread.is_alive():
            self.logger.debug(f"No thread is running in {self}.")
            self.start()
            self.logger.debug(f"Started monitoring in {self}")

        with self.__lock:
            try:
                self.logger.debug(f"Adding a process to the queue for a {self.class_name}...")
                self._queue.put_nowait(value)
                self.__size += 1
                self.logger.debug(f"Added a process to the queue for a {self.class_name}.")
                if isinstance(scope, ObjectManagerScope):
                    self.__scopes.append((scope, value))
            except:
                self.logger.error(f"Failed to add a process to a {self.class_name}")

    def __cleanup(self):
        """
        Remove everything associated with a completed monitoring operation
        """
        with self.__lock:
            while not self._queue.empty():
                try:
                    entry = self._queue.get()
                    if isinstance(entry, futures.Future) and entry.running():
                        entry.cancel()
                except queue.Empty:
                    pass
            self._queue = queue.Queue()
            self.__size = 0
            self.__scopes.clear()

    def __str__(self):
        return f"{self.__class__.__name__}: Monitoring {self.size} Items"

    def __repr__(self):
        return self.__str__()
