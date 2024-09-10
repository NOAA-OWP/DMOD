#!/usr/bin/env python3
"""
Listens to redis to identify messages indicating that an evaluation should be launched
"""
from __future__ import annotations

import traceback
import queue
import typing
import os
import sys
import multiprocessing
import json
import signal
import dataclasses
import threading

from argparse import ArgumentParser

import redis

from concurrent import futures
from functools import partial

import utilities
from dmod.metrics import CommunicatorGroup
from dmod.core.context import DMODObjectManager

from dmod.core.context import get_object_manager

import service
import worker
from service.service_logging import get_logger

from utilities.common import ErrorCounter
from utilities import streams

CT = typing.TypeVar("CT")
"""A type of object that may be cleaned up"""

EXCEPTION_LIMIT: typing.Final[int] = 10
"""
The maximum number of a specific type of error to catch before exiting. If an error occurs 11 times in rapid 
succession and the limit is 10, the runner should stop. If it only occurs 9 times it could be the result of something 
that this has no control over and may remain functional.
"""

SUCCESSFUL_EXIT: typing.Final[int] = 0
"""The exit code for a successful operation. `os.EX_OK` would be ideal, but that approach isn't portable"""

ERROR_EXIT: typing.Final[int] = 1
"""
The exit code when the runner halts because of an error. 1 is used since that is generally associated with the catch 
all error code.
"""


def get_concurrency_executor_type(**kwargs) -> typing.Callable[[], futures.Executor]:
    """
    Gets the class type that will be responsible for running evaluation jobs concurrently

    Returns:
        The type of executor that should be used to run the evaluation jobs
    """
    method = os.environ.get("EVALUATION_RUNNER_CONCURRENCY_METHOD", "multiprocessing")
    method = kwargs.pop("method", method)
    method = method.lower()

    if method == "threading":
        return partial(futures.ThreadPoolExecutor, **kwargs)

    return partial(futures.ProcessPoolExecutor, **kwargs)


def signal_handler(signum: int, frame):
    """
    Handles cleanup operations for the runner in case of an unexpected signal

    Args:
        signum: The type of signal currently being handled
        frame: The frame explaining where the code was when the signal was triggered
    """
    signal_description: str = signal.strsignal(signum).split(":")[0]
    service.error(f"Received external signal: {signal_description}")

    Cleanupable.cleanup_all()

    service.error("Now exiting...")
    sys.exit(signum)


class Arguments:
    """
    CLI Argument handler for the `runner`
    """
    def __init__(self, *args):
        self.__host: typing.Optional[str] = None
        self.__port: typing.Optional[str] = None
        self.__username: typing.Optional[str] = None
        self.__password: typing.Optional[str] = None
        self.__stream_name: typing.Optional[str] = None
        self.__group_name: typing.Optional[str] = None
        self.__db: int = 0
        self.__limit: typing.Optional[int] = None
        self.__parse_command_line(*args)

    @property
    def host(self) -> typing.Optional[str]:
        """
        The host of the redis instance
        """
        return self.__host

    @property
    def port(self) -> typing.Optional[int]:
        """
        The port through which to reach the redis instance
        """
        return self.__port

    @property
    def username(self) -> typing.Optional[str]:
        """
        The username of the redis instance
        """
        return self.__username

    @property
    def password(self) -> typing.Optional[str]:
        """
        The password of the redis instance
        """
        return self.__password

    @property
    def db(self) -> int:
        """
        The logical db for what database to use in the redis instance
        """
        return self.__db

    @property
    def stream_name(self) -> str:
        """
        The name of the redis stream to listen to
        """
        return self.__stream_name

    @property
    def group_name(self) -> str:
        """
        The name of the redis consumer group that will listen to the redis stream
        """
        return self.__group_name

    @property
    def limit(self) -> typing.Optional[int]:
        """
        The limit to the number of evaluations that may be run at once
        """
        return self.__limit

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Starts a series of processes that will listen and launch evaluations")

        parser.add_argument(
            '--redis-host',
            help='Set the host value for making Redis connections',
            dest='redis_host',
            default=None
        )

        parser.add_argument(
            '--redis-port',
            help='Set the port value for making Redis connections',
            dest='redis_port',
            default=None
        )

        parser.add_argument(
            '--redis-username',
            help='Set the username for making Redis connections',
            dest='redis_username',
            default=None
        )

        parser.add_argument(
            '--redis-pass',
            help='Set the password value for making Redis connections',
            dest='redis_pass',
            default=None
        )

        parser.add_argument(
            '--redis-db',
            help='Set the database value for making Redis connections',
            dest='redis_db',
            default=None
        )

        parser.add_argument(
            "--limit",
            help="The number of evaluations that may run at once",
            dest="limit",
            default=None
        )

        parser.add_argument(
            "--stream_name",
            help="The name of the stream to listen to for jobs to run",
            default=service.EVALUATION_QUEUE_NAME,
            dest="stream_name"
        )

        parser.add_argument(
            "--group_name",
            help="The name of the consumer group that will listen to for jobs to run",
            dest="group_name"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__host = parameters.redis_host or service.RUNNER_HOST
        self.__port = parameters.redis_port or service.RUNNER_PORT
        self.__username = parameters.redis_username or service.RUNNER_USERNAME
        self.__password = parameters.redis_pass or service.RUNNER_PASSWORD
        self.__db = parameters.redis_db or service.RUNNER_DB
        self.__stream_name = parameters.stream_name
        self.__group_name = parameters.group_name or f"Runner Group for {self.__stream_name}"
        self.__limit = parameters.limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))


