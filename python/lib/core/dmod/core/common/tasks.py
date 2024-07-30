"""
Provides helper functions for asynchronous tasks
"""
import typing
import logging
import inspect
import asyncio

from .helper_functions import get_current_function_name

DEFAULT_TASK_WAIT_SECONDS = 2
"""
The default amount of time to wait on an asynchronous task to finish. Controls the amount of time to wait when
polling for completion. Increase to poll less frequently and decrease to poll more frequently
"""

DEFAULT_MAXIMUM_POLLS = 5
"""
The maximum amount of attempts to wait on a task to finish.

A task may not finish within the given time, so this lets the function extend its waiting period while making sure
that it completes without taking too much time. Increase to poll more times (useful when you poll frequently on
possibly long running tasks) and decrease to exit without completion sooner
"""

TASK_MESSAGE = typing.Union[str, typing.Callable[[asyncio.Task], typing.Union[typing.Coroutine, str]]]
"""
Either a string or a function that will generate a string that will be logged in relation to an asynchronous task
"""

TASK_EXCEPTION_MESSAGE = typing.Union[
    str,
    typing.Callable[
        [asyncio.Task, typing.Optional[BaseException]],
        typing.Union[
            typing.Coroutine,
            str
        ]
    ]
]
"""
Either a string or a function that will generate a string that will be logged as an exception message in relation
to an asynchronous task
"""


class CancelResults:
    """
    Typed results detailing whether a cancel operation was successful
    """
    def __init__(self, task_name: str, cancelled: bool, message: str = None):
        """
        Constructor

        Args:
            task_name: The name of the task
            cancelled: Whether the task was cancelled successfully
            message: Any accompanying message (usually with a failed cancel)
        """
        self.__task_name = task_name
        self.__cancelled = cancelled
        self.__message = message

    @property
    def task_name(self):
        """
        The name of the task
        """
        return self.__task_name

    @property
    def cancelled(self) -> bool:
        """
        Whether the task was cancelled successfully
        """
        return self.__cancelled

    @property
    def message(self) -> str:
        """
        Any accompanying message (usually with a failed cancel)
        """
        return self.__message


async def wait_on_task(task: asyncio.Task, wait_seconds: int = None, maximum_times_to_poll: int = None) -> bool:
    """
    Wait for a task to finish

    Will only wait a limited number of times before moving on

    Note: Setting maximum_times_to_poll to a number less than 1 will poll until the task has been marked as completed

    Args:
        task: The task to poll
        wait_seconds: The number of seconds to wait between polling
        maximum_times_to_poll: The maximum number of times to poll the running task

    Returns:
        Whether the task completed during or prior to the polling period
    """
    if not isinstance(wait_seconds, typing.SupportsInt):
        logging.warning(
            f"'{get_current_function_name(parent_name=True)}' did not supply a valid amount of seconds to "
            f"wait for polling. Defaulting to {DEFAULT_TASK_WAIT_SECONDS} seconds"
        )
        wait_seconds = DEFAULT_TASK_WAIT_SECONDS
    elif wait_seconds is None:
        wait_seconds = DEFAULT_TASK_WAIT_SECONDS

    if not isinstance(maximum_times_to_poll, typing.SupportsInt):
        logging.warning(
            f"'{get_current_function_name(parent_name=True)}' did not supply a valid number of times to poll. "
            f"Defaulting to {DEFAULT_MAXIMUM_POLLS}"
        )
        maximum_times_to_poll = DEFAULT_MAXIMUM_POLLS
    elif maximum_times_to_poll is None:
        maximum_times_to_poll = DEFAULT_MAXIMUM_POLLS

    # Poll the task until it is deemed completed
    # Just move on if it takes too long
    wait_count = 0
    while not task.done() and (wait_count < maximum_times_to_poll or maximum_times_to_poll < 0):
        # Wait for the task to finish just in case it has its own asyncio sleep within (possible for producers)
        await asyncio.sleep(wait_seconds)

        if maximum_times_to_poll > 0:
            wait_count += 1

    return task.done() or task.cancelled()


