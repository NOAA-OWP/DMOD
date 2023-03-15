#!/usr/bin/env python3
import typing
import os

import dmod.evaluations.specification as specification
import dmod.evaluations.writing as writing
import dmod.core.common as common

import utilities


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

    available_writers = [
        writer_name
        for writer_name in writing.get_available_formats()
    ]

    if available_writers:
        return available_writers[0]

    return default_format()


def get_parameters_from_redis(configuration_key: str) -> typing.Dict[str, typing.Any]:
    with utilities.get_redis_connection() as connection:
        parameters = connection.hgetall(name=configuration_key)

    if parameters is None:
        return dict()

    return parameters


def get_destination_parameters(evaluation_id: str, output_format: str = None, **kwargs) -> typing.Dict[str, typing.Any]:
    environment_variables = output_environment_variables()

    should_use_environment_variables = common.is_true(environment_variables.get("USE_ENVIRONMENT", False))
    redis_configuration_key = environment_variables.get("REDIS_OUTPUT_KEY", None)

    parameters = dict()

    if redis_configuration_key:
        parameters.update(
            get_parameters_from_redis(redis_configuration_key)
        )

    if should_use_environment_variables:
        parameters.update(
            {
                key: value
                for key, value in environment_variables.items()
                if key not in parameters
            }
        )

    parameters = {
        key.lower() if key.isupper() else key: value
        for key, value in parameters.items()
    }

    if not parameters.get("output_format"):
        parameters['output_format'] = get_output_format(output_format=output_format, **kwargs)

    if not parameters.get("writer_format"):
        parameters['writer_format'] = get_output_format(output_format=output_format, **kwargs)

    writing_class = writing.get_writer_classes().get(parameters['output_format'])
    output_extension = writing_class.get_extension()
    output_extension = "." + output_extension if output_extension else output_extension
    parameters['name'] = f"{evaluation_id}_results{output_extension}"

    parameters.update({
        key: value
        for key, value in kwargs.items()
        if key not in parameters
    })

    if not parameters.get("destination"):
        parameters['destination'] = os.path.join(get_default_writing_location(), parameters['name'])

    return parameters


def write(evaluation_id: str, results: specification.EvaluationResults, output_format: str = None, **kwargs) -> dict:
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters)
    writer.write(evaluation_results=results, **destination_parameters)
    return destination_parameters


def get_output(evaluation_id: str, output_format: str = None, **kwargs) -> writing.writer.OutputData:
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    return writing.get_written_output(**destination_parameters)


def clean(evaluation_id: str, output_format: str = None, **kwargs):
    destination_parameters = get_destination_parameters(
        evaluation_id=evaluation_id,
        output_format=output_format,
        writer_format=output_format,
        **kwargs
    )
    writer = writing.get_writer(**destination_parameters)
    writer.clean(**destination_parameters)
