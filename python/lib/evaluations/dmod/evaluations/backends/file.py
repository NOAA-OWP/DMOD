"""
Defines Backends for loading data from a filesystem, generally straight from disk
"""
import typing
import os
import io
import re
import pathlib

import pkg_resources
import logging
import h5py

from deprecated import deprecated

import pandas

import dmod.core.common as common

from . import backend
from .. import util
from .. import specification

util.configure_logging()


RE_PATTERN = re.compile(r"(\{.+\}|\[.+\]|\(.+\)|(?<!\\)\.|\{|\}|\]|\[|\(|\)|\+|\*|\\[a-zA-Z]|\?)+")
MULTI_GLOB_PATTERN = re.compile(r"\*+")
EXPLICIT_START_PATTERN = re.compile(r"^(~|\.)?/.*$")


class FileBackend(backend.Backend):
    @classmethod
    def get_backend_type(cls) -> str:
        return "file"

    def __init__(self, definition: specification.BackendSpecification, cache_limit: int = None):
        super().__init__(definition, cache_limit)
        self._sources = util.get_matching_paths(self.address)

    def read(self, identifier: str, store_data: bool = None) -> bytes:
        """
        Loads data from either disk or from the cache

        Args:
            identifier: The identifier (such as a file name) for the data
            store_data: Whether to save the data in the cache

        Returns:
            Raw byte data from the file
        """
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

    def read_stream(self, identifier: str, store_data: bool = None) -> typing.IO:
        """
        Retrieves data in the form of a stream

        Args:
            identifier: The identifier for the data (generally the path to the file)
            store_data: Whether to store the retrieved data in the cache

        Returns:
            An IO stream containing the loaded data
        """
        # TODO: This just shifts data into a new buffer - find a way to return the original buffer instead
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

    @deprecated
    def write(
            self,
            destination: typing.Union[pathlib.Path, str, io.IOBase, typing.Sequence[str]],
            data: specification.EvaluationResults,
            data_format: str = None,
            **kwargs
    ):
        # TODO: Move all into the writing package
        if data_format is None:
            data_format = self.format

        if common.is_sequence_type(destination):
            destination = pathlib.Path(*destination)

        write_functions = {
            "html": self.write_to_html,
            "markdown": self.write_to_markdown,
            "hdf": self.write_to_hdf
        }

        if data_format not in write_functions:
            raise KeyError(f"'{data_format}' is not a valid file output format.")

        return write_functions[data_format](destination, data, **kwargs)

    @deprecated
    def write_to_hdf(
            self,
            destination: typing.Union[pathlib.Path, str, io.IOBase, typing.Sequence[str]],
            data: specification.EvaluationResults,
            **kwargs
    ):
        """
        Writes evaluation results to the given destination in HDF5

        Args:
            destination: Where to write the results to
            data: The results to save
            **kwargs: Keyword arguments used when saving to the HDF5 file

        Returns:

        """
        # TODO: Move into a writer class
        with pandas.HDFStore(destination, mode='w') as store:
            for name, frame in data.to_frames():  # type: str, pandas.DataFrame
                store[name] = frame

        with h5py.File(destination, mode='r+') as generated_file:
            generated_file.attrs['result'] = data.value
            generated_file.attrs['mean'] = data.mean
            generated_file.attrs['median'] = data.median
            generated_file.attrs['grade'] = data.grade
            generated_file.attrs['standard_deviation'] = data.standard_deviation
            generated_file.attrs['location_count'] = len(data)

    @deprecated
    def write_to_markdown(
            self,
            destination: typing.Union[pathlib.Path, str, io.IOBase, typing.Sequence[str], typing.IO],
            data: pandas.DataFrame,
            group_columns: typing.Sequence[str] = None,
            **kwargs
    ):
        # TODO: Move into a writer class

        grouped_data: typing.Dict[str, pandas.DataFrame] = dict()
        if group_columns:
            for identifier, group in data.groupby(group_columns):  # type: tuple, pandas.DataFrame
                grouped_data["-".join(identifier)] = group
        else:
            grouped_data["Evaluation Results"] = data

        if common.is_sequence_type(destination):
            destination = pathlib.Path(*destination)

        buffer: typing.Optional[typing.Union[typing.IO, io.IOBase]] = None
        buffer_was_created_here = True
        try:
            if isinstance(destination, (io.IOBase, typing.IO)):
                buffer = destination
                buffer_was_created_here = False
            else:
                buffer = open(destination, "a")

            append_count = 0

            for group_identifier, group in grouped_data.items():
                if not isinstance(group_identifier, str):
                    group_identifier = str(group_identifier)

                if append_count > 0:
                    buffer.write(os.linesep)
                    buffer.write(os.linesep)

                buffer.write(f"## {group_identifier}{os.linesep}")
                buffer.write(group.to_markdown(**kwargs))
                append_count += 1
        finally:
            if buffer is not None and not buffer.closed and buffer_was_created_here:
                buffer.close()

    @deprecated
    def write_to_html(
            self,
            destination: typing.Union[pathlib.Path, str, io.IOBase, typing.Sequence[str]],
            data: specification.EvaluationResults,
            css_query: str = None,
            xpath_query: str = None,
            **kwargs
    ):
        """
        Writes resultant metric data to an html file

        TODO: Move into a writer class

        Args:
            destination:
                Where to find the html file to write to
            data:
                The data to write
            css_query:
                A css query to an HTML element to attempt to append to
            xpath_query:
                An xpath query to an HTML element to attempt to append to
            **kwargs:
        """

        if common.is_sequence_type(destination):
            destination = pathlib.Path(*destination)

        buffer: typing.Optional[typing.Union[typing.IO, io.IOBase]] = None
        buffer_was_created_here = True

        use_css = False
        use_xpath = False

        document_already_exists = not isinstance(destination, (typing.IO, io.IOBase)) and os.path.exists(destination)

        insert_into_document = document_already_exists and (css_query or xpath_query)

        if insert_into_document and css_query:
            if "bs4" in pkg_resources.working_set.by_key:
                # Use BeautifulSoup to check if tables may be added via css selector
                use_css = True
                import bs4
            else:
                # Warn that the html could not be inserted via css
                logging.getLogger().warning(
                        "BeautifulSoup was not installed - css selection cannot be used to insert html"
                )

        elif insert_into_document and xpath_query and not use_css:
            if "lxml" in pkg_resources.working_set.by_key:
                # Use lxml.etree to check if tables may be added via xpath
                use_xpath = True
                import lxml.etree as etree
            else:
                # Warn that the xpath could not be used to insert the html into the document
                logging.getLogger().warning(
                        "lxml is not installed - xpath selection cannot be used to insert html"
                )

        try:
            document = None

            if isinstance(destination, (typing.IO, io.IOBase)):
                buffer = destination
                buffer_was_created_here = False
            else:
                buffer = open(destination, "a")

            nodes = None

            if use_css:
                document = bs4.BeautifulSoup(buffer, "html.parser")
                nodes = document.select(css_query)
            if use_xpath:
                document = etree.fromstring(buffer.read())
                nodes = document.xpath(xpath_query)

            one_table_per_node = nodes is not None and len(nodes) == len(data)
            node_index = 0

            for title, results_data in data:
                results_data.style.caption = title
                result_html = results_data.to_html(**kwargs)

                if nodes:
                    if use_css:
                        nodes[node_index].append(bs4.BeautifulSoup(result_html, "html.parser"))
                    else:
                        nodes[node_index].insert(0, etree.fromstring(result_html))
                else:
                    buffer.write(result_html)

                if one_table_per_node:
                    node_index += 1

            if nodes:
                if use_css:
                    buffer.write(document.prettify())
                else:
                    document.write(destination, pretty_print=True)
        finally:
            if buffer is not None and not buffer.closed and buffer_was_created_here:
                buffer.close()

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