# TODO: worker.evaluate should probably just take arguments as its sole required parameter since the other values
#  it needs are in the arguments
class WorkerProcessArguments:
    """
    Arguments used when engaging the worker
    """
    def __init__(
        self,
        evaluation_id: str,
        instructions: str,
        verbosity: str = None,
        start_delay: str = None,
        communicators: CommunicatorGroup = None
    ):
        # Mark that instructions will come in as raw text
        raw_arguments: typing.List[str] = ["-t"]

        # Set the verbosity to either the passed in value or make sure it sends all
        raw_arguments.extend(("--verbosity", verbosity or "ALL"))

        # Set a start delay with a minimum of 5 seconds
        raw_arguments.extend(("-d", start_delay or "5"))

        # Pass in the name as the evaluation ID
        raw_arguments.extend(("-n", evaluation_id))

        # If there is a specific host to connect to, pass that
        if service.REDIS_HOST:
            raw_arguments.extend(("--redis-host", service.REDIS_HOST))

        # If there is a specific port to connect to, pass that
        if service.REDIS_PORT:
            raw_arguments.extend(("--redis-port", service.REDIS_PORT))

        # If there is a specific redis password to use, pass that
        if service.REDIS_PASSWORD:
            raw_arguments.extend(("--redis-password", service.REDIS_PASSWORD))

        # Finally add in the raw instructions
        raw_arguments.append(instructions)

        self.__arguments = worker.Arguments(*raw_arguments)

        self.__communicators: CommunicatorGroup = communicators

    @property
    def kwargs(self):
        """
        Keyword arguments to send to the worker
        """
        return {
            "evaluation_id": self.__arguments.evaluation_name,
            "arguments": self.__arguments,
            "definition_json": self.__arguments.instructions,
            "communicators": self.__communicators,
        }


REDIS_PARAMETERS_FOR_PROCESS = streams.StreamParameters()
"""
Process-local parameters describing how to access a stream.

Held at the process level so that the signal handler may use it for cleanup operations
"""


