import typing
import json

import pandas
from dmod.core.common.collections import catalog

from .. import reader
from .. import specification

from . import retriever


# TODO: Implement
class FrameRetriever(retriever.CrosswalkRetriever):
    """
    Retrieves crosswalk data from tabulated formats, typically CSV
    """
    ...


class JSONCrosswalkRetriever(retriever.CrosswalkRetriever):
    """
    Retrieves crosswalk data from JSON formats
    """
    @classmethod
    def get_type(cls) -> str:
        return "file"

    @classmethod
    def get_format(cls) -> str:
        return "json"

    def retrieve(self, *args, **kwargs) -> pandas.DataFrame:
        crosswalked_data = reader.select_values(self._document, self.field)

        if not (crosswalked_data is None or crosswalked_data.empty):
            crosswalked_data.dropna(inplace=True)

        return crosswalked_data

    def __init__(self, definition: specification.CrosswalkSpecification, input_catalog: catalog.InputCatalog):
        super().__init__(definition, input_catalog=input_catalog)

        full_document: typing.Dict[str, typing.Any] = {}

        for crosswalk_source in self.backend.sources:
            document = json.loads(self.backend.read(crosswalk_source))
            if not isinstance(document, dict):
                raise ValueError(
                        f"'{crosswalk_source}' is not a valid source for crosswalk data. "
                        f"Only standard JSON data is allowed."
                )
            full_document.update(document)

        self._document = full_document
