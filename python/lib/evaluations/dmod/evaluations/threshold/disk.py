#!/usr/bin/env python3
import io
import typing
import os
import re
import inspect

import pandas
import jsonpath_ng as jsonpath

from jsonpath_ng.ext import parse as create_expression

from .. import specification
from .. import jsonquery
from .. import util

from . import retriever


def get_datasource(datasource_definition: specification.DataSourceSpecification) -> retriever.ThresholdRetriever:
    return __FORMAT_MAPPING[datasource_definition.backend.format](datasource_definition)


class JSONThresholdRetriever(retriever.ThresholdRetriever):
    def get_data(self) -> pandas.DataFrame:
        documents = {
            source: jsonquery.Document(self.backend.get_data(source)).data
            for source in self.backend.sources
        }

        frames = dict()

        search_path = ".".join(self.definition.origin)
        base_expression = create_expression(search_path)

        values = {
            "value": list(),
            "name": list(),
            "weight": list(),
            "unit": list(),
            "location": list()
        }

        for document_name, document in documents.items():  # type: str, dict
            base = base_expression.find(document)

            location_name = None

            if self.definition.locations.from_field.lower() == "filename":
                location_name = None

                if self.definition.locations.pattern:
                    search_results = re.search(os.path.pathsep.join(self.definition.locations.pattern), document_name)
                    if search_results:
                        location_name = search_results.group()

                if not location_name:
                    location_name = os.path.splitext(os.path.basename(document_name))[0]

            for branch_entry in base:  # type: jsonpath.DatumInContext
                branch = str(branch_entry.full_path)
                for threshold in self.definition.definitions:  # type: specification.ThresholdDefinition
                    path = branch + "." + ".".join(threshold.field)
                    threshold_expression = create_expression(path)

                    for result in threshold_expression.find(document):
                        values['value'].append(result.value)

                    unit_path = branch + "." + ".".join(threshold.unit.path)
                    unit_expression = create_expression(unit_path)

                    for unit in unit_expression.find(document):
                        values['unit'].append(unit.value)

                    if self.definition.locations.from_field.lower() == 'value':
                        location_path = branch + "." + ".".join(self.definition.locations.pattern)
                        location_expression = create_expression(location_path)

                        for location_name in location_expression.find(document):
                            values['location'].append(location_name.value)
                    elif location_name:
                        while len(values['location']) < len(values['value']):
                            values['location'].append(location_name)

                    while len(values['name']) < len(values['value']):
                        values['name'].append(threshold.name)

                    while len(values['weight']) < len(values['value']):
                        values['weight'].append(threshold.weight)

            frame = pandas.DataFrame(values)

            if util.is_indexed(frame):
                frame = frame.reset_index()

            frames[document_name] = frame

        combined_frame = pandas.concat([frame for frame in frames.values()])

        return combined_frame


class FrameThresholdRetriever(retriever.ThresholdRetriever):
    def load_frame(self, source: str, **kwargs) -> pandas.DataFrame:
        return pandas.read_csv(self.backend.get_data_stream(source), **kwargs)

    def get_data(self) -> pandas.DataFrame:
        constructor_signature = inspect.signature(pandas.read_csv)
        provided_parameters = {
            key: value
            for key, value in self.backend.definition.properties.items()
            if key in constructor_signature.parameters
        }

        if 'date_parser' not in provided_parameters:
            provided_parameters['date_parser'] = util.parse_non_naive_dates

        combined_table = None

        for source in self.backend.sources:
            document = self.load_frame(source, **provided_parameters)

            if self.definition.application_rules:
                field = self.definition.application_rules.threshold_field

                def conversion_function(column_name_and_value: pandas.Series):
                    """
                    Converts a series of column names vs values to the desired data type

                    Args:
                        column_name_and_value:
                            A pandas Series mapping column names to values
                    Returns:
                        The converted value
                    """
                    converted_value = field.to_datatype([value for value in column_name_and_value])
                    return converted_value

                document[field.name] = document[field.path].apply(conversion_function, axis=1)
                document = document.set_index(field.name)

            column_names: typing.List[str] = [
                threshold_definition.field[-1]
                for threshold_definition in self.definition.definitions
            ]

            if self.definition.locations.should_identify and self.definition.locations.from_field.lower() == 'column':
                column_names.append(self.definition.locations.pattern[-1])

            table: pandas.DataFrame = document[column_names]

            if self.definition.locations.should_identify and self.definition.locations.from_field.lower() == 'filename':
                file_name_without_extension = os.path.splitext(os.path.basename(source))[0]

                full_pattern = os.pathsep.join(self.definition.locations.pattern)
                search_results = re.search(full_pattern, file_name_without_extension)

                name = search_results.group() if search_results else file_name_without_extension

                table = table.assign(location=[name for _ in range(len(table))])

            renames = {
                threshold_definition.field[-1]: threshold_definition.name
                for threshold_definition in self.definition.definitions
            }

            if renames:
                table.rename(columns=renames, inplace=True)

            if combined_table is None:
                combined_table = table
            else:
                combined_table = pandas.concat([combined_table, table])

        return combined_table


class RDBThresholdRetriever(FrameThresholdRetriever):
    def load_frame(self, source: str, **kwargs) -> pandas.DataFrame:
        with open(source) as threshold_file:
            lines = [
                line
                for line in threshold_file.readlines()
                if not line.startswith("#")
            ]
        column_names = lines[0].strip().split("\t")
        column_types = lines.pop(1).strip().split("\t")
        column_types = [
            float if column_type[-1] == 'n' else str
            for column_type in column_types
        ]
        dtype = {
            column_name: column_type
            for column_name, column_type in zip(column_names, column_types)
        }
        threshold_buffer = io.StringIO()
        threshold_buffer.writelines(lines)
        threshold_buffer.seek(0)

        arguments = kwargs
        arguments['sep'] = '\t'

        if 'dtype' in arguments:
            for column_name, column_type in dtype.items():
                if column_name not in arguments['dtype']:
                    arguments['dtype'][column_name] = column_type
        else:
            arguments['dtype'] = dtype

        frame: pandas.DataFrame = pandas.read_csv(threshold_buffer, **arguments)

        return frame


__FORMAT_MAPPING = {
    "json": JSONThresholdRetriever,
    "csv": FrameThresholdRetriever,
    'rdb': RDBThresholdRetriever
}
