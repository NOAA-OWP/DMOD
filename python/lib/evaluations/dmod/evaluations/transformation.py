#!/usr/bin/env python3
import typing
import abc

import pandas

from . import specification
from . import util


class TransformationFunction(typing.Callable[[pandas.DataFrame, str, typing.Optional[str]], pandas.DataFrame]):
    """
    A function used to transform values in a data frame into a whole other datatype, series,
    or anything else necessary for processing
    """
    @abc.abstractmethod
    def __call__(
            self,
            initial_frame: pandas.DataFrame,
            observation_key: str,
            prediction_key: str = None,
            *args,
            **kwargs
    ):
        ...


class ReindexTransformation(TransformationFunction):
    """
    A transformation function that translates one dataframe index into another
    """
    def __init__(self, application_rules: specification.ThresholdApplicationRules):
        self._application_rules = application_rules

    def __call__(
            self,
            initial_frame: pandas.DataFrame,
            observation_key: str,
            prediction_key: str = None,
            *args,
            **kwargs
    ):
        perform_on_observations = self._application_rules.observation_field is not None

        if not perform_on_observations:
            return initial_frame

        observation_rules = self._application_rules.observation_field

        result_frame = initial_frame.copy()

        # If there is just one value, we just need to pass it for conversion, otherwise we need to pass multiple fields
        if len(observation_rules.path) == 1:
            result_frame[observation_rules.name] = result_frame[observation_rules.path[0]].apply(observation_rules.to_datatype)

            if util.is_indexed(result_frame):
                result_frame = result_frame.reset_index()
            else:
                result_frame = result_frame.reset_index(drop=True)

        else:
            result_frame[observation_rules.name] = result_frame[observation_rules.path].apply(observation_rules.to_datatype, axis=1)

        result_frame = result_frame.set_index(observation_rules.name)

        return result_frame






