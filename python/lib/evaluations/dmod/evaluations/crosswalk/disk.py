import typing
import io
import abc
import json

import pandas

from .. import specification
from .. import jsonquery

from . import retriever
from . import reader


def get_crosswalk_format_map() -> typing.Dict[str, typing.Callable]:
    return {
        "json": JSONRetriever,
        "csv": FrameRetriever
    }


def get_retriever(definition: specification.CrosswalkSpecification) -> retriever.CrosswalkRetriever:
    data_format = definition.backend.format.lower()
    return get_crosswalk_format_map()[data_format](definition)


class FrameRetriever(retriever.CrosswalkRetriever):
    pass


class JSONRetriever(retriever.CrosswalkRetriever):
    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        crosswalked_data = reader.select_values(self._document.data, self.field)

        if self.observation_field_name != 'observed_location' or self.prediction_field_name != 'predicted_location':
            # Rename correct fields to match the config
            if self.observation_field_name != self.prediction_field_name:
                renaming = dict()
                if self.observation_field_name != 'observed_location':
                    renaming[self.observation_field_name] = 'observed_location'
                if self.prediction_field_name != 'predicted_location':
                    renaming[self.prediction_field_name] = 'predicted_location'

                crosswalked_data.rename(columns=renaming, inplace=True)
            else:
                crosswalked_data['predicted_location'] = crosswalked_data[self.observation_field_name]

                if self.observation_field_name != 'observed_location':
                    crosswalked_data.rename(columns={self.observation_field_name: "observed_location"}, inplace=True)

        crosswalked_data.dropna(inplace=True)
        return crosswalked_data

    def __init__(self, definition: specification.CrosswalkSpecification):
        super().__init__(definition)

        full_document: typing.Dict[str, typing.Any] = dict()

        for crosswalk_source in self.backend.sources:
            document = json.load(self.backend.get_data_stream(crosswalk_source))
            if not isinstance(document, dict):
                raise ValueError(
                        f"'{crosswalk_source}' is not a valid source for crosswalk data. "
                        f"Only standard JSON data is allowed."
                )
            full_document.update(document)

        self._document = jsonquery.Document(full_document)


