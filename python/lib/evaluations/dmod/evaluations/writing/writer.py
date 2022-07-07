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

    @classmethod
    @abc.abstractmethod
    def get_extension(cls) -> str:
        """
        Returns:
            The extension that the data will be written to
        """
        ...

    @classmethod
    @abc.abstractmethod
    def requires_destination_address_or_buffer(cls) -> bool:
        """
        Returns:
            Whether the writer requires a string to tell it where to put data or a buffer within which to put it
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

    def clean(self, *args, **kwargs) -> typing.Sequence[str]:
        """
        Attempts to remove saved data

        Args:
            *args:
            **kwargs:

        Returns:
            A collection of everything that was removed
        """
        cleaned_data = list()

        if self.destination and os.path.exists(self.destination):
            os.remove(self.destination)
            cleaned_data.append(self.destination)

        return cleaned_data
