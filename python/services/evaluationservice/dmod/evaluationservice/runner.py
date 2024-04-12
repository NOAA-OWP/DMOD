#!/usr/bin/env python3
import typing
import os
import sys
import multiprocessing
import json
import signal

from argparse import ArgumentParser

import service
import utilities
import worker


def signal_handler(signum, frame):
    service.error("Received external signal. Now exiting.")
    sys.exit(1)


class Arguments(object):
    def __init__(self, *args):
        self.__host: typing.Optional[str] = None
        self.__port: typing.Optional[str] = None
        self.__password: typing.Optional[str] = None
        self.__channel: typing.Optional[str] = None
        self.__limit: typing.Optional[int] = None
        self.__parse_command_line(*args)

    @property
    def host(self) -> typing.Optional[str]:
        return self.__host

    @property
    def port(self) -> typing.Optional[int]:
        return self.__port

    @property
    def password(self) -> typing.Optional[str]:
        return self.__password

    @property
    def channel(self) -> typing.Optional[str]:
        return self.__channel

    @property
    def limit(self) -> typing.Optional[int]:
        return self.__limit

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Starts a series of processes that will listen and launch evaluations")

        # Add options
        parser.add_argument('--redis-host',
                            help='Set the host value for making Redis connections',
                            dest='redis_host',
                            default=None)

        parser.add_argument('--redis-pass',
                            help='Set the password value for making Redis connections',
                            dest='redis_pass',
                            default=None)

        parser.add_argument('--redis-port',
                            help='Set the port value for making Redis connections',
                            dest='redis_port',
                            default=None)

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

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        # Assign parsed parameters to member variables
        self.__host = parameters.redis_host or service.RQ_HOST
        self.__port = parameters.redis_port or service.RQ_PORT
        self.__password = parameters.redis_pass or service.REDIS_PASSWORD
        self.__channel = parameters.channel or service.EVALUATION_QUEUE_NAME
        self.__limit = parameters.limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))


# TODO: worker.evaluate should probably just take arguments as its sole required parameter since the other values
#  it needs are in the arguments
class JobArguments:
    def __init__(self, evaluation_id: str, instructions: str, verbosity: str = None, start_delay: str = None):
        self.__arguments = worker.Arguments(
            "-t",
            "--verbosity",
            verbosity or "ALL",
            "-d",
            start_delay or "5",
            "-n",
            evaluation_id,
            instructions
        )

    @property
    def kwargs(self):
        return {
            "evaluation_id": self.__arguments.evaluation_name,
            "arguments": self.__arguments,
            "definition_json": self.__arguments.instructions
        }


def run_job(
    launch_message: dict,
    worker_pool: multiprocessing.Pool
) -> typing.Optional[multiprocessing.pool.AsyncResult]:
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
        service.info(f"Launching an evaluation for {launch_parameters['evaluation_id']}...")
        instructions = launch_parameters.get("instructions")

        if isinstance(instructions, dict):
            instructions = json.dumps(instructions, indent=4)
        arguments = JobArguments(
            evaluation_id=launch_parameters['evaluation_id'],
            instructions=instructions,
            verbosity=launch_parameters.get("verbosity"),
            start_delay=launch_parameters.get("start_delay")
        )
        worker_pool.apply_async(
            worker.evaluate,
            kwds=arguments.kwargs
        )
        service.info(f"Evaluation for {launch_parameters['evaluation_id']} has been launched.")
    elif purpose in ("close", "kill", "terminate"):
        service.info("Exit message received. Closing the runner.")
        sys.exit(0)
    else:
        service.debug(
            f"runner => The purpose was not to launch or terminate. Only launching is handled through this. {os.linesep}"
            f"Message: {json.dumps(launch_parameters)}"
        )


def listen(
    channel: str,
    host: str = None,
    port: typing.Union[str, int] = None,
    password: str = None,
    job_limit: int = None
):
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    job_limit = job_limit or int(float(os.environ.get("MAXIMUM_RUNNING_JOBS", os.cpu_count())))

    service.info(f"Listening for evaluation jobs on '{channel}'...")
    already_listening = False
    while True:
        if already_listening:
            service.info("Starting to listen for evaluation jobs again")
        else:
            already_listening = True
        try:
            connection = utilities.get_redis_connection(
                host=host,
                port=port,
                password=password
            )
            listener = connection.pubsub()
            listener.subscribe(channel)
            with multiprocessing.Pool(processes=job_limit) as worker_pool:
                for message in listener.listen():
                    run_job(message, worker_pool)
        except Exception as exception:
            service.error(message="An error occured while listening for evaluation jobs", exception=exception)


def main():
    """
    Define your initial application code here
    """
    arguments = Arguments()
    listen(
        channel=arguments.channel,
        host=arguments.host,
        port=arguments.port,
        password=arguments.password,
        job_limit=arguments.limit
    )


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
