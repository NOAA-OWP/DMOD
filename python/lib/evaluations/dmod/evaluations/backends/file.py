import typing
import io
import glob
import re

from . import backend
from .. import specification


RE_PATTERN = re.compile(r"(\{.+\}|\[.+\]|\(.+\)|(?<!\\)\.|\{|\}|\]|\[|\(|\)|\+|\*|\\[a-zA-Z]|\?)+")
MULTI_GLOB_PATTERN = re.compile(r"\*+")
EXPLICIT_START_PATTERN = re.compile(r"^(~|\.)?/.*$")


class FileBackend(backend.Backend):
    def __init__(self, definition: specification.BackendSpecification, cache_limit: int = None):
        super().__init__(definition, cache_limit)
        self._load_sources()

    def _load_sources(self):
        glob_address = self._get_globbed_address()
        matching_paths: typing.Sequence[str] = glob.glob(glob_address, recursive=True)

        address_pattern: re.Pattern = re.compile(self.address)
        matching_paths = [
            path
            for path in matching_paths
            if address_pattern.match(path)
        ]
        self._sources = matching_paths

    def get_data(self, identifier: str, store_data: bool = None) -> bytes:
        if identifier not in self._sources:
            raise ValueError(f"'{identifier}' is not available within this backend")

        if identifier in self._raw_data:
            self._update_access_time(identifier)
            return self._raw_data[identifier][1]

        with open(identifier, 'rb') as data_file:
            byte_data = data_file.read()

            if store_data:
                self._add_to_cache(identifier, byte_data)

            return byte_data

    def get_data_stream(self, identifier: str, store_data: bool = None) -> typing.IO:
        if identifier not in self._sources:
            raise ValueError(f"'{identifier}' is not available within this backend")

        if identifier in self._raw_data:
            raw_data = self._raw_data[identifier][1]
            self._update_access_time(identifier)
        else:
            with open(identifier, 'rb') as data_file:
                raw_data = data_file.read()

                if store_data:
                    self._add_to_cache(identifier, raw_data)

        stream = io.BytesIO()
        stream.write(raw_data)
        stream.seek(0)
        return stream

    def _get_globbed_address(self) -> str:
        """
        Returns:
            The address except with regular expressions converted to glob statements
        """
        globbed_address = RE_PATTERN.sub("*", self.address)

        if globbed_address.endswith("$"):
            globbed_address = globbed_address[:-1]
        else:
            globbed_address += "*"

        if not EXPLICIT_START_PATTERN.match(globbed_address):
            globbed_address = f"*{globbed_address}"

        # Make sure to remove multiple '*' from the glob that may have been added
        globbed_address = MULTI_GLOB_PATTERN.sub("*", globbed_address)
        globbed_address = globbed_address.replace("\\", "")

        return globbed_address

