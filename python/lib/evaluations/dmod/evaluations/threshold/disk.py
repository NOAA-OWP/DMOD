#!/usr/bin/env python3
import typing
import os
import re
import inspect

import pandas
import jsonpath_ng as jsonpath

from jsonpath_ng.ext import parse as create_expression

from .. import specification
from ..crosswalk import reader
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

                full_pattern = os.pathsep.join(self.definition.locations.pattern)
                search_results = re.search(full_pattern, file_name_without_extension)

                name = search_results.group() if search_results else file_name_without_extension

                table = table.assign(location=[name for _ in range(len(table))])

            if combined_table is None:
                combined_table = table
            else:
                combined_table = pandas.concat([combined_table, table])

        return combined_table


__FORMAT_MAPPING = {
    "json": JSONThresholdRetriever,
    "csv": FrameThresholdRetriever
}