@dataclasses.dataclass
class JobRecord:
    """
    Represents an evaluation job that has launched and the data that has come with it
    """
    stream_name: str
    """The name of the stream that the instructions for the job went through"""
    group_name: str
    """The name of the group that the message containing the instructions belongs to"""
    consumer_name: str
    """The name of the stream consumer that owns the message that the instructions belongs to"""
    message_id: str
    """The ID of the message with the instructions for the evaluation"""
    evaluation_id: str
    """The ID of the evaluation"""
    job: futures.Future
    """The asynchronous results for the job"""

    def mark_complete(self, connection: redis.Redis, object_manager: DMODObjectManager) -> bool:
        """
        Attempt to mark a job as no longer running

        Args:
            connection: A redis connection used to mark the record as complete
            object_manager: A shared object manager that may hold data for this evaluation

        Returns:
            Whether the job was acknowledged as complete
        """
        try:
            object_manager.free(self.evaluation_id, fail_on_missing_scope=False)
        except KeyError:
            service.error(f"There is no scope for '{self.evaluation_id}' in the object manager to close")
        except Exception as exception:
            service.error(
                f"Failed to clear the scope of shared objects in evaluation '{self.evaluation_id}'",
                exception=exception
            )

        try:
            service.debug(
                f"{self.stream_name}:{self.group_name}:{self.consumer_name} will now delete message '{self.message_id}' "
                f"since it has been consumed"
            )
            confirmation = connection.xdel(self.stream_name, self.message_id)
            return bool(confirmation)
        except Exception as exception:
            service.error("Failed to mark the evaluation job as complete", exception=exception)
            return False


class Cleanupable(typing.Generic[CT]):
    """
    A wrapper that details how to clean up resources
    """
    items_to_cleanup: typing.List[Cleanupable] = []
    """A class level collection of objects marked to be cleaned"""

    @classmethod
    def cleanup_all(cls):
        """
        Call the cleanup function for all marked objects
        """
        for item in cls.items_to_cleanup:
            try:
                service.debug(f"Calling '{item}'...")
                item.cleanup()
            except Exception as exception:
                service.error(f"Could not call '{item.method}' to clean up '{item.item}'", exception)

    @classmethod
    def schedule_for_cleanup(cls, item: CT, method: typing.Callable[[CT], typing.Any] = None):
        """
        Record an object that needs to be cleaned up later

        Args:
            item: The item to clean up
            method: How to clean the item up
        """
        cls.items_to_cleanup.append(cls(item=item, method=method))

    def __init__(self, item: CT, method: typing.Callable[[CT], typing.Any]):
        """
        Constructor

        Args:
            item: The item to clean up
            method: How to clean the item up
        """
        self.item = item
        self.method = method

    def cleanup(self):
        """
        Call the method that will perform clean up operations
        """
        self.method(self.item)

    def __call__(self):
        self.cleanup()

    def __del__(self):
        self.cleanup()

    def __str__(self):
        return f"{self.method.__qualname__}({self.item})"


def launch_evaluation(
    stream_message: streams.StreamMessage,
    worker_pool: futures.Executor,
    object_manager: DMODObjectManager,
) -> typing.Optional[JobRecord]:
    """
    Launch an evaluation based on a message received through a redis stream

    Args:
        stream_message: The message received through a redis stream
        worker_pool: The pool that handles the creation of other processes
        object_manager: A shared object creator and tracker

    Returns:
        A record of the evaluation job that was created
    """
    payload = stream_message.payload
    evaluation_id = payload.get('evaluation_id')
    scope = object_manager.establish_scope(evaluation_id)

    service.debug(f"Launching an evaluation for {evaluation_id}...")
    instructions = payload.get("instructions")

    if not instructions:
        raise ValueError(f"Cannot launch an evaluation with no instructions: {stream_message}")

    if isinstance(instructions, dict):
        instructions = json.dumps(instructions, indent=4)
    
    try:
        # Build communicators that will communicate evaluation updates outside of the evaluation process
        communicators: CommunicatorGroup = utilities.get_communicators(
            communicator_id=evaluation_id,
            verbosity=payload.get("verbosity"),
            object_manager=scope,
            host=service.REDIS_HOST,
            port=service.REDIS_PORT,
            password=service.REDIS_PASSWORD,
            include_timestamp=False
        )
        service.debug(f"Communicators have been created for the evaluation named '{evaluation_id}'")
    except Exception as exception:
        service.error(
            message=f"Could not create communicators for evaluation: {evaluation_id} due to {exception}",
            exception=exception
        )
        return None

    arguments = WorkerProcessArguments(
        evaluation_id=payload['evaluation_id'],
        instructions=instructions,
        verbosity=payload.get("verbosity"),
        start_delay=payload.get("start_delay"),
        communicators=communicators
    )

    try:
        service.debug(f"Submitting the evaluation job for {evaluation_id}...")
        evaluation_job: futures.Future = worker_pool.submit(
            worker.evaluate,
            **arguments.kwargs
        )
    except Exception as exception:
        service.error(f"Could not launch evaluation {evaluation_id} due to {exception}", exception=exception)
        return None

    new_job: futures.Future = worker_pool.submit(worker.evaluate, **arguments.kwargs)

    service.info(f"Evaluation for {evaluation_id} has been launched.")

    job_record = JobRecord(
        stream_name=stream_message.stream_name,
        group_name=stream_message.group_name,
        consumer_name=stream_message.consumer_name,
        message_id=stream_message.message_id,
        evaluation_id=payload['evaluation_id'],
        job=new_job
    )

    service.debug(f"Preparing to monitor objects for {evaluation_id}...")
    try:
        object_manager.monitor_operation(evaluation_id, evaluation_job)
    except BaseException as exception:
        service.error(f"Could not monitor {evaluation_id} due to: {exception}")
        traceback.print_exc()

    return job_record


