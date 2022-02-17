"""
Defines formalized Threshold objects that serve as functions for subsetting data
"""

import typing

from math import inf as infinity

import pandas
import numpy

NUMBER = typing.Union[int, float]

PANDAS_DATA = typing.Union[pandas.DataFrame, pandas.Series]

NUMERIC_FILTER = typing.Callable[[NUMBER, NUMBER], bool]
FRAME_FILTER = typing.Callable[[PANDAS_DATA], PANDAS_DATA]


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
            operator: NUMERIC_FILTER = None
    ):
        if None in (name, value, weight) or numpy.nan in (value, weight) or not name:
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

        self.__name = name
        self.__value = value
        self.__weight = weight
        self.__on_predicted = on_predicted
        self.__on_observed = on_observed
        self.__observed_value_key = observed_value_key
        self.__predicted_value_key = predicted_value_key
        self._allow = self.__build_filter(value, operator)

    def __build_filter(self, threshold_value: NUMBER, operator: NUMERIC_FILTER = None) -> FRAME_FILTER:
        if operator is None:
            operator = Operators.greater_than_or_equal

        def filter_func(frame: PANDAS_DATA) -> PANDAS_DATA:
            if isinstance(frame, pandas.Series):
                return frame[operator(frame, threshold_value)]

            if not self.__on_observed and not self.__on_predicted:
                return frame

            if self.__on_observed and self.__on_predicted:
                allow_sequence = operator(frame[self.__observed_value_key], threshold_value)
                allow_sequence = allow_sequence & operator(frame[self.__predicted_value_key], threshold_value)
                return frame[allow_sequence]
            elif self.__on_observed:
                return frame[operator(frame[self.__observed_value_key], threshold_value)]

            return frame[operator(frame[self.__predicted_value_key], threshold_value)]

        return filter_func

    def __call__(self, pairs: PANDAS_DATA) -> PANDAS_DATA:
        return self._allow(pairs)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def value(self) -> NUMBER:
        return self.__value

    @property
    def weight(self) -> NUMBER:
        return self.__weight

    def __str__(self) -> str:
        return f"{self.name}"

    def __repr__(self) -> str:
        return f"Threshold(name={self.name}, value={self.value}, weight={self.weight})"
