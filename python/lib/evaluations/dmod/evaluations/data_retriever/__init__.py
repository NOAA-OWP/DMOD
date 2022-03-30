
from .. import specification

from .dataretriever import DataRetriever

from . import disk

__RETRIEVER_MAPPING = {
    "file": disk
}


def get_datasource(datasource_definition: specification.DataSourceSpecification) -> DataRetriever:
    if datasource_definition.backend.type not in __RETRIEVER_MAPPING:
        raise ValueError(f"'{datasource_definition.backend.type}' is not a valid type of data backend")

    return __RETRIEVER_MAPPING[datasource_definition.backend.type].get_datasource(datasource_definition)

