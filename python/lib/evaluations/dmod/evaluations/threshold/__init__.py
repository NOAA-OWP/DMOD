
from .. import specification

from .retriever import ThresholdRetriever

from . import disk

__RETRIEVER_MAPPING = {
    "file": disk
}


def get_thresholds(threshold_definition: specification.ThresholdSpecification) -> ThresholdRetriever:
    if threshold_definition.backend.type not in __RETRIEVER_MAPPING:
        raise ValueError(f"'{threshold_definition.backend.type}' is not a valid type of threshold")

    return __RETRIEVER_MAPPING[threshold_definition.backend.type].get_datasource(threshold_definition)

