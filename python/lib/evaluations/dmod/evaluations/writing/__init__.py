import os

__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'writer.py'
]

from . import *

import typing
import inspect
import pathlib

from . import writer

from .. import specification


def get_writer_classes() -> typing.Dict[str, typing.Type[writer.OutputWriter]]:
    return {
        subclass.get_format_name().lower(): subclass
        for subclass in writer.OutputWriter.__subclasses__()
        if not inspect.isabstract(subclass)
    }


def get_writer(
        output_format: str,
        destination: typing.Union[str, pathlib.Path, typing.Sequence[str]] = None,
        **kwargs
) -> writer.OutputWriter:
    output_format = output_format.lower()
    writer_class = get_writer_classes().get(output_format)

    if writer_class is None:
        raise KeyError(
                f"There are no output writers that write '{output_format}' data."
                f"Check to make sure the correct format and spelling are given."
        )

    return writer_class(destination, **kwargs)


def get_available_formats() -> typing.List[str]:
    return [
        subclass
        for subclass in get_writer_classes()
    ]


def write(
        output_format: str,
        evaluation_results: specification.EvaluationResults,
        destination: typing.Union[str, pathlib.Path, typing.Sequence[str]] = None,
        buffer: typing.IO = None,
        **kwargs
):
    output_writer = get_writer(output_format, destination, **kwargs)
    output_writer.write(evaluation_results, buffer, **kwargs)


def clean(
    output_format: str,
    destination: typing.Union[str, pathlib.Path, typing.Sequence[str]] = None,
    **kwargs
) -> typing.Sequence[str]:
    output_writer = get_writer(output_format, destination, **kwargs)
    return output_writer.clean(**kwargs)


def get_written_output(
    output_format: str,
    destination: typing.Union[str, pathlib.Path, typing.Sequence[str]],
    **kwargs
) -> writer.OutputData:
    output_writer = get_writer(output_format, destination, **kwargs)
    return output_writer.retrieve_written_output(**kwargs)
