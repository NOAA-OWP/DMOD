import typing
import inspect
import pathlib
import os

__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'writer.py'
]

from . import *
from . import writer

from .. import specification


def get_writer(
        writer_format: str,
        destination: typing.Union[str, pathlib.Path, typing.Sequence[str]] = None,
        **kwargs
) -> writer.OutputWriter:
    writer_map = {
        subclass.get_format_name().lower(): subclass
        for subclass in writer.OutputWriter.__subclasses__()
        if not inspect.isabstract(subclass)
    }

    writer_format = writer_format.lower()
    writer_class = writer_map.get(writer_format)

    if writer_class is None:
        raise KeyError(
                f"There are no output writers that write '{writer_format}' data."
                f"Check to make sure the correct format and spelling are given."
        )

    return writer_class(destination, **kwargs)


def write(
        writer_format: str,
        evaluation_results: specification.EvaluationResults,
        destination: typing.Union[str, pathlib.Path, typing.Sequence[str]] = None,
        buffer: typing.IO = None,
        **kwargs
):
    output_writer = get_writer(writer_format, destination, **kwargs)
    output_writer.write(evaluation_results, buffer, **kwargs)
