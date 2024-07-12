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

from functools import reduce
from operator import iconcat as combine

from argparse import ArgumentParser
from multiprocessing.pool import ApplyResult
from time import sleep

import redis

from concurrent import futures
from datetime import timedelta
from functools import partial

from dmod.metrics import CommunicatorGroup
from dmod.core.context import DMODObjectManager

from dmod.core.context import get_object_manager

import service
import utilities
import worker

from utilities.common import ErrorCounter


RawRedisMessage = typing.Tuple[bytes, typing.Dict[bytes, bytes]]
"""
How each individual message is represented - a tuple indicating the message id and a dictionary of each key and value
"""

RawRedisMessageStream = typing.List[typing.Union[bytes, typing.List[RawRedisMessage]]]
"""
How each collection of messages is represented when reading from a stream.
This is implemented via a list, but a tuple would be more appropriate. The first index is the stream name and the 
second index is the collection of messages read for it
"""

LATEST_MESSAGE: typing.Final[str] = ">"
"""
The `xreadgroup` function uses a dictionary of '{<stream name>: <previously read message id>}' to determine what next 
to read. Using '{<stream name>: ">"}' will tell it to get the next unread message for <stream name>
"""


EXCEPTION_LIMIT: typing.Final[int] = 10


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
    Handles cleanup operations for
    Args:
        signum: The type of signal currently being handled
        frame: The frame explaining where the code was when the signal was triggered
    """
    signal_description: str = signal.strsignal(signum).split(":")[0]
    service.error(f"Received external signal: {signal_description}")

    if all(REDIS_PARAMETERS_FOR_PROCESS.values()):
        service.error("Cleaning up redis resources...")
        cleanup(**REDIS_PARAMETERS_FOR_PROCESS)

    service.error("Now exiting...")
    sys.exit(1)


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

        # Add options

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


@dataclasses.dataclass
class RedisArguments:
    """
    A DTO for the common arguments used to connect to redis
    """
    host: typing.Optional[str] = dataclasses.field(default=None)
    port: typing.Optional[typing.Union[int, str]] = dataclasses.field(default=None)
    username: typing.Optional[str] = dataclasses.field(default=None)
    password: typing.Optional[str] = dataclasses.field(default=None)
    db: typing.Optional[int] = dataclasses.field(default=None)

    def get_connection(self) -> redis.Redis:
        """
        Connect to Redis

        Returns:
            A connection to redis
        """
        return utilities.get_redis_connection(self.host, self.port, self.username, self.password, self.db)


ARGUMENTS_FOR_PROCESS: typing.Optional[RedisArguments] = None


REDIS_PARAMETERS_FOR_PROCESS: typing.Dict[
    typing.Literal['redis_parameters', 'stream_name', 'group_name'],
    typing.Union[None, str, RedisArguments]
] = {
    "redis_parameters": None,
    "stream_name": None,
    "group_name": None
}


@dataclasses.dataclass
class StreamMessage:
    """
    Represents a message sent through a redis stream
    """
    stream_name: str
    """The name of the stream that this travelled through"""

    group_name: str
    """The name of the group that is readding the message"""

    consumer_name: str
    """The name of the consumer reading the message"""

    message_id: str
    """The ID of the message that was sent"""

    values: typing.Dict[str, str]
    """The payload of the message that was sent"""

    @classmethod
    def listen(
        cls,
        connection: redis.Redis,
        group_name: str,
        consumer_name: str,
        stop_signal: multiprocessing.Event,
        stream: str
    ) -> typing.Generator[StreamMessage, None, None]:
        """
        Get the next message in the indicated stream

        Args:
            connection: A redis connection to read from
            group_name: The group that the reader belongs to
            consumer_name: The name of the reader
            stop_signal: The signal to stop listening for messages
            stream: The name of the stream to read from

        Returns:
            All new messages from the indicated streams
        """
        # Create a dict of {"name": ">"} to tell the redis client to read the latest message from the
        streams: typing.Dict[str, str] = {stream: LATEST_MESSAGE}

        while not stop_signal.is_set():
            try:
                # Read a single message from any of the possible streams and assign them to the given consumer name
                #   for the given group
                # This adds a single message from any of the given streams to the group's PEL, assigning it to the given
                #   consumer
                #       - Call `xack` to remove it from the consumer and announce that the given group won't look at it
                #       - Call `xclaim` to assign the message to another consumer within the group
                messages_per_stream: typing.List[RawRedisMessageStream] = connection.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams=streams,
                    count=1,
                    block=1000
                )
            except Exception as read_exception:
                message = (f"Could not read the latest unread messages from the '{', '.join(streams)}' stream(s) for the "
                           f"{consumer_name} consumer in the '{group_name}' group using a consumer named '{consumer_name}'")

                service.error(message, exception=read_exception)
                raise read_exception

            # Extract the contents of the difficultly formatted messages
            read_streams: typing.List[typing.List[StreamMessage]] = [
                cls.parse_stream(message_stream, group_name=group_name, consumer_name=consumer_name)
                for message_stream in messages_per_stream
            ]

            # Put all of the read messages into a single list
            messages: typing.List[StreamMessage] = reduce(combine, read_streams, [])

            if messages:
                service.info(
                    f"The following messages are now in the pending list for the consumer named {consumer_name}:"
                    f"{os.linesep}"
                    f"* {(os.linesep + '* ').join(message.message_id for message in messages)}"
                    f"{os.linesep}"
                )

                yield from messages
            else:
                sleep(1)

    @classmethod
    def parse_stream(
        cls,
        message_stream: RawRedisMessageStream,
        group_name: str,
        consumer_name: str,
    ) -> typing.List[StreamMessage]:
        """
        Convert all given collection of messages into a collection of concrete message objects

        Args:
            message_stream: The raw collection of messages. The first index is the stream name,
                the second is the collection of messages
            group_name: The name of the consumer group that will listen to for messages
            consumer_name: The name of the consumer reading the message

        Returns:
            A collection of concrete message objects
        """
        # Convert the name to the friendlier 'str' type
        stream_name: str = message_stream[0].decode()

        # Call the `parse` function on each received message to convert each collected message into the concrete type
        messages: typing.List[StreamMessage] = [
            cls.parse(stream_name=stream_name, raw_message=message, group_name=group_name, consumer_name=consumer_name)
            for message in message_stream[1]
        ]

        return messages

    @classmethod
    def parse(
        cls,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        raw_message: RawRedisMessage,
    ) -> StreamMessage:
        """
        Read the basic values from a message from a redis stream and form a concrete message object

        Args:
            stream_name: The name of the stream where this message originated
            group_name: The name of the consumer group that this message belongs to
            consumer_name: The name of the consumer reading the message
            raw_message: The raw message that was received

        Returns:
            A concrete message object
        """
        # The first index of the message is the ID in bytes, so convert that to a string
        message_id: str = raw_message[0].decode()
        return StreamMessage(
            stream_name=stream_name,
            message_id=message_id,
            group_name=group_name,
            consumer_name=consumer_name,
            values={
                key.decode(): value.decode()
                for key, value in raw_message[1].items()
            }
        )


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
    job: ApplyResult
    """The asynchronous results for the job"""

    def mark_complete(self, connection: redis.Redis) -> bool:
        """
        Attempt to mark a job as no longer running

        Args:
            connection: A redis connection used to mark the record as complete

        Returns:
            Whether the job was acknowledged as complete
        """
        try:
            confirmation = connection.xdel(self.stream_name, self.message_id)
            return bool(confirmation)
        except Exception as exception:
            service.error("Failed to mark the evaluation job as complete", exception=exception)
            return False


def launch_evaluation(
    stream_message: StreamMessage,
    worker_pool: multiprocessing.Pool
) -> JobRecord:
    """
    Launch an evaluation based on a message received through a redis stream

    Args:
        stream_message: The message received through a redis stream
        worker_pool: The pool that handles the creation of other processes

    Returns:
        A record of the evaluation job that was created
    """
    payload = stream_message.values

    service.info(f"Launching an evaluation for {payload['evaluation_id']}...")
    instructions = payload.get("instructions")

    if not instructions:
        raise ValueError(f"Cannot launch an evaluation with no instructions: {stream_message}")

    if isinstance(instructions, dict):
        instructions = json.dumps(instructions, indent=4)

    arguments = JobArguments(
        evaluation_id=payload['evaluation_id'],
        instructions=instructions,
        verbosity=payload.get("verbosity"),
        start_delay=payload.get("start_delay")
    )

    new_job: ApplyResult = worker_pool.apply_async(
        worker.evaluate,
        kwds=arguments.kwargs
    )

    service.info(f"Evaluation for {payload['evaluation_id']} has been launched.")

    job_record = JobRecord(
        stream_name=stream_message.stream_name,
        group_name=stream_message.group_name,
        consumer_name=stream_message.consumer_name,
        message_id=stream_message.message_id,
        evaluation_id=payload['evaluation_id'],
        job=new_job
    )

    return job_record


def interpret_message(
    stream_message: StreamMessage,
    worker_pool: multiprocessing.Pool,
    stop_signal: multiprocessing.Event
) -> typing.Optional[JobRecord]:
    """
    Figures out what to do based on a message received through a redis stream

    stop_signal is functionally a write-only variable within this function

    Args:
        stream_message: The message received through a redis stream
        worker_pool: A multiprocessing pool that can be used to start new evaluations
        stop_signal: The signal used to stop the reading loop

    Returns:
        The record of a job if one has been launched
    """
    payload = stream_message.values

    if not payload:
        raise ValueError(
            f"No payload was sent through message '{stream_message.message_id}' along the "
            f"'{stream_message.stream_name}' stream"
        )

    if 'purpose' not in payload:
        service.info(f"A purpose was not communicated through the {service.EVALUATION_QUEUE_NAME} channel")
        return None

    purpose = payload.get("purpose").lower()

    if purpose == 'launch':
        return launch_evaluation(stream_message, worker_pool)
    if purpose in ("close", "kill", "terminate"):
        stop_signal.set()
        service.info("Exit message received. Closing the runner.")
        sys.exit(0)
    else:
        service.info(
            f"Runner => The purpose was not to launch or terminate. Only launching is handled through the runner."
            f"{os.linesep}Message: {json.dumps(payload)}"
        )
    return None


def monitor_running_jobs(
    connection: redis.Redis,
    active_job_queue: queue.Queue[ApplyResult[JobRecord]],
    stop_signal: multiprocessing.Event
):
    """
    Poll a queue of jobs and close ones that are marked as complete

    Meant to be run in a separate thread

    Args:
        connection: A connection to redis that will be used to acknowledge completed jobs
        active_job_queue: A queue of jobs to poll
        stop_signal: A signal used to stop the reading loop
    """
    potentially_complete_job: typing.Optional[ApplyResult] = None

    monitor_errors = ErrorCounter(limit=EXCEPTION_LIMIT)

    while not stop_signal.is_set():
        try:
            potentially_complete_job = active_job_queue.get(block=True, timeout=1)

            if not potentially_complete_job.ready():
                active_job_queue.put(potentially_complete_job)
                continue

            record: JobRecord = potentially_complete_job.get()

            marked_complete = record.mark_complete(connection=connection)

            if not marked_complete:
                service.error(
                    f"Evaluation '{record.evaluation_id}', recognized by the '{record.consumer_name}' consumer "
                    f"within the '{record.group_name}' group on the '{record.stream_name}' stream as coming from "
                    f"message '{record.message_id}', could not be marked as complete"
                )

            potentially_complete_job = None
        except TimeoutError:
            if potentially_complete_job:
                active_job_queue.put(potentially_complete_job)
        except queue.Empty:
            # There are plenty of times when this might be empty and that's fine. In this case we just want
            pass
        except Exception as exception:
            monitor_errors.add_error(error=exception)
            service.error(exception)

        potentially_complete_job = None


def run_job(
    launch_message: dict,
    worker_pool: futures.Executor,
    object_manager: DMODObjectManager
):
    """
    Adds the evaluation to the worker pool for background processing

    Args:
        launch_message: A dictionary containing data to send to the process running the job
        worker_pool: The pool with processes ready to run an evaluation
        object_manager: The object manager used to create shared objects
    """
    if launch_message['type'] != 'message':
        # We exit because this isn't a useful message
        return

    launch_parameters = launch_message['data']
    if not isinstance(launch_parameters, dict):
        try:
            launch_parameters = json.loads(launch_parameters)
        except Exception as exception:
            service.error("The passed message wasn't JSON")
            service.error(launch_parameters, exception)
            return

    if 'purpose' not in launch_parameters:
        service.info(f"A purpose was not communicated through the {service.EVALUATION_QUEUE_NAME} channel")
        return

    purpose = launch_parameters.get("purpose").lower()

    if purpose == 'launch':
        evaluation_id = launch_parameters.get('evaluation_id')
        scope = object_manager.establish_scope(evaluation_id)
        try:
            communicators: CommunicatorGroup = utilities.get_communicators(
                communicator_id=evaluation_id,
                verbosity=launch_parameters.get("verbosity"),
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
            return

        service.info(f"Launching an evaluation for {launch_parameters['evaluation_id']}...")
        instructions = launch_parameters.get("instructions")

        if isinstance(instructions, dict):
            instructions = json.dumps(instructions, indent=4)

        arguments = WorkerProcessArguments(
            evaluation_id=launch_parameters['evaluation_id'],
            instructions=instructions,
            verbosity=launch_parameters.get("verbosity"),
            start_delay=launch_parameters.get("start_delay"),
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
            return

        service.debug(f"Preparing to monitor {evaluation_id}...")
        try:
            object_manager.monitor_operation(evaluation_id, evaluation_job)
            service.debug(f"Evaluation for {launch_parameters['evaluation_id']} has been launched.")
        except BaseException as exception:
            service.error(f"Could not monitor {evaluation_id} due to: {exception}")
            traceback.print_exc()
    elif purpose in ("close", "kill", "terminate"):
        service.info("Exit message received. Closing the runner.")
        sys.exit(0)
    else:
        service.info(
            f"Runner => The purpose was not to launch or terminate. Only launching is handled through the runner."
            f"{os.linesep}Message: {json.dumps(payload)}"
        )
    return None


def monitor_running_jobs(
    connection: redis.Redis,
    active_job_queue: queue.Queue[ApplyResult[JobRecord]],
    stop_signal: multiprocessing.Event
):
    """
    Poll a queue of jobs and close ones that are marked as complete

    Meant to be run in a separate thread

    Args:
        connection: A connection to redis that will be used to acknowledge completed jobs
        active_job_queue: A queue of jobs to poll
        stop_signal: A signal used to stop the reading loop
    """
    potentially_complete_job: typing.Optional[ApplyResult] = None

    monitor_errors = ErrorCounter(limit=EXCEPTION_LIMIT)

    while not stop_signal.is_set():
        try:
            potentially_complete_job = active_job_queue.get(block=True, timeout=1)

            if not potentially_complete_job.ready():
                active_job_queue.put(potentially_complete_job)
                continue

            record: JobRecord = potentially_complete_job.get()

            marked_complete = record.mark_complete(connection=connection)

            if not marked_complete:
                service.error(
                    f"Evaluation '{record.evaluation_id}', recognized by the '{record.consumer_name}' consumer "
                    f"within the '{record.group_name}' group on the '{record.stream_name}' stream as coming from "
                    f"message '{record.message_id}', could not be marked as complete"
                )

            potentially_complete_job = None
        except TimeoutError:
            if potentially_complete_job:
                active_job_queue.put(potentially_complete_job)
        except queue.Empty:
            # There are plenty of times when this might be empty and that's fine. In this case we just want
            pass
        except Exception as exception:
            monitor_errors.add_error(error=exception)
            service.error(exception)

        potentially_complete_job = None


def get_consumer_name() -> str:
    """
    Get the unique name for the consumer for this process
    """
    return f"Listener {os.getpid()}"


def listen(
    stream_name: str,
    group_name: str,
    redis_parameters: RedisArguments,
    job_limit: int = None
):
    """
    Listen for messages from redis and launch evaluations or halt operations based on their content

    Args:
        stream_name: The name of the stream to read through
        group_name: The name of the group to read from
        redis_parameters: The means to connect to redis
        job_limit: The maximum number of jobs that may be run at once
    """
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    job_limit = job_limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))
    stop_signal: multiprocessing.Event = multiprocessing.Event()
    active_jobs: queue.Queue[JobRecord] = queue.Queue(maxsize=job_limit)

    service.info(f"Listening for evaluation jobs on '{stream_name}' through the '{group_name}' group...")
    already_listening = False

    consumer_name = get_consumer_name()
    connection = redis_parameters.get_connection()
    initialize_consumer(
        stream_name=stream_name,
        group_name=group_name,
        consumer_name=consumer_name,
        redis_connection=connection
    )

    monitoring_thread = threading.Thread(target=monitor_running_jobs, args=(connection, active_jobs, stop_signal))
    monitoring_thread.setDaemon(True)
    monitoring_thread.start()

    error_counter = ErrorCounter(limit=EXCEPTION_LIMIT)

    with multiprocessing.Pool(processes=job_limit) as worker_pool:  # type: multiprocessing.pool.Pool
        while not stop_signal.is_set():
            if already_listening:
                service.info("Starting to listen for evaluation jobs again")
            else:
                already_listening = True

            try:
                # Form the generator used to receive messages
                message_stream: typing.Generator[StreamMessage, None, None] = StreamMessage.listen(
                    connection,
                    group_name,
                    consumer_name,
                    stop_signal,
                    stream_name
                )

                for message in message_stream:
                    possible_record = interpret_message(message, worker_pool, stop_signal)

                    if possible_record:
                        # This will block until another entry may be put into the queue - this will prevent one
                        # instance of the runner from trying to hoard all of the messages and allow other
                        # instances to try and carry the load
                        active_jobs.put(possible_record)
                    else:
                        connection.xack(stream_name, group_name, message.message_id)

                    if stop_signal.is_set():
                        break
            except Exception as exception:
                error_counter.add_error(error=exception)
                service.error(message="An error occured while listening for evaluation jobs", exception=exception)

    monitoring_thread.join(timeout=5)


# TODO: Switch from pubsub to a redis stream
def listen(
    channel: str,
    host: str = None,
    port: typing.Union[str, int] = None,
    username: str = None,
    password: str = None,
    db: int = 0,
    job_limit: int = None
):
    """
    Listen for requested evaluations

    Args:
        channel: The channel to listen to
        host: The address of the redis server
        port: The port of the host that is serving the redis server
        username: The username used for credentials into the redis server
        password: A password that might be needed to access redis
        db: The database number of the redis server to interact with
        job_limit: The number of jobs that may be run at once
    """
    # Trap signals that stop the application to correctly inform what exactly shut the runner down
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    job_limit = job_limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))

    service.info(f"Listening for evaluation jobs on '{channel}'...")
    already_listening = False

    error_tracker: TimedOccurrenceWatcher = TimedOccurrenceWatcher(
        duration=timedelta(seconds=10),
        threshold=10,
        on_filled=too_many_exceptions_hit
    )

    try:
        with get_object_manager(monitor_scope=True) as object_manager:
            object_manager.logger = get_logger()
            while True:
                if already_listening:
                    service.info("Starting to listen for evaluation jobs again")
                else:
                    service.info("Listening out for evaluation jobs")
                    already_listening = True

                try:
                    connection = utilities.get_redis_connection(
                        host=host,
                        port=port,
                        password=password,
                        username=username,
                        db=db
                    )

                    listener = connection.pubsub()
                    listener.subscribe(channel)

                    executor_type: typing.Callable[[], futures.Executor] = get_concurrency_executor_type(
                        max_workers=job_limit
                    )

                    with executor_type() as worker_pool:
                        for message in listener.listen():
                            run_job(launch_message=message, worker_pool=worker_pool, object_manager=object_manager)
                except Exception as exception:
                    service.error(message="An error occured while listening for evaluation jobs", exception=exception)
    except Exception as exception:
        service.error(
            message="A critical error caused the evaluation listener to fail and not recover",
            exception=exception
        )

        # Inform the error tracker that the exception was hit. An exception will be hit and the loop will halt if
        # the type of exception has been hit too many times in a short period
        error_tracker.value_encountered(value=exception)


def initialize_consumer(stream_name: str, group_name: str, consumer_name: str, redis_connection: redis.Redis) -> None:
    """
    Create a consumer that will retrieve messages for a group. Generated streams will have a limited lifespan

    Args:
        stream_name: The name of the stream that the consumer will read from
        group_name: The name of the group that the consumer will be a member of
        consumer_name: The name of the consumer to create
        redis_connection: A redis connection to communicate through
    """
    service.info(
        f"initializing a consumer named '{consumer_name}' for the '{group_name}' group for the {stream_name} stream"
    )

    try:
        service.info(
            f"Making sure that the '{group_name}' group has been added to the '{stream_name}' stream"
        )
        # Create a group on the given stream, creating the stream if it doesn't exist, and allow it to read all
        #   messages that come after the one with the id of '0' (the beginning of the stream)
        redis_connection.xgroup_create(name=stream_name, groupname=group_name, id="0", mkstream=True)
    except redis.exceptions.ResponseError as group_create_error:
        if 'consumer group name already exists' not in str(group_create_error).lower():
            raise group_create_error

        service.info(f"The '{group_name}' consumer group is active on the '{stream_name}' stream")
        service.info(
            f"Adding the '{consumer_name}' consumer to the '{group_name}' group on the '{stream_name}' stream"
        )

        # Create a consumer for a group that may read from the stream and add data to the group
        redis_connection.xgroup_createconsumer(name=stream_name, groupname=group_name, consumername=consumer_name)


def cleanup(
    stream_name: str,
    group_name: str,
    redis_parameters: RedisArguments
):
    """
    Clean up any leftover artifacts that might be considered no longer needed

    Args:
        stream_name: The name of the stream that the runner will have been communicating through
        group_name: The name of the group that this runner is a member of
        redis_parameters: The means to connect to redis
    """
    connection = redis_parameters.get_connection()

    try:
        connection.xgroup_delconsumer(name=stream_name, groupname=group_name, consumername=get_consumer_name())
    except Exception as exception:
        service.error(exception)



def main(*args):
    """
    Listen to a redis stream and launch evaluations based on received content
    """
    arguments = Arguments(*args)

    redis_parameters = RedisArguments(
        host=arguments.host,
        port=arguments.port,
        username=arguments.username,
        password=arguments.password,
        db=arguments.db
    )

    # Basic information needs to be accessible globally for the cleanup process to run in case of an interrupt
    REDIS_PARAMETERS_FOR_PROCESS['redis_parameters'] = redis_parameters
    REDIS_PARAMETERS_FOR_PROCESS['stream_name'] = arguments.stream_name
    REDIS_PARAMETERS_FOR_PROCESS['group_name'] = arguments.group_name

    try:
        listen(
            stream_name=arguments.stream_name,
            group_name=arguments.group_name,
            redis_parameters=redis_parameters,
            job_limit=arguments.limit
        )
        exit_code = 0
    except Exception as exception:
        service.error(exception)
        exit_code = 1
    finally:
        try:
            cleanup(
                stream_name=arguments.stream_name,
                group_name=arguments.group_name,
                redis_parameters=redis_parameters
            )
        except Exception as exception:
            service.error(exception)
            exit_code = 1

    sys.exit(exit_code)


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