async def cancel_task(
    task: asyncio.Task,
    cancel_message: TASK_MESSAGE = None,
    incomplete_message: TASK_MESSAGE = None,
    cancel_failed_message: TASK_MESSAGE = None
) -> CancelResults:
    """
    Attempt to cancel a specific task

    Args:
        task: The task to cancel
        cancel_message: A message or function to create a message to report when cancelling a task
        incomplete_message: A message or function to generate a message for when a task could not be properly canceled in time
        cancel_failed_message: A message to report in an exception if an error is encountered when cancelling a task

    Returns:
        A description of the success of the cancellation
    """
    successfully_ended: bool = True
    task_name: str = task.get_name()
    message: typing.Optional[str] = None

    # Only try to cancel the task if it hasn't completed yet
    if not (task.done() or task.cancelled()):
        try:
            # Evaluate the cancel message if it's a function
            if cancel_message is None:
                cancel_message_for_task = f"Cancelling {task.get_name()}"
            elif inspect.iscoroutinefunction(cancel_message):
                cancel_message_for_task = await cancel_message(task)
            elif isinstance(cancel_message, typing.Callable):
                cancel_message_for_task = cancel_message(task)
            else:
                cancel_message_for_task = cancel_message

            task.cancel()

            completed = await wait_on_task(task)

            # Python 3.9+ lets you pass the message into cancel, but not 3.8, so we do this manually
            if task.cancelled():
                logging.debug(cancel_message_for_task)

            # Report an error and move on if the cancel function did not properly stop execution
            if not completed:
                # Evaluate the incomplete message if the given message is a function
                if incomplete_message is None:
                    task_incomplete_message = f"Could not cancel {task.get_name()} within the given amount of time"
                elif inspect.iscoroutinefunction(incomplete_message):
                    task_incomplete_message = await incomplete_message(task)
                elif inspect.isroutine(incomplete_message):
                    task_incomplete_message = incomplete_message(task)
                else:
                    task_incomplete_message = incomplete_message

                logging.error(task_incomplete_message)
                successfully_ended = task.cancelled()
                message = task_incomplete_message
        except BaseException as cancel_exception:
            if cancel_failed_message is None:
                cancel_failed_message = f"Failed to cancel an incomplete task: " \
                                        f"{task.get_name()}; {str(cancel_exception)}"
            elif inspect.iscoroutinefunction(cancel_failed_message):
                cancel_failed_message = await cancel_failed_message(task, cancel_exception)
            elif isinstance(cancel_failed_message, typing.Callable):
                cancel_failed_message = cancel_failed_message(task, cancel_exception)

            logging.error(cancel_failed_message, exc_info=cancel_exception)
            successfully_ended = False
            message = cancel_failed_message

        return CancelResults(task_name, successfully_ended, message)


async def cancel_tasks(
    tasks: typing.Iterable[asyncio.Task],
    cancel_message: TASK_MESSAGE = None,
    incomplete_message: TASK_MESSAGE = None,
    cancel_failed_message: TASK_MESSAGE = None
) -> typing.Tuple[CancelResults, ...]:
    """
    Attempt to cancel all passed in tasks

    Args:
        tasks: The tasks to cancel
        cancel_message: A message or function to create a message to report when cancelling a task
        incomplete_message: A message or function to generate a message for when a task could not be properly canceled in time
        cancel_failed_message: A message to report in an exception if an error is encountered when cancelling a task
    """
    cancellation_tasks: typing.List[typing.Coroutine[typing.Any, typing.Any, CancelResults]] = [
        cancel_task(
            task,
            incomplete_message,
            cancel_message,
            cancel_failed_message
        )
        for task in tasks
    ]
    results: typing.Tuple[CancelResults, ...] = await asyncio.gather(*cancellation_tasks)
    return results
