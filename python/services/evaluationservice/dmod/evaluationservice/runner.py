#!/usr/bin/env python3
"""
Script for running a listener that will launch workers to run requested evaluations
"""
import collections
import traceback
import typing
import os
import sys
import json
import signal
import enum

from argparse import ArgumentParser

from concurrent import futures
from datetime import timedelta
from functools import partial

from dmod.metrics import CommunicatorGroup
from dmod.core.context import DMODObjectManager
from dmod.core.common.collection import TimedOccurrenceWatcher

from dmod.core.context import get_object_manager
from dmod.core.common.protocols import JobLauncherProtocol
from dmod.core.common.protocols import JobResultProtocol

import service
import utilities
import worker

from service.service_logging import get_logger


_ExitCode = collections.namedtuple('ExitCode', ['code', 'explanation'])


class _ExitCodes(_ExitCode, enum.Enum):
    """
    Exit Codes and their corresponding meanings for this application
    """
    SUCCESSFUL = 0, "Naturally Exited"
    UNEXPECTED = 1, "Exitted Unexpectedly"
    FORCED = 2, "Forced to exit by signal"
    TOO_MANY_ERRORS = 3, "Exitted due to too many errors"

    @classmethod
    def print_codes(cls):
        """
        Print out the explanation for each exit code to stdout
        """
        for exit_code in cls:
            print(str(exit_code))

    def exit(self):
        """
        Exit the application with the appropriate code
        """
        sys.exit(self.code)

    def __str__(self):
        return f"{self.code}={self.explanation}"


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


def signal_handler(signum, frame):
    """
    Catches and handles signals sent into the application from the os, such as a termination or keyboard interupt

    Args:
        signum:
        frame:
    """
    service.error("Received external signal. Now exiting.")
    _ExitCodes.FORCED.exit()


class Arguments:
    """
    Command line arguments used to launch the runner
    """
    def __init__(self, *args):
        self.__host: typing.Optional[str] = None
        self.__port: typing.Optional[str] = None
        self.__username: typing.Optional[str] = None
        self.__password: typing.Optional[str] = None
        self.__db: int = 0
        self.__channel: typing.Optional[str] = None
        self.__limit: typing.Optional[int] = None
        self.__print_exit_codes: bool = False
        self.__parse_command_line(*args)

    @property
    def host(self) -> typing.Optional[str]:
        return self.__host

    @property
    def port(self) -> typing.Optional[int]:
        return self.__port

    @property
    def username(self) -> typing.Optional[str]:
        return self.__username

    @property
    def password(self) -> typing.Optional[str]:
        return self.__password

    @property
    def db(self) -> int:
        return self.__db

    @property
    def channel(self) -> typing.Optional[str]:
        return self.__channel

    @property
    def limit(self) -> typing.Optional[int]:
        return self.__limit

    @property
    def print_exit_codes(self) -> bool:
        return self.__print_exit_codes

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
            "--channel",
            help="The name of the channel to kill",
            dest="channel"
        )

        parser.add_argument(
            "--print-exit-codes",
            dest="print_exit_codes",
            action="store_true",
            help="Print exit codes instead of running"
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
        self.__channel = parameters.channel or service.EVALUATION_QUEUE_NAME
        self.__limit = parameters.limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))
        self.__print_exit_codes = parameters.print_exit_codes


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

        service.debug(f"Launching an evaluation for {launch_parameters['evaluation_id']} from the runner...")
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
        _ExitCodes.SUCCESSFUL.exit()
    else:
        service.debug(
            f"runner => The purpose was not to launch or terminate. Only launching is handled through this. {os.linesep}"
            f"Message: {json.dumps(launch_parameters)}"
        )


def too_many_exceptions_hit(type_of_exception: type):
    """
    Raise an exception stating that the given value was hit too many times

    Args:
        type_of_exception: A type of value that is (hopefully) an exception
    """
    if isinstance(type_of_exception, BaseException):
        service.error(f'{type_of_exception} encountered too many times in too short a timee. Exiting...')
        _ExitCodes.TOO_MANY_ERRORS.exit()


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


def main(*args):
    """
    Define your initial application code here
    """
    arguments = Arguments(*args)

    if arguments.print_exit_codes:
        _ExitCodes.print_codes()
        _ExitCodes.SUCCESSFUL.exit()

    listen(
        channel=arguments.channel,
        host=arguments.host,
        port=arguments.port,
        username=arguments.username,
        password=arguments.password,
        db=arguments.db,
        job_limit=arguments.limit
    )


# Run the following if the script was run directly
if __name__ == "__main__":
    main()

    # Something else should have caused this app to exit here, so report an unexpected exit
    _ExitCodes.UNEXPECTED.exit()
