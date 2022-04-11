import typing

import pandas

from dmod.metrics.threshold import Threshold

from .. import specification

from .retriever import ThresholdRetriever

from . import disk

__RETRIEVER_MAPPING = {
    "file": disk
}


def get_threshold_retriever(threshold_definition: specification.ThresholdSpecification) -> ThresholdRetriever:
    if threshold_definition.backend.type not in __RETRIEVER_MAPPING:
        raise ValueError(f"'{threshold_definition.backend.type}' is not a valid type of threshold")

    return __RETRIEVER_MAPPING[threshold_definition.backend.type].get_datasource(threshold_definition)


def get_thresholds(threshold_definition: specification.ThresholdSpecification) -> typing.Sequence[Threshold]:
    threshold_retriever = get_threshold_retriever(threshold_definition)
    threshold_data: pandas.DataFrame = threshold_retriever.get_data()

    thresholds: typing.List[Threshold] = list()

    for definition in threshold_definition.definitions:
        new_threshold = Threshold(
                name=definition.name,
                value=threshold_data[definition.field],
                weight=definition.weight
        )

    return thresholds


