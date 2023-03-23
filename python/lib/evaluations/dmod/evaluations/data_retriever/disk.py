#!/usr/bin/env python3
import typing
import os
import re
import inspect
import logging

import pandas

import dmod.core.common as common

from .. import specification
from .. import retrieval

from .. import reader
from .. import util


def get_datasource(datasource_definition: specification.DataSourceSpecification) -> retrieval.Retriever:
    return __FORMAT_MAPPING[datasource_definition.backend.format](datasource_definition)


class JSONDataRetriever(retrieval.Retriever):
    @classmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """
        return "input_data"

    @property
    def definition(self) -> specification.DataSourceSpecification:
        return self._definition

    @classmethod
    def get_format(cls) -> str:
        return "json"

    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        documents = {
            str(source): util.data_to_dictionary(self.backend.read(source))
            for source in self.backend.sources
        }

        frames = dict()

        for document_name, document in documents.items():  # type: str, typing.Dict[str, typing.Any]
            frame = None
            for selector in self.definition.value_selectors:
                if selector.where == "constant":
                    continue

                selected_data = reader.select_values(document, selector)

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

            constants = [
                selector
                for selector in self.definition.value_selectors
                if selector.where == 'constant'
            ]

            frame_index = frame.index

            for constant in constants:
                value = constant.to_datatype(constant.path[0])
                constant_frame = pandas.DataFrame(
                        data={constant.name: [value for _ in range(len(frame_index))]},
                        index=frame_index
                )
                frame = frame.join(constant_frame)

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


class FrameDataRetriever(retrieval.Retriever):
    @classmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """
        return "input_data"

    @property
    def definition(self) -> specification.DataSourceSpecification:
        return self._definition

    @classmethod
    def get_format(cls) -> str:
        return "csv"

    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
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
            elif common.is_sequence_type(value) and common.is_sequence_type(provided_parameters[option]):
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
            try:
                document = pandas.read_csv(self.backend.read_stream(source), **provided_parameters)
            except Exception as e:
                logging.error(f"Failed to read {source}", exc_info=e)
                raise

            column_names: typing.List[str] = list()

            variable_selectors = [
                selector
                for selector in self.definition.value_selectors
                if selector.where.lower() != 'constant'
            ]

            for selector in variable_selectors:
                if selector.where.lower() != 'column':
                    raise ValueError(f"Column to be found in a '{selector.where}' is not valid for csv data.")

                if selector.name not in document.keys():
                    raise KeyError(f"There is not a column named '{selector.name}' in '{source}'")

                if selector.name not in column_names:
                    column_names.append(selector.name)

                for index in selector.associated_fields:
                    if index.name not in document.keys():
                        raise KeyError(f"There is not a column named '{index.name}' in '{source}'")

                    if index.name not in column_names:
                        column_names.append(index.name)

            table: pandas.DataFrame = document[column_names]

            if self.definition.locations.identify and self.definition.locations.from_field.lower() == 'filename':
                file_name_without_extension = os.path.splitext(os.path.basename(source))[0]
                pattern = self.definition.locations.pattern

                path_to_check = os.path.join(*pattern) if common.is_sequence_type(pattern) else pattern
                search_results = re.search(
                        path_to_check,
                        file_name_without_extension
                )

                name = search_results.group() if search_results else file_name_without_extension

                table = table.assign(location=[name for _ in range(len(table))])

            if self.definition.unit.value:
                index = table.index
                unit_field = pandas.Series(data=[self.definition.unit.value for _ in range(len(index))], index=index)
                table['unit'] = unit_field

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

            constants = [
                selector for selector in self.definition.value_selectors
                if selector.where == 'constant'
            ]

            frame_index = table.index

            for constant in constants:
                values = {
                    constant.name: [
                        constant.to_datatype(constant.path[0])
                        for _ in range(len(frame_index))
                    ]
                }
                constant_frame = pandas.DataFrame(data=values, index=frame_index)
                table = table.join(constant_frame)

            if combined_table is None:
                combined_table = table
            else:
                combined_table = pandas.concat([combined_table, table])

        return combined_table


__FORMAT_MAPPING = {
    "json": JSONDataRetriever,
    "csv": FrameDataRetriever
}
