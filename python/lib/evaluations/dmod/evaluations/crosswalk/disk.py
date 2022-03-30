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
        observations = reader.select_values(self._document.data, self.observation_fields)
        observations.rename(inplace=True, columns={"location": "observed_location"})

        predictions = reader.select_values(self._document.data, self.prediction_fields)
        predictions.rename(inplace=True, columns={"location": "predicted_location"})

        crosswalked_data = observations.join(predictions)
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