def interpret_message(
    stream_message: streams.StreamMessage,
    worker_pool: futures.Executor,
    stop_signal: multiprocessing.Event,
    object_manager: DMODObjectManager
) -> typing.Optional[JobRecord]:
    """
    Figures out what to do based on a message received through a redis stream

    stop_signal is functionally a write-only variable within this function

    Args:
        stream_message: The message received through a redis stream
        worker_pool: A multiprocessing pool that can be used to start new evaluations
        stop_signal: The signal used to stop the reading loop
        object_manager: A shared object manager

    Returns:
        The record of a job if one has been launched
    """
    if not stream_message.payload:
        raise ValueError(
            f"No payload was sent through message '{stream_message.message_id}' along the "
            f"'{stream_message.stream_name}' stream"
        )

    if 'purpose' not in stream_message.payload:
        service.debug(f"A purpose was not communicated through the {service.EVALUATION_QUEUE_NAME} stream")
        return None

    purpose = stream_message.payload.get("purpose").lower()

    if purpose == 'launch':
        return launch_evaluation(stream_message, worker_pool, object_manager=object_manager)
    if purpose in ("close", "kill", "terminate"):
        stop_signal.set()
        service.info("Exit message received. Closing the runner.")
    else:
        service.error(
            f"Runner => The purpose was not to launch or terminate. Only launching is handled through the runner."
            f"{os.linesep}Message: {json.dumps(stream_message.payload)}"
        )
    return None


def monitor_running_jobs(
    connection: redis.Redis,
    active_job_queue: queue.Queue[JobRecord],
    stop_signal: multiprocessing.Event,
    object_manager: DMODObjectManager
):
    """
    Poll a queue of jobs and close ones that are marked as complete

    Meant to be run in a separate thread

    Args:
        connection: A connection to redis that will be used to acknowledge completed jobs
        active_job_queue: A queue of jobs to poll
        stop_signal: A signal used to stop the reading loop
        object_manager: An object manager that may hold scope for a running job
    """
    record: typing.Optional[JobRecord] = None

    encountered_errors = ErrorCounter(limit=EXCEPTION_LIMIT)
    """
    A collection of errors that may bear repeats of of individual types of errors. 
    Collected errors are only finally raised if and when they have occurred over a given amount of times
    
    This ensures that the polling loop is not interrupted on rare remote errors yet still throws errors when stuck 
    in an infinite loop of failing code
    """

    # Tell this loop and the runner to halt due to the error
    #   Failure to do this will allow the runner to continue with an offline monitor
    encountered_errors.on_exceedance(lambda _: stop_signal.set())

    while not stop_signal.is_set():
        try:
            record = active_job_queue.get(block=True, timeout=1)

            if not record.job.done():
                active_job_queue.put(record)
                continue

            marked_complete = record.mark_complete(connection=connection, object_manager=object_manager)

            if not marked_complete:
                service.error(
                    f"Evaluation '{record.evaluation_id}', recognized by the '{record.consumer_name}' consumer "
                    f"within the '{record.group_name}' group on the '{record.stream_name}' stream as coming from "
                    f"message '{record.message_id}', could not be marked as complete"
                )

            record = None
        except TimeoutError:
            if record and not record.job.cancelled():
                active_job_queue.put(record)
        except queue.Empty:
            # There are plenty of times when this might be empty and that's fine. In this case we just want
            pass
        except Exception as exception:
            encountered_errors.add_error(error=exception)
            service.error(exception)

        record = None


