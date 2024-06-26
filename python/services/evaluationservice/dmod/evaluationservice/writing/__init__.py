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


class DestinationParameters(BaseModel):
    """
    Details where output was written
    """
    destination: str = Field(description='Where the output was written')
    """Where the output was written"""

    writer_format: str = Field(description='What type of writer was used')
    """What type of writer was used"""

    output_format: str = Field(description='The format of the written output')
    """The format of the written output"""

    name: str = Field(description='The name of the outputs')
    """The name of the outputs"""

    additional_parameters: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        default=None,
        description='Nonstandard Parameters used when writing'
    )
    """Nonstandard Parameters used when writing"""

    redis_configuration: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        default=None,
        description='Information about how redis was employed'
    )
    """Information about how redis was employed"""

    environment_variables: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        default=None,
        description="Special environment variables used for writing output"
    )
    """Special environment variables used for writing output"""

    def json(self, *args, **kwargs) -> str:
        """
        Convert this into a JSON string

        Args:
            *args:
            **kwargs:

        Returns:
            A JSON string containing all the contents of this
        """
        dictionary = self.dict(*args, **kwargs)
        return json.dumps(dictionary)


def default_format() -> str:
    return "netcdf"


def output_environment_variable_prefix() -> str:
    return "MAAS::EVALUATION::OUTPUT::"


def output_environment_variables() -> typing.Dict[str, typing.Any]:
    return {
        key.replace(output_environment_variable_prefix(), ""): value
        for key, value in os.environ.items()
        if key.startswith(output_environment_variable_prefix())
    }


def get_default_writing_location() -> str:
    directory = os.environ.get("EVALUATION_OUTPUT_PATH", "evaluation_results")

    if not os.path.exists(directory):
        os.makedirs(directory)

    return directory


def get_output_format(output_format: str = None, **kwargs) -> str:
    if output_format:
        return output_format

    available_writers = writing.get_available_formats()

    if available_writers:
        return available_writers[0]

    return default_format()


def get_parameters_from_redis(configuration_key: str = None) -> typing.Dict[str, typing.Any]:
    with utilities.get_redis_connection() as connection:
        parameters = connection.hgetall(name=configuration_key)

    if parameters is None:
        return {}

    return parameters


def get_destination_parameters(
    evaluation_id: str,
    output_format: str = None,
    writer_format: str = None,
    destination: str = None,
    name: str = None,
    **kwargs
) -> DestinationParameters:
    """
    Gather information on how and where evaluation output should be written

    Args:
        evaluation_id: The identifier for the evaluation
        output_format: What format the output should be written
        writer_format: The type of writer should be used
        destination: Where the output should be written
        name: The name of the output
        **kwargs: additional parameters for the writer

    Returns:
        Information on how and where evaluation output should be written
    """
    environment_variables = output_environment_variables()

    should_use_environment_variables = common.is_true(environment_variables.get("USE_ENVIRONMENT", False))
    redis_configuration_key = environment_variables.get("REDIS_OUTPUT_KEY", None)

    if redis_configuration_key:
        redis_configuration = get_parameters_from_redis(redis_configuration_key)
    else:
        redis_configuration = None

    if should_use_environment_variables:
        environment_variables = output_environment_variables()
    else:
        environment_variables = None

    if not output_format:
        output_format = get_output_format(output_format=output_format, **kwargs)

    if not writer_format:
        writer_format = get_output_format(output_format=output_format, **kwargs)

    writing_class = writing.get_writer_classes().get(output_format)
    output_extension = writing_class.get_extension()
    output_extension = "." + output_extension if output_extension else output_extension

    if not name:
        name = f"{evaluation_id}_results{output_extension}"

    if not destination:
        destination = os.path.join(get_default_writing_location(), name)

    return DestinationParameters(
        destination=destination,
        writer_format=writer_format,
        output_format=output_format,
        name=name,
        redis_configuration=redis_configuration,
        environment_variables=environment_variables,
        additional_parameters=kwargs.copy()
    )


def write(
    evaluation_id: str,
    results: specification.EvaluationResults,
    output_format: str = None,
    **kwargs
) -> DestinationParameters:
    """
    Writes evaluation results to the official location

    Args:
        evaluation_id: The ID of the evaluation being written
        results: The formed metrics
        output_format: What format the output should be in
        **kwargs: Additional parameters required to write in the given format

    Returns:
        Information about how output was written and where it is
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )

    writer = writing.get_writer(**destination_parameters.dict())
    writer.write(evaluation_results=results, **destination_parameters.dict())

    return destination_parameters


def get_output(evaluation_id: str, output_format: str = None, **kwargs) -> writing.writer.OutputData:
    """
    Retrieve a mechanism that provides raw output data

    Args:
        evaluation_id: The ID for the evaluation whose output should be read
        output_format: The format that the output was written in
        **kwargs:

    Returns:
        A mechanism used to iterate through evaluation output
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    return writing.get_written_output(**destination_parameters.dict())


def clean(evaluation_id: str, output_format: str = None, **kwargs) -> typing.Sequence[str]:
    """
    Remove output data for an evaluation

    Args:
        evaluation_id: The ID of the evaluation whose output should be removed
        output_format: The format that the output was written in
        **kwargs: Additional parameters for the writer that has access to the output

    Returns:
        Names of the output that were removed
    """
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters.dict())
    return writer.clean(**destination_parameters.dict())
