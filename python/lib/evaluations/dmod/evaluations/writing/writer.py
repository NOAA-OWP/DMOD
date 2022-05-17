import os
import pathlib
import typing
import abc

from .. import specification
from .. import util


class OutputWriter(abc.ABC):
    """
    Saves evaluation results
    """
    __destination: str

    def __init__(self, destination: typing.Union[pathlib.Path, str, typing.Sequence[str]] = None, **kwargs):
        if destination and util.is_arraytype(destination):
            destination = os.path.join(*[part for part in destination])
        elif destination:
            destination = str(destination)

        self.__destination = destination

    @property
    def destination(self) -> str:
        """
        Where the data should be written if not passed through a buffer
        """
        return self.__destination

    @classmethod
    @abc.abstractmethod
    def get_format_name(cls) -> str:
        """
        Returns:
            The name that the writer should be referred to by outside code
        """
        ...

    @abc.abstractmethod
    def write(self, evaluation_results: specification.EvaluationResults, buffer: typing.IO = None, **kwargs):
        """
        Writes evaluation data to either disk or a given buffer

        Args:
            evaluation_results:
                The results to write
            buffer:
                An optional stream to write to instead of the disk
            **kwargs:
                Optional args specific to the type of writer
        """
        pass
