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
    destination: typing.Optional[str] = Field(default=None, description='Where the output was written')
    """Where the output was written"""

    writer_format: typing.Optional[str] = Field(default=None, description='What type of writer was used')
    """What type of writer was used"""

    output_format: typing.Optional[str] = Field(default=None, description='The format of the written output')
    """The format of the written output"""

    name: typing.Optional[str] = Field(default=None, description='The name of the outputs')
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

    def _validate_for_serialization(self):
        missing_elements: typing.List[str] = []

        if not self.name:
            missing_elements.append('name')

        if not self.destination:
            missing_elements.append('destination')

        if not self.writer_format:
            missing_elements.append('writer_format')

        if not self.output_format:
            missing_elements.append('output_format')

        if missing_elements:
            raise MissingError(
                f"A {self.__class__.__name__} cannot be serialized as it is missing values for the following fields: "
                f"{', '.join(missing_elements)}"
            )

    def dict(self, *args, **kwargs) -> typing.Dict[str, typing.Any]:
        """
        Convert this into a dictionary

        Args:
            *args:
            **kwargs:

        Returns:
            The contents of this converted into a dictionary
        """
        self._validate_for_serialization()

        dictionary = {
            "destination": self.destination,
            "output_format": self.output_format,
            "writer_format": self.writer_format,
            "name": self.name,
        }

        if self.redis_configuration:
            dictionary.update(self.redis_configuration)

        if self.environment_variables:
            dictionary.update(self.environment_variables)

        if self.additional_parameters:
            dictionary.update(self.additional_parameters)

        return dictionary

    def json(self, *args, **kwargs) -> str:
        """
        Convert this into a JSON string

        Args:
            *args:
            **kwargs:

        Returns:
            A JSON string containing all the contents of this
        """
        self._validate_for_serialization()
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


def get_destination_parameters(evaluation_id: str, output_format: str = None, **kwargs) -> DestinationParameters:
    destination_parameters = DestinationParameters()

    environment_variables = output_environment_variables()

    should_use_environment_variables = common.is_true(environment_variables.get("USE_ENVIRONMENT", False))
    redis_configuration_key = environment_variables.get("REDIS_OUTPUT_KEY", None)

    if redis_configuration_key:
        destination_parameters.redis_configuration = get_parameters_from_redis(redis_configuration_key)

    if should_use_environment_variables:
        destination_parameters.environment_variables = output_environment_variables()

    if not destination_parameters.output_format:
        destination_parameters.output_format = get_output_format(output_format=output_format, **kwargs)

    if not destination_parameters.writer_format:
        destination_parameters.writer_format = get_output_format(output_format=output_format, **kwargs)

    writing_class = writing.get_writer_classes().get(destination_parameters.output_format)
    output_extension = writing_class.get_extension()
    output_extension = "." + output_extension if output_extension else output_extension
    destination_parameters.name = f"{evaluation_id}_results{output_extension}"
    destination_parameters.additional_parameters = kwargs.copy()

    if not destination_parameters.destination:
        destination_parameters.destination = os.path.join(get_default_writing_location(), destination_parameters.name)

    return destination_parameters


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
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    return writing.get_written_output(**destination_parameters.dict())


def clean(evaluation_id: str, output_format: str = None, **kwargs):
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters.dict())
    writer.clean(**destination_parameters.dict())
