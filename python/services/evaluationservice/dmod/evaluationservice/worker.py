#!/usr/bin/env python3
"""
Performs an evaluation based on a set of command line arguments
"""
import os
import typing
import json

from time import sleep
from argparse import ArgumentParser

from dmod.metrics import Verbosity

from dmod.metrics import CommunicatorGroup
from dmod.evaluations.evaluate import Evaluator
from dmod.metrics.communication import StandardCommunicator

import service
import utilities
import writing

from service.application_values import COMMON_DATETIME_FORMAT

DEFAULT_OUTPUT_FORMAT = "netcdf"


class Arguments:
    """
    Command line arguments bearing all the information needed to run an evaluation
    """
    def __init__(self, *args):
        self.__instructions: typing.Optional[str] = None
        self.__evaluation_name: typing.Optional[str] = None
        self.__is_text: typing.Optional[bool] = False
        self.__redis_host: typing.Optional[str] = None
        self.__redis_port: typing.Optional[int] = None
        self.__redis_password: typing.Optional[str] = None
        self.__verbosity: typing.Optional[Verbosity] = None
        self.__start_delay: int = 0
        self.__format: typing.Optional[str] = None
        self.__write_to_stdout: bool = False
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

    @property
    def format(self):
        return self.__format

    @property
    def write_to_stdout(self) -> bool:
        return self.__write_to_stdout

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

        parser.add_argument(
            "--format",
            help="The format that output should be written as",
            default=DEFAULT_OUTPUT_FORMAT,
            dest="format"
        )

        parser.add_argument(
            "--stdout",
            dest="to_stdout",
            action="store_true",
            default=False,
            help="Print messages to stdout alongside other communicators"
        )

        # Parse the list of args if one is passed instead of args passed to the script
        if args:
            args = [str(arg) for arg in args]
            try:
                parameters = parser.parse_args(args)
            except Exception as exception:
                message = "Could not parse passed arguments:" + os.linesep
                for arg in args:
                    message += f"    {type(arg)}: {str(arg)}{os.linesep}"
                service.error(exception)
                raise Exception(message) from exception
        else:
            parameters = parser.parse_args()

        verbosity = parameters.verbosity.upper() if parameters.verbosity else "NORMAL"

        # Assign parsed parameters to member variables
        self.__is_text = parameters.is_text
        self.__instructions = parameters.instructions
        self.__evaluation_name = parameters.name
        self.__verbosity = Verbosity[verbosity]
        self.__start_delay = int(parameters.delay) if parameters.delay else 0
        self.__format = parameters.format
        self.__write_to_stdout = parameters.to_stdout


def evaluate(
    evaluation_id: str,
    definition_json: str,
    arguments: Arguments = None,
    communicators: CommunicatorGroup = None
) -> dict:
    """
    Run an evaluation

    Args:
        evaluation_id: The ID that the evaluation will be referred to
        definition_json: The definition of what to do in JSON string form
        arguments: Command line arguments
        communicators: A collection of communicator objects used to broadcast messages

    Returns:
        A dictionary of evaluation results
    """
    service.debug(f"Preparing to run the evaluation named '{evaluation_id}' in the worker")

    if " " in evaluation_id:
        raise ValueError("The evaluation id must not contain spaces")

    write_results = {
        "success": False,
        "evaluation_id": evaluation_id
    }

    redis_host = arguments.redis_host if arguments else None
    redis_port = arguments.redis_port if arguments else None
    redis_password = arguments.redis_password if arguments else None
    delay_seconds = int(arguments.start_delay) if arguments else 0

    if arguments:
        verbosity = arguments.verbosity
    else:
        verbosity = Verbosity[os.environ.get("EVALUATION_VERBOSITY", "NORMAL").upper()]

    should_publish = verbosity >= Verbosity.NORMAL
    write_to_stdout = arguments is not None and arguments.write_to_stdout

    service.debug("Giving the system time to be ready to run the evaluation")
    sleep(delay_seconds)

    if communicators is None:
        communicators = utilities.get_communicators(
            communicator_id=evaluation_id,
            verbosity=verbosity,
            host=redis_host,
            port=redis_port,
            password=redis_password,
            include_timestamp=False
        )

    try:
        if write_to_stdout:
            communicators.attach(communicator=StandardCommunicator(communicator_id="standard-communicator"))

        error_key = utilities.key_separator().join([utilities.redis_prefix(), evaluation_id, "ERRORS"])
        message_key = utilities.key_separator().join([utilities.redis_prefix(), evaluation_id, "MESSAGES"])

        communicators.update(
            created_at=utilities.now().strftime(COMMON_DATETIME_FORMAT),
            failed=False,
            complete=False,
            error_key=error_key,
            message_key=message_key
        )

        try:
            definition = json.loads(definition_json)
            service.info(f"Loaded the definition for the evaluation named '{evaluation_id}")
        except Exception as exception:
            message = "The evaluation instructions could not be loaded"
            communicators.error(message, exception, publish=should_publish)
            communicators.error(definition_json, None, publish=should_publish)
            communicators.update(failed=True)
            communicators.sunset(60*3)
            raise exception

        try:
            evaluator = Evaluator(definition, communicators=communicators, verbosity=verbosity)
            communicators.info(f"starting {evaluation_id}", publish=should_publish)
            results = evaluator.evaluate()
            communicators.info(f"Result: {results.grade:.2f}%", publish=should_publish)
            communicators.info(f"{evaluation_id} complete; now writing results")
            write_results = writing.write(evaluation_id=evaluation_id, results=results, output_format=arguments.format)
            communicators.info(f"Data from {evaluation_id} was written.")
        except Exception as e:
            communicators.error(f"{e.__class__.__name__}: {e}", e, publish=should_publish)
            communicators.update(failed=True)
            communicators.sunset(60*3)
        finally:
            communicators.update(complete=True)
            communicators.info(f"{evaluation_id} is complete", publish=should_publish)
    except Exception as e:
        service.error(f"An error occurred that prevented the proper execution of an evaluation: {e}")

    return write_results


def main(arguments: Arguments = None):
    """
    Runs an evaluation based on passed command line arguments
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
        name = "Evaluation_at"

    name += f"_{utilities.now().strftime('%Y-%m-%d_%H%M')}"
    name = name.replace(" ", "_")

    try:
        evaluate(name, instructions, arguments)
    except Exception as e:
        service.error(e)


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
