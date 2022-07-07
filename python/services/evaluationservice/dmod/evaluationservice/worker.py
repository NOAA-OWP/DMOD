#!/usr/bin/env python3
import os
import typing
import json
import logging

from time import sleep
from datetime import datetime
from argparse import ArgumentParser

from dmod.evaluations.util import Verbosity

from dmod.evaluations.evaluate import Evaluator

import utilities
import writing

utilities.configure_logging()


class Arguments(object):
    def __init__(self, *args):
        self.__instructions: typing.Optional[str] = None
        self.__evaluation_name: typing.Optional[str] = None
        self.__is_text: typing.Optional[bool] = False
        self.__redis_host: typing.Optional[str] = None
        self.__redis_port: typing.Optional[int] = None
        self.__redis_password: typing.Optional[str] = None
        self.__verbosity: typing.Optional[Verbosity] = None
        self.__start_delay: int = 0
        self.__parse_command_line(*args)

    @property
    def instructions(self) -> str:
        return self.__instructions

    @property
    def evaluation_name(self) -> str:
        return self.__evaluation_name

    @property
    def is_text(self) -> bool:
        return self.__is_text

    @property
    def redis_host(self) -> typing.Optional[str]:
        return self.__redis_host

    @property
    def redis_port(self) -> typing.Optional[int]:
        return self.__redis_port

    @property
    def redis_password(self) -> typing.Optional[str]:
        return self.__redis_password

    @property
    def start_delay(self) -> typing.Optional[int]:
        return self.__start_delay

    @property
    def verbosity(self):
        return self.__verbosity

    def __parse_command_line(self, *args):
        parser = ArgumentParser("Launches the worker script that starts and tracks an evaluation")

        # Add options
        parser.add_argument(
            "-t",
            dest="is_text",
            action="store_true",
            default=False,
            help="The instructions are pure text and not a path"
        )

        parser.add_argument(
            "-n",
            metavar="name",
            dest="name",
            help="The name of the evaluation"
        )

        parser.add_argument(
            "-d",
            metavar="seconds",
            dest="delay",
            type=int,
            default=0,
            help="The number of seconds to wait before starting the evaluation"
        )

        parser.add_argument(
            "instructions",
            type=str,
            help="The instructions that define the evaluation"
        )

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
            "--verbosity",
            help="The amount of information that will be emitted by the evaluation",
            dest="verbosity",
            default="NORMAL",
            choices=["QUIET", "NORMAL", "LOUD", "ALL"]
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            parameters = parser.parse_args(args)
        else:
            parameters = parser.parse_args()

        verbosity = parameters.verbosity.upper() if parameters.verbosity else "NORMAL"

        # Assign parsed parameters to member variables
        self.__is_text = parameters.is_text
        self.__instructions = parameters.instructions
        self.__evaluation_name = parameters.name
        self.__verbosity = Verbosity[verbosity]
        self.__start_delay = int(parameters.delay) if parameters.delay else 0


def evaluate(evaluation_id: str, definition_json: str, arguments: Arguments = None):
    evaluation_id = evaluation_id.replace(" ", "_")

    redis_host = arguments.redis_host if arguments else None
    redis_port = arguments.redis_port if arguments else None
    redis_password = arguments.redis_password if arguments else None
    delay_seconds = int(arguments.start_delay) if arguments else 0

    if arguments:
        verbosity = arguments.verbosity
    else:
        verbosity = Verbosity[os.environ.get("EVALUATION_VERBOSITY", "NORMAL").upper()]

    should_publish = verbosity >= Verbosity.NORMAL

    sleep(delay_seconds)

    communicator = utilities.get_communicator(
        communicator_id=evaluation_id,
        host=redis_host,
        port=redis_port,
        password=redis_password
    )

    print(f"Writing to {communicator}")

    error_key = "::".join([utilities.redis_prefix(), evaluation_id, "ERRORS"])
    message_key = "::".join([utilities.redis_prefix(), evaluation_id, "MESSAGES"])

    communicator.update(
        created_at=utilities.now().strftime(utilities.datetime_format()),
        failed=False,
        complete=False,
        error_key=error_key,
        message_key=message_key
    )

    try:
        definition = json.loads(definition_json)
    except Exception as exception:
        message = "The evaluation instructions could not be loaded"
        communicator.error(message, exception, should_publish)
        communicator.error(definition_json, None, should_publish)
        communicator.update(failed=True)
        communicator.sunset(60*3)
        raise exception

    try:
        evaluator = Evaluator(definition, communicators=communicator, verbosity=verbosity)
        communicator.info(f"starting {evaluation_id}", publish=should_publish)
        results = evaluator.evaluate()
        communicator.info(f"Result: {results.grade}%", publish=should_publish)
        communicator.info(f"{evaluation_id} complete; now writing results")
        writing.write(evaluation_id=evaluation_id, results=results)
        communicator.info(f"Data from {evaluation_id} was written.")
    except Exception as e:
        communicator.error(f"{e.__class__.__name__}: {e}", e, should_publish)
        communicator.update(failed=True)
        communicator.sunset(60*3)
    finally:
        communicator.update(complete=True)
        communicator.info(f"{evaluation_id} is complete", should_publish)


def main(arguments: Arguments = None):
    """
    Define your initial application code here
    """
    if arguments is None:
        arguments = Arguments()

    if arguments.is_text:
        instructions = arguments.instructions
    else:
        with open(arguments.instructions) as instruction_file:
            instructions = instruction_file.read()

    if arguments.evaluation_name:
        name = arguments.evaluation_name
    else:
        name = ""

    name += f"_{datetime.now().strftime('%Y-%m-%d_%H%M')}"
    name = name.replace(" ", "_")
    evaluate(name, instructions, arguments)


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
