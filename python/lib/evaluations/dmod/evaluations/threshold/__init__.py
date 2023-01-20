import os


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
]

from . import *

import typing

from collections import defaultdict

import pandas

from dmod.metrics.threshold import Threshold

import dmod.core.common as common

from .. import specification
from .. import retrieval


def get_threshold_retriever(threshold_definition: specification.ThresholdSpecification) -> retrieval.Retriever:
    threshold_format = threshold_definition.backend.format.lower()

    possible_retrievers = [
        cls for cls in common.get_subclasses(retrieval.Retriever)
        if cls.get_purpose() == 'thresholds'
           and cls.get_format().lower() == threshold_format
    ]

    if not possible_retrievers:
        message = f"There are no threshold retrievers for '{threshold_format}' through " \
                  f"'{threshold_definition.backend.type}'(s)"
        raise ValueError(message)

    return possible_retrievers[0](threshold_definition)


def get_thresholds(threshold_definition: specification.ThresholdSpecification) -> typing.Dict[str, typing.Sequence[Threshold]]:
    """
    Creates a dictionary mapping a location identifier (ThresholdSpecification.locations.pattern[-1]) to a series
    of Thresholds to be sent to the metrics library

    Args:
        threshold_definition:
            The definition of how all thresholds should work
    Returns:
        A dictionary mapping locations to their thresholds
    """
    threshold_retriever = get_threshold_retriever(threshold_definition)
    threshold_data: pandas.DataFrame = threshold_retriever.retrieve()

    thresholds: typing.Dict[str, typing.List[Threshold]] = defaultdict(list)

    groupby_columns = ['name', threshold_definition.locations.pattern[-1]]

    for identifiers, group in threshold_data.groupby(by=groupby_columns, as_index=False):  # type: tuple, pandas.DataFrame
        extra_kwargs = dict()

        if threshold_definition.application_rules is None:
            extra_kwargs['observed_value_key'] = "observation"
        else:
            rules = threshold_definition.application_rules

            on_observation = rules.observation_field is not None and bool(rules.observation_field)
            if on_observation:
                extra_kwargs['observed_value_key'] = "observation"
            else:
                extra_kwargs['on_observed'] = False

            on_prediction = bool(rules.prediction_field)

            if on_prediction:
                extra_kwargs['on_predicted'] = True
                extra_kwargs['predicted_value_key'] = "prediction"

                # TODO: Build custom transformation function if needed

        new_threshold = Threshold(
                name=identifiers[0],
                value=group.value,
                weight=threshold_definition[identifiers[0]].weight,
                **extra_kwargs
        )

        thresholds[identifiers[1]].append(new_threshold)

    return thresholds
