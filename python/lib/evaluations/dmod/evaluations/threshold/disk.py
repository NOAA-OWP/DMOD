"""
Defines threshold retrievers for formats that generally originate from disk
"""
import abc
import io
import typing
import os
import re
import inspect

import pandas
# TODO: Use jmespath instead
import jsonpath_ng as jsonpath

from jsonpath_ng.ext import parse as create_expression

from .. import specification
from .. import util
from .. import retrieval


class ThresholdRetriever(retrieval.Retriever[specification.ThresholdSpecification], abc.ABC):
    """
    A retriever that loads threshold data
    """
    @classmethod
    def get_purpose(cls) -> str:
        """
        Returns:
            What type of data this retriever is supposed to get
        """
        return "thresholds"


class JSONThresholdRetriever(ThresholdRetriever):
    """
    Retriever that loads thresholds from a json document
    """
    @classmethod
    def get_format(cls) -> str:
        """
        The format that this retriever reads
        """
        return 'json'

    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        """
        Loads thresholds from a json document

        Args:
            *args:
            **kwargs:

        Returns:
            A dataframe containing the loaded thresholds
        """
        documents = {
            source: util.data_to_dictionary(self.backend.read(source))
            for source in self.backend.sources
        }

        frames = {}

        search_path = ".".join(self.definition.origin)
        base_expression = create_expression(search_path)

        location_key = self.definition.locations.pattern[-1]

        values = {
            "value": [],
            "name": [],
            "weight": [],
            "unit": [],
            location_key: []
        }

        # TODO: See if this loop can be extracted into its own function
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

            # TODO: See if this loop can be extracted into its own funciton
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
                            values[location_key].append(location_name.value)
                    elif location_name:
                        while len(values[location_key]) < len(values['value']):
                            values[location_key].append(location_name)

                    while len(values['name']) < len(values['value']):
                        values['name'].append(threshold.name)

                    while len(values['weight']) < len(values['value']):
                        values['weight'].append(threshold.weight)

            frame = pandas.DataFrame(values)

            if util.is_indexed(frame):
                frame = frame.reset_index()

            frames[document_name] = frame

        combined_frame = pandas.concat(list(frames.values()))

        return combined_frame


class CSVThresholdRetriever(ThresholdRetriever):
    @classmethod
    def get_format(cls) -> str:
        return "csv"

    def load_frame(self, source: str, **kwargs) -> pandas.DataFrame:
        return pandas.read_csv(self.backend.read_stream(source), **kwargs)

    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        constructor_signature = inspect.signature(pandas.read_csv)
        provided_parameters = {
            key: value
            for key, value in self.backend.definition.properties.items()
            if key in constructor_signature.parameters
        }

        if 'date_parser' not in provided_parameters:
            provided_parameters['date_parser'] = util.parse_non_naive_dates

        if self.definition.locations.from_field == 'column':
            if 'dtype' not in provided_parameters:
                provided_parameters['dtype'] = {}

            provided_parameters['dtype'][self.definition.locations.pattern[-1]] = str

        combined_table = None

        for source in self.backend.sources:
            document = self.load_frame(source, **provided_parameters)
            custom_rules = self.definition.application_rules

            column_names: typing.List[str] = [
                threshold_definition.field[-1]
                for threshold_definition in self.definition.definitions
                if threshold_definition.field[-1] in document.keys()
            ]

            column_names.extend([
                threshold_definition.name
                for threshold_definition in self.definition.definitions
                if threshold_definition.name in document.keys()
            ])

            column_names.extend([
                    threshold_definition.unit.path[-1]
                    for threshold_definition in self.definition.definitions
                    if bool(threshold_definition.unit.path)
            ])

            column_names.extend([
                threshold_definition.unit.field
                for threshold_definition in self.definition.definitions
                if bool(threshold_definition.unit.field)
            ])

            if custom_rules and custom_rules.threshold_field.name not in document.keys():
                field = custom_rules.threshold_field

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
                column_names.append(field.name)

            # TODO: This is missing handling for value units

            if self.definition.locations.identify and self.definition.locations.from_field.lower() == 'column':
                column_names.append(self.definition.locations.pattern[-1])

            table: pandas.DataFrame = document[column_names]

            if self.definition.locations.identify and self.definition.locations.from_field.lower() == 'filename':
                file_name_without_extension = os.path.splitext(os.path.basename(source))[0]

                full_pattern = os.pathsep.join(self.definition.locations.pattern)
                search_results = re.search(full_pattern, file_name_without_extension)

                name = search_results.group() if search_results else file_name_without_extension

                table = table.assign(location=[name for _ in range(len(table))])

            if combined_table is None:
                combined_table = table
            else:
                combined_table = pandas.concat([combined_table, table])

        definition_columns = [
            definition.field[-1]
            for definition in self.definition.definitions
            if definition.field[-1] in combined_table.keys()
               and definition.field[-1].lower() not in ("name", "value")
        ]

        if definition_columns:
            id_variables = [self.definition.locations.pattern[-1]]
            threshold_field = None
            if self.definition.application_rules:
                threshold_field = self.definition.application_rules.threshold_field
                id_variables.append(threshold_field.name)

            # This is going to take all the columns that should be rows for threshold values and rotate them
            combined_table = combined_table.melt(id_vars=id_variables, var_name="name")

            # If there was a special rule for thresholding, go ahead and set the index for later joining
            if threshold_field:
                combined_table = combined_table.set_index(threshold_field.name)

        return combined_table


class RDBThresholdRetriever(CSVThresholdRetriever):
    @classmethod
    def get_format(cls) -> str:
        return "rdb"

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
        dtype = dict(zip(column_names, column_types))

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

        if self.definition.application_rules:
            threshold_field = self.definition.application_rules.threshold_field

            # We want pandas to handle the conversion,
            # but only if the threshold field is already present (i.e. not added later)
            if 'dtype' in arguments and threshold_field.name in column_names:
                arguments['dtype'][threshold_field.name] = threshold_field.get_concrete_datatype()
            elif threshold_field.name in column_names:
                arguments['dtype'] = {
                    threshold_field.name: threshold_field.get_concrete_datatype()
                }

        frame: pandas.DataFrame = pandas.read_csv(threshold_buffer, **arguments)

        threshold_names = [
            definition.field[-1]
            for definition in self.definition.definitions
        ]

        for threshold_name in threshold_names:
            if threshold_name in frame.keys() and frame[threshold_name].dtype != float:
                frame[threshold_name] = frame[threshold_name].astype(float)

        return frame