def get_consumer_name() -> str:
    """
    Get the unique name for the consumer for this process
    """
    return f"Listener {os.getpid()}"


def shutdown_pool(pool: futures.Executor):
    """
    Shutdown an actively running executor

    Args:
        pool: The executor to shut down
    """
    if pool and hasattr(pool, "shutdown") and isinstance(getattr(pool, "shutdown"), typing.Callable):
        pool.shutdown()

def listen(
    stream_parameters: streams.StreamParameters,
    job_limit: int = None
):
    """
    Listen for messages from redis and launch evaluations or halt operations based on their content

    Args:
        stream_parameters: The means to connect to redis
        job_limit: The maximum number of jobs that may be run at once
    """
    job_limit = job_limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))
    """The maximum number of jobs that may be actively running from this listener"""

    stop_signal: multiprocessing.Event = multiprocessing.Event()
    """Tells this function and the associated monitoring thread to stop polling"""

    active_jobs: queue.Queue[JobRecord] = queue.Queue(maxsize=job_limit)
    """A queue of active jobs to poll"""

    service.info(
        f"Listening for evaluation jobs on '{stream_parameters.stream_name}' through the "
        f"'{stream_parameters.group_name}' group..."
    )
    already_listening = False

    consumer_name = get_consumer_name()
    connection = stream_parameters.get_connection()
    initialize_consumer(
        stream_name=stream_parameters.stream_name,
        group_name=stream_parameters.group_name,
        consumer_name=consumer_name,
        redis_connection=connection
    )

    monitoring_thread: typing.Optional[threading.Thread] = None

    error_counter = ErrorCounter(limit=EXCEPTION_LIMIT)

    executor_type: typing.Callable[[], futures.Executor] = get_concurrency_executor_type(
        max_workers=job_limit
    )

    try:
        with get_object_manager(monitor_scope=True) as object_manager, executor_type() as worker_pool:
            Cleanupable.schedule_for_cleanup(worker_pool, shutdown_pool)
            object_manager.logger = get_logger()

            monitoring_thread = threading.Thread(
                target=monitor_running_jobs,
                name=f"{service.application_values.APPLICATION_NAME}: Monitor for {consumer_name}",
                kwargs={
                    "connection": connection,
                    "active_job_queue": active_jobs,
                    "stop_signal": stop_signal,
                    "object_manager": object_manager
                },
                daemon=True
            )
            monitoring_thread.start()

            while not stop_signal.is_set():
                if already_listening:
                    service.warn(f"{consumer_name}: Starting to listen for evaluation jobs again")
                else:
                    already_listening = True

                try:
                    # Form the generator used to receive messages
                    message_stream = streams.StreamMessage.listen(
                        connection,
                        stream_parameters.group_name,
                        consumer_name,
                        stop_signal,
                        stream_parameters.stream_name
                    )

                    for message in message_stream:
                        service.debug(
                            f"{message.stream_name}:{message.group_name}:{consumer_name}: Received message "
                            f"'{message.message_id}'"
                        )
                        possible_record = interpret_message(
                            message,
                            worker_pool,
                            stop_signal=stop_signal,
                            object_manager=object_manager
                        )

                        if possible_record:
                            # This will block until another entry may be put into the queue - this will prevent one
                            # instance of the runner from trying to hoard all of the messages and allow other
                            # instances to try and carry the load
                            active_jobs.put(possible_record)
                        else:
                            # Since this message isn't considered one for the runner, acknowledge that it's been seen
                            # and move on so something else may view the message
                            service.debug(
                                f"{message.stream_name}:{message.group_name}:{consumer_name}: "
                                f"Acknowledging message '{message.message_id}'"
                            )
                            connection.xack(
                                stream_parameters.stream_name,
                                stream_parameters.group_name,
                                message.message_id
                            )
                            service.debug(
                                f"{message.stream_name}:{message.group_name} will no longer use message "
                                f"'{message.message_id}'"
                            )

                        if stop_signal.is_set():
                            break
                except KeyboardInterrupt:
                    stop_signal.set()
                    break
                except Exception as exception:
                    error_counter.add_error(error=exception)
                    service.error(message="An error occured while listening for evaluation jobs", exception=exception)
    finally:
        if monitoring_thread:
            monitoring_thread.join(timeout=5)


