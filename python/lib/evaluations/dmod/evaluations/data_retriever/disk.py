#!/usr/bin/env python3
import typing
import os
import re
import inspect

import pandas

from .. import specification
from ..crosswalk import reader
from .. import jsonquery
from .. import util

from . import dataretriever


def get_datasource(datasource_definition: specification.DataSourceSpecification) -> dataretriever.DataRetriever:
    return __FORMAT_MAPPING[datasource_definition.backend.format](datasource_definition)


class JSONDataRetriever(dataretriever.DataRetriever):
    def get_data(self) -> pandas.DataFrame:
        documents = {
            source: jsonquery.Document(self.backend.get_data(source))
            for source in self.backend.sources
        }

        frames = dict()

        for document_name, document in documents.items():  # type: str, jsonquery.Document
            frame = None
            for selector in self.definition.value_selectors:
                selected_data = reader.select_values(document.data, selector)

                if frame is None:
                    frame = selected_data
                else:
                    if util.is_indexed(frame):
                        frame.reset_index(inplace=True)

                    if util.is_indexed(selected_data):
                        selected_data.reset_index(inplace=True)

                    common_columns = [
                        column_name
                        for column_name in frame.keys()
                        if column_name in selected_data.keys()
                    ]

                    if common_columns:
                        frame.set_index(keys=common_columns, inplace=True)
                        selected_data.set_index(keys=common_columns, inplace=True)

                    frame = frame.join(selected_data)

                    if util.is_indexed(frame):
                        frame.reset_index(inplace=True)

            if self.definition.locations.from_field.lower() == "filename":
                name = None

                if self.definition.locations.pattern:
                    full_pattern = os.pathsep.join(self.definition.locations.pattern)
                    search_results = re.search(full_pattern, document_name)
                    if search_results:
                        name = search_results.group()

                if not name:
                    name = os.path.splitext(os.path.basename(document_name))[0]

                frame['location'] = name

            if util.is_indexed(frame):
                frame = frame.reset_index()

            for mapping in self.definition.field_mapping:
                if mapping.map_type != "column":
                    continue

                if mapping.value in frame:
                    frame.rename(columns={mapping.value: mapping.field}, inplace=True)

            frames[document_name] = frame

        combined_frame = pandas.concat([frame for frame in frames.values()])

        return combined_frame



class FrameDataRetriever(dataretriever.DataRetriever):
    def get_data(self) -> pandas.DataFrame:
        constructor_signature = inspect.signature(pandas.read_csv)
        provided_parameters = {
            key: value
            for key, value in self.backend.definition.properties.items()
            if key in constructor_signature.parameters
        }

        column_options = self.definition.get_column_options()

        for option, value in column_options.items():
            if option not in provided_parameters:
                provided_parameters[option] = value
            elif util.is_arraytype(value) and util.is_arraytype(provided_parameters[option]):
                for entry in value:
                    if entry not in provided_parameters[option]:
                        provided_parameters[option].append(entry)
            elif isinstance(value, dict) and isinstance(provided_parameters[option], dict):
                provided_parameters[option].update(value)
            else:
                provided_parameters[option] = value

        if 'date_parser' not in provided_parameters:
            provided_parameters['date_parser'] = util.parse_non_naive_dates

        combined_table = None

        for source in self.backend.sources:
            document = pandas.read_csv(self.backend.get_data_stream(source), **provided_parameters)

            column_names: typing.Set[str] = set()

            index_names: typing.Set[str] = set()

            for selector in self.definition.value_selectors:
                if selector.where.lower() != 'column':
                    raise ValueError(f"Column to be found in a '{selector.where}' is not valid for csv data.")

                if selector.name not in document.keys():
                    raise KeyError(f"There is not a column named '{selector.name}' in '{source}'")

                column_names.add(selector.name)

                for index in selector.index:
                    if index.name not in document.keys():
                        raise KeyError(f"There is not a column named '{index.name}' in '{source}'")

                    column_names.add(index.name)
                    index_names.add(index.name)

            table: pandas.DataFrame = document[column_names]

            if self.definition.locations.should_identify and self.definition.locations.from_field.lower() == 'filename':
                file_name_without_extension = os.path.splitext(os.path.basename(source))[0]

                search_results = re.search(
                        os.path.pathsep.join(self.definition.locations.pattern),
                        file_name_without_extension
                )

                name = search_results.group() if search_results else file_name_without_extension

                table = table.assign(location=[name for _ in range(len(table))])

            fields_to_rename: typing.Dict[str, str] = dict()

            for mapping in self.definition.field_mapping:
                if mapping.map_type.lower() != 'column':
                    raise ValueError(
                            f"Values from the {mapping.value} field may not be mapped to '{mapping.field}' "
                            f"via a '{mapping.map_type}' for CSV data."
                    )

                if mapping.value not in table.keys():
                    raise KeyError(
                            f"There is not a column named '{mapping.value}' to rename in the retrieved table; "
                            f"available columns are: [{', '.join([column_name for column_name in table.keys()])}]"
                    )

                fields_to_rename[mapping.value] = mapping.field

            if fields_to_rename:
                table.rename(columns=fields_to_rename, inplace=True)

            if combined_table is None:
                combined_table = table
            else:
                combined_table = pandas.concat([combined_table, table])

        return combined_table


__FORMAT_MAPPING = {
    "json": JSONDataRetriever,
    "csv": FrameDataRetriever
}
