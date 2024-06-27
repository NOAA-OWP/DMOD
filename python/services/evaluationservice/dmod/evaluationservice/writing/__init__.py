import typing
import os
import json

from pydantic import BaseModel
from pydantic import Field
from pydantic.errors import MissingError

import dmod.evaluations.specification as specification
import dmod.evaluations.writing as writing
import dmod.core.common as common

import utilities


def default_format() -> str:
    return "netcdf"


def get_default_writing_location() -> str:
    directory = os.environ.get("EVALUATION_OUTPUT_PATH", "evaluation_results")

    if not os.path.exists(directory):
        os.makedirs(directory)

    return directory


def get_output_format(output_format: str = None) -> str:
    if output_format:
        return output_format

    return writing.get_available_formats()[0]


def get_parameters_from_redis(configuration_key: str = None) -> typing.Dict[str, typing.Any]:
    if configuration_key is None:
        return {}

    with utilities.get_redis_connection() as connection:
        parameters = connection.hgetall(name=configuration_key)

    if parameters is None:
        return {}

    return parameters


def get_destination_parameters(
    evaluation_id: str,
    output_format: str = None,
    **writer_parameters
) -> typing.Dict[str, typing.Any]:
    """
    Get details about where to put or find evaluation output

    Args:
        evaluation_id: The id of the evaluation whose results to find
        output_format: The expected format of the outputs
        **writer_parameters: Keyword arguments for the writer that constructs outputs

    Returns:
        A dictionary of keyword parameters to send to a writer to inform it of where to write or find output
    """
    if not output_format:
        output_format = get_output_format()

    parameters = writer_parameters.copy()

    parameters['output_format'] = output_format

    writing_class = writing.get_writer_classes().get(output_format)

    output_extension = writing_class.get_extension()
    output_extension = "." + output_extension if output_extension else output_extension
    parameters['name'] = f"{evaluation_id}_results{output_extension}"

    if not parameters.get("destination"):
        parameters['destination'] = os.path.join(get_default_writing_location(), parameters['name'])

    return parameters


def write(evaluation_id: str, results: specification.EvaluationResults, output_format: str = None, **kwargs) -> dict:
    """
    Writes evaluation results to the official location

    Args:
        evaluation_id: The ID of the evaluation being written
        results: The formed metrics
        output_format: The format that the output should be written in
        **kwargs: Additional parameters required to write in the given format

    Returns:
        Information about how output was written and where it is
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters)
    writer.write(evaluation_results=results, **destination_parameters)
    return destination_parameters


def get_output(evaluation_id: str, **kwargs) -> writing.writer.OutputData:
    """
    Retrieve a mechanism that provides raw output data

    Args:
        evaluation_id: The ID for the evaluation whose output should be read
        **kwargs:

    Returns:
        A mechanism used to iterate through evaluation output
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        **kwargs
    )
    return writing.get_written_output(**destination_parameters)


def clean(evaluation_id: str, **kwargs) -> typing.Sequence[str]:
    """
    Remove output data for an evaluation

    Args:
        evaluation_id: The ID of the evaluation whose output should be removed
        **kwargs: Additional parameters for the writer that has access to the output

    Returns:
        Names of the output that were removed
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters)
    return writer.clean(**destination_parameters)