def initialize_consumer(stream_name: str, group_name: str, consumer_name: str, redis_connection: redis.Redis) -> None:
    """
    Create a consumer that will retrieve messages for a group. Generated streams will have a limited lifespan

    Args:
        stream_name: The name of the stream that the consumer will read from
        group_name: The name of the group that the consumer will be a member of
        consumer_name: The name of the consumer to create
        redis_connection: A redis connection to communicate through
    """
    service.debug(
        f"initializing a consumer named '{consumer_name}' for the '{group_name}' group for the {stream_name} stream"
    )

    try:
        service.debug(
            f"Making sure that the '{group_name}' group has been added to the '{stream_name}' stream"
        )
        # Create a group on the given stream, creating the stream if it doesn't exist, and allow it to read all
        #   messages that come after the one with the id of '0' (the beginning of the stream)
        redis_connection.xgroup_create(name=stream_name, groupname=group_name, id="0", mkstream=True)
    except redis.exceptions.ResponseError as group_create_error:
        if 'consumer group name already exists' not in str(group_create_error).lower():
            raise group_create_error

    service.debug(f"The '{group_name}' consumer group is active on the '{stream_name}' stream")
    service.debug(
        f"Adding the '{consumer_name}' consumer to the '{group_name}' group on the '{stream_name}' stream"
    )

    # Create a consumer for a group that may read from the stream and add data to the group
    redis_connection.xgroup_createconsumer(name=stream_name, groupname=group_name, consumername=consumer_name)


def cleanup_redis(redis_parameters: streams.StreamParameters) -> None:
    """
    Clean up any leftover artifacts that might be considered no longer needed

    Args:
        redis_parameters: The means to connect to redis and access a stream
    """
    if redis_parameters.is_valid:
        service.debug("Cleaning up redis resources...")
        connection = redis_parameters.get_connection()

        try:
            connection.xgroup_delconsumer(
                name=redis_parameters.stream_name,
                groupname=redis_parameters.group_name,
                consumername=get_consumer_name()
            )
        except Exception as exception:
            service.error(exception)


def main(*args):
    """
    Listen to a redis stream and launch evaluations based on received content
    """
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    arguments = Arguments(*args)

    redis_parameters = streams.StreamParameters(
        kvstore_parameters=streams.KVStoreArguments(
            host=arguments.host,
            port=arguments.port,
            username=arguments.username,
            password=arguments.password,
            db=arguments.db
        ),
        stream_name=arguments.stream_name,
        group_name=arguments.group_name,
    )

    Cleanupable.schedule_for_cleanup(redis_parameters, cleanup_redis)

    try:
        listen(stream_parameters=redis_parameters, job_limit=arguments.limit)
        exit_code = SUCCESSFUL_EXIT
    except KeyboardInterrupt:
        exit_code = SUCCESSFUL_EXIT
    except Exception as exception:
        service.error(exception)
        exit_code = ERROR_EXIT
    finally:
        try:
            cleanup_redis(redis_parameters=redis_parameters)
        except Exception as exception:
            service.error(exception)
            exit_code = ERROR_EXIT

    sys.exit(exit_code)


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
