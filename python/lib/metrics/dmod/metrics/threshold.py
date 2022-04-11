"""
Defines formalized Threshold objects that serve as functions for subsetting data
"""

import typing

from math import inf as infinity

import pandas
import numpy

NUMBER = typing.Union[int, float, pandas.Series]

PANDAS_DATA = typing.Union[pandas.DataFrame, pandas.Series]

NUMERIC_FILTER = typing.Callable[[NUMBER, NUMBER], bool]
FRAME_FILTER = typing.Callable[[PANDAS_DATA], PANDAS_DATA]
INDEX_TRANSFORMATION_FUNCTION = typing.Callable[[PANDAS_DATA, typing.Optional[str], typing.Optional[str]], PANDAS_DATA]


class Operators(object):
    """
    A collection of stock comparators that form threshold operators
    """

    @staticmethod
    def get_method(name: str) -> NUMERIC_FILTER:
        """
        Gets a thresholding function based on a name representation

        Supported Operators:
        * ">", 'greater_than', 'greater than'
        * ">=", 'greater_than_or_equal', 'greater than or equal', 'greater than or equal to'
        * "<", 'less_than', 'less than'
        * "<=", "less_than_or_equal", 'less than or equal', 'less than or equal to'
        * is', '=', '==', 'equal', 'equals', 'equal to'

        Args:
            name: The name of the operator to use

        Returns:

        """
        name = name.lower()

        if name in [">", 'greater_than']:
            return Operators.greater_than

        if name in [">=", 'greater_than_or_equal']:
            return Operators.greater_than_or_equal

        if name in ["<", 'less_than']:
            return Operators.less_than

        if name in ["<=", "less_than_or_equal"]:
            return Operators.less_than_or_equal

        if name in ['is', '=', '==', 'equal', 'equals']:
            return Operators.equal

        raise ValueError(f"{name} is not a valid threshold operator")

    @staticmethod
    def greater_than(first, second) -> bool:
        return first > second

    @staticmethod
    def greater_than_or_equal(first, second) -> bool:
        return first >= second

    @staticmethod
    def equal(first, second) -> bool:
        return first == second

    @staticmethod
    def less_than(first, second) -> bool:
        return first < second

    @staticmethod
    def less_than_or_equal(first, second) -> bool:
        return first <= second

    def __init__(self, operator_name: str):
        self.__operator_function: NUMERIC_FILTER = Operators.get_method(operator_name)

    def __call__(self, first: NUMBER, second: NUMBER) -> bool:
        return self.__operator_function(first, second)


class Threshold(FRAME_FILTER):
    @staticmethod
    def default() -> "Threshold":
        return Threshold(name="All", value=-infinity, weight=1, on_observed=False, on_predicted=False)

    def __init__(
            self,
            name: str,
            value: NUMBER,
            weight: NUMBER,
            on_observed: bool = True,
            on_predicted: bool = False,
            observed_value_key: str = None,
            predicted_value_key: str = None,
            operator: NUMERIC_FILTER = None,
            transformation_function: INDEX_TRANSFORMATION_FUNCTION = None
    ):
        data_is_existent = value is not None

        if data_is_existent and isinstance(value, (pandas.DataFrame, pandas.Series)):
            data_is_existent = not value.empty
        elif data_is_existent:
            data_is_existent &= not numpy.isnan(value)

        if not data_is_existent and None in (name, weight) or numpy.isnan(weight) or not name:
            raise ValueError(
                    f"Thresholds must have a name, a value, and a weight. "
                    f"Received: name='{name}', value='{value}, and weight='{weight}'"
            )

        if on_observed and not observed_value_key:
            raise ValueError(
                    f"The name of the observed column must be given if the threshold named '{name}' "
                    f"is going to be applied to the observed values"
            )

        if on_predicted and not predicted_value_key:
            raise ValueError(
                    f"The name of the predicted column must be given if the threshold named '{name}' "
                    f"is going to be applied to the predicted values"
            )

        self._name = name
        self._value = value
        self._weight = weight
        self._on_predicted = on_predicted
        self._on_observed = on_observed
        self._observed_value_key = observed_value_key
        self._predicted_value_key = predicted_value_key
        self._transformation_function = transformation_function
        self._allow = self._build_filter(value, operator)

    def _build_filter(self, threshold_value: NUMBER, operator: NUMERIC_FILTER = None) -> FRAME_FILTER:
        if operator is None:
            operator = Operators.greater_than_or_equal

        threshold_value_is_pandas = isinstance(threshold_value, pandas.Series)
        threshold_value_is_pandas |= isinstance(threshold_value, pandas.DataFrame)

        def filter_func(frame: PANDAS_DATA) -> PANDAS_DATA:
            if not self._on_observed and not self._on_predicted:
                return frame

            frame_is_series = isinstance(frame, pandas.Series)

            if frame_is_series and not threshold_value_is_pandas:
                return frame[operator(frame, threshold_value)]

            if self._transformation_function:
                frame = self._transformation_function(frame, self._observed_value_key, self._predicted_value_key)

            if frame_is_series:
                frame = frame.to_frame().join(threshold_value[self._name])

            if threshold_value_is_pandas:
                threshold = frame[self._name]
            else:
                threshold = threshold_value

            if frame_is_series:
                return frame[operator(frame, threshold)]

            if self._on_observed and self._on_predicted:
                allow_sequence = operator(frame[self._observed_value_key], threshold)
                allow_sequence &= operator(frame[self._predicted_value_key], threshold)
                return frame[allow_sequence]
            elif self._on_observed:
                return frame[operator(frame[self._observed_value_key], threshold)]

            return frame[operator(frame[self._predicted_value_key], threshold)]

        return filter_func

    def __call__(self, pairs: PANDAS_DATA) -> PANDAS_DATA:
        return self._allow(pairs)

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> NUMBER:
        return self._value

    @property
    def weight(self) -> NUMBER:
        return self._weight

    def __str__(self) -> str:
        return f"{self.name}"

    def __repr__(self) -> str:
        return f"Threshold(name={self.name}, value={self.value}, weight={self.weight})"
