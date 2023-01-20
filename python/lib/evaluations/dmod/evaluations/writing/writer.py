import os
import pathlib
import typing
import abc
import io
import zipfile

import dmod.core.common as common

from .. import specification


def read_and_act_recursively(
    base_path: str,
    action: typing.Callable[[str], typing.Any] = None,
    filter: typing.Callable[[str], bool] = None
) -> typing.Sequence[str]:
    files_acted_upon: typing.List[str] = list()
    directories = list()

    for found_path in os.listdir(base_path):
        full_path = os.path.join(base_path, found_path)
        if os.path.isdir(found_path):
            directories.append(full_path)
        elif os.path.isfile(full_path) and (not filter or filter(full_path)):
            if action:
                action(full_path)
            files_acted_upon.append(full_path)

    for directory in directories:
        files_acted_upon.extend(
            read_and_act_recursively(directory, action, filter)
        )

    return files_acted_upon


class OutputData(abc.ABC):
    def __init__(self, writer: "OutputWriter", **kwargs):
        self._writer = writer
        self._destinations: typing.List[str] = list()
        self._current_index: int = 0
        self._load_destination_catalog()

    def _load_destination_catalog(self):
        if not os.path.exists(self._writer.destination):
            return

        if os.path.isfile(self._writer.destination):
            self._destinations.append(self._writer.destination)
        else:
            self._destinations.extend(
                read_and_act_recursively(self._writer.destination)
            )

    def __next__(self):
        return self.next()

    def __iter__(self):
        return self._destinations

    def __len__(self):
        return len(self._destinations)

    def get_raw_data(self) -> bytes:
        output: typing.Optional[bytes] = None

        if len(self) > 1:
            buffer = io.BytesIO()

            with zipfile.ZipFile(buffer, 'w') as collected_data:
                for output_index in range(len(self)):
                    path = self._destinations[output_index]
                    collected_data.write(path, path)

            output = buffer.getvalue()
        elif len(self) == 1:
            output = self.get_bytes()

        return output

    @abc.abstractmethod
    def get_content_type(self) -> str:
        ...

    @abc.abstractmethod
    def get_extension(self) -> str:
        ...

    @abc.abstractmethod
    def get_bytes(self, index: int = None) -> bytes:
        ...

    @abc.abstractmethod
    def get(self, index: int = None):
        ...

    @abc.abstractmethod
    def next(self):
        ...

    @abc.abstractmethod
    def next_bytes(self) -> bytes:
        ...


class OutputWriter(abc.ABC):
    """
    Saves evaluation results
    """
    __destination: str

    def __init__(self, destination: typing.Union[pathlib.Path, str, typing.Sequence[str]] = None, **kwargs):
        if destination and common.is_sequence_type(destination):
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

    @abc.abstractmethod
    def retrieve_written_output(self, **kwargs) -> OutputData:
        ...
