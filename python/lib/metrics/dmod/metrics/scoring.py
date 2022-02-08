#!/usr/bin/env python
import typing
import math
import abc
from collections import defaultdict

from math import inf as infinity

import pandas
import numpy

from dmod.metrics.threshold import Threshold

ARGS = typing.Optional[typing.Sequence]
KWARGS = typing.Optional[typing.Dict[str, typing.Any]]
NUMBER = typing.Union[int, float]

METRIC = typing.Callable[[pandas.DataFrame, pandas.DataFrame, typing.Sequence["Threshold"], ARGS, KWARGS], NUMBER]
NUMERIC_OPERATOR = typing.Callable[[NUMBER, NUMBER, typing.Optional[NUMBER]], NUMBER]
NUMERIC_TRANSFORMER = typing.Callable[[NUMBER], NUMBER]
NUMERIC_FILTER = typing.Callable[[NUMBER, NUMBER], bool]
FRAME_FILTER = typing.Callable[[pandas.DataFrame], pandas.DataFrame]


EPSILON = 0.0001


class Metric(abc.ABC):
    def __init__(
            self,
            weight: NUMBER,
            lower_bound: NUMBER = -infinity,
            upper_bound: NUMBER = infinity,
            ideal_value: NUMBER = numpy.nan,
            failure: NUMBER = None,
            greater_is_better: bool = True
    ):
        self.__lower_bound = lower_bound
        self.__upper_bound = upper_bound
        self.__ideal_value = ideal_value
        self.__weight = weight
        self.__greater_is_better = greater_is_better
        self.__failure = failure

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    def fails_on(self) -> NUMBER:
        return self.__failure

    @property
    def weight(self) -> NUMBER:
        return self.__weight

    @property
    def ideal_value(self) -> NUMBER:
        return self.__ideal_value

    @property
    def greater_is_better(self) -> bool:
        return self.__greater_is_better

    @property
    def has_upper_bound(self) -> bool:
        return not numpy.isnan(self.__upper_bound) and self.__upper_bound < infinity

    @property
    def has_lower_bound(self) -> bool:
        return not numpy.isnan(self.__lower_bound) and self.__lower_bound > -infinity

    @property
    def has_ideal_value(self) -> bool:
        return self.__ideal_value is not None and \
               not numpy.isnan(self.__ideal_value) and \
               not numpy.isinf(self.__ideal_value)

    @property
    def fully_bounded(self) -> bool:
        return self.has_lower_bound and self.has_upper_bound

    @property
    def partially_bounded(self) -> bool:
        return self.has_lower_bound ^ self.has_upper_bound

    @property
    def bounded(self) -> bool:
        return self.has_lower_bound or self.has_upper_bound

    def _scaled_value(self, raw_value: NUMBER) -> NUMBER:
        if numpy.isnan(raw_value):
            return numpy.nan

        scale_factor = 0.0

        if self.has_ideal_value and raw_value == self.__ideal_value:
            scale_factor = 1.0
        elif self.bounded and self.has_ideal_value:
            if self.has_lower_bound:
                lower_distance = self.ideal_value - self.__lower_bound
                lower_bound = self.__lower_bound
            else:
                lower_distance = None
                lower_bound = None

            if self.has_upper_bound:
                upper_distance = self.__upper_bound - self.__ideal_value
                upper_bound = self.__upper_bound
            else:
                upper_distance = None
                upper_bound = None

            if lower_distance is None:
                lower_distance = upper_distance
                lower_bound = self.ideal_value - lower_distance
            elif upper_distance is None:
                upper_distance = lower_distance
                upper_bound = self.__ideal_value + lower_distance

            if raw_value < self.__ideal_value:
                rise = 1
                y_intercept = 0
            else:
                rise = -1
                y_intercept = 1.0

            run = max(upper_distance, lower_distance)

            slope = rise / run

            def line_function(value) -> float:
                return slope * value + y_intercept

            minimum_possible_factor = 0.0

            if raw_value > self.ideal_value and upper_bound < run:
                x = self.ideal_value + upper_distance
                minimum_possible_factor = line_function(x)
            elif raw_value < self.ideal_value and lower_bound < run:
                x = self.ideal_value - lower_distance
                minimum_possible_factor = line_function(x)

            scale_factor = max(line_function(raw_value), minimum_possible_factor)

        scaled_value = raw_value * scale_factor

        return scaled_value

    @abc.abstractmethod
    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[Threshold] = None,
            *args,
            **kwargs
    ) -> "Scores":
        pass

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "Metric(name=" + self.name + ")"


class Score(object):
    def __init__(self, metric: Metric, value: NUMBER, threshold: Threshold = None):
        self.__metric = metric
        self.__value = value
        self.__threshold = threshold or Threshold.default()

    @property
    def value(self) -> NUMBER:
        return self.__value

    @property
    def scaled_value(self) -> NUMBER:
        return self.__value * self.__threshold.weight

    @property
    def metric(self) -> Metric:
        return self.__metric

    @property
    def threshold(self) -> Threshold:
        return self.__threshold

    @property
    def failed(self) -> bool:
        if self.__metric.fails_on is None:
            return False
        elif numpy.isnan(self.__metric.fails_on) and numpy.isnan(self.__value):
            return True
        elif numpy.isnan(self.__metric.fails_on):
            return False

        difference = self.__value - self.__metric.fails_on
        difference = abs(difference)

        failed = difference < EPSILON

        return failed

    def __str__(self) -> str:
        return f"{self.metric} => ({self.threshold}: {self.scaled_value})"


class Scores(object):
    def __init__(self, metric: Metric, scores: typing.Sequence[Score]):
        self.__metric = metric

        self.__results = {
            score.threshold: score
            for score in scores
        }

    @property
    def metric(self) -> Metric:
        return self.__metric

    @property
    def total(self) -> NUMBER:
        if len(self.__results) == 0:
            raise ValueError("There are no scores to total")

        return sum([score.scaled_value for score in self.__results])

    def __getitem__(self, key: typing.Union[str, Threshold]) -> Score:
        if isinstance(key, Threshold):
            key = key.name

        for threshold, score in self.__results.items():
            if threshold.name == key:
                return score

        raise ValueError(f"There is not a score for '{key}'")

    def __iter__(self):
        return iter(self.__results.values())

    @property
    def __str__(self) -> str:
        return ", ".join([str(score) for score in self.__results])


class MetricResults(object):
    def __init__(
            self,
            aggregator: NUMERIC_OPERATOR,
            metric_scores: typing.Sequence[Scores] = None,
            weight: NUMBER = None
    ):
        if not metric_scores:
            metric_scores = list()

        self.__aggregator = aggregator
        self.__results: typing.Dict[Threshold, typing.List[Score]] = defaultdict(list)

        for scores in metric_scores:
            self.add_scores(scores)

        self.__weight = weight or 1

    def score_threshold(self, threshold: Threshold) -> NUMBER:
        threshold_score = numpy.nan

        for score in self.__results[threshold]:
            if score.failed:
                return 0

            scaled_value = score.scaled_value

            if score is None or numpy.isnan(scaled_value):
                continue

            if numpy.isnan(threshold_score):
                threshold_score = scaled_value
            else:
                threshold_score += scaled_value

        return threshold_score

    @property
    def total(self) -> NUMBER:
        total_score = numpy.nan
        count = 0

        for threshold in self.__results.keys():
            threshold_score = self.score_threshold(threshold)
            count += 1
            total_score = self.__aggregator(total_score, threshold_score, count)

        return total_score

    def add_scores(self, scores: Scores):
        for score in scores:
            self.__results[score.threshold].append(score)

    def __getitem__(self, key: str) -> typing.Sequence[Score]:
        result_key = None
        for threshold in self.__results.keys():
            if threshold.name.lower() == key.lower():
                result_key = threshold
                break

        if result_key:
            return self.__results[result_key]

        available_thresholds = [threshold.name for threshold in self.__results.keys()]

        raise KeyError(f"There are no thresholds named '{key}'. Available keys are: {', '.join(available_thresholds)}")

    def __iter__(self) -> typing.ItemsView[Threshold, typing.List[Score]]:
        return self.__results.items()


class ScoringScheme(object):
    @staticmethod
    def get_default_aggregator() -> NUMERIC_OPERATOR:
        def operator(first_score_value: NUMBER, second_score_value: NUMBER, count: NUMBER = None) -> NUMBER:
            if numpy.isnan(first_score_value) and numpy.isnan(second_score_value):
                return numpy.nan
            elif numpy.isnan(first_score_value):
                return second_score_value
            elif numpy.isnan(second_score_value):
                return first_score_value

            return first_score_value + second_score_value
        return operator

    def __init__(
            self,
            metrics: typing.Sequence[Metric] = None,
            aggregator: NUMERIC_OPERATOR = None
    ):
        self.__aggregator = aggregator or ScoringScheme.get_default_aggregator()
        self.__metrics = metrics or list()
    
    def score(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[Threshold] = None,
            weight: NUMBER = None,
            *args,
            **kwargs
    ) -> MetricResults:
        if len(self.__metrics) == 0:
            raise ValueError(
                "No metrics were attached to the scoring scheme - values cannot be scored and aggregated"
            )

        weight = 1 if not weight or numpy.isnan(weight) else weight

        results = MetricResults(aggregator=self.__aggregator, weight=weight)

        for metric in self.__metrics:
            scores = metric(
                pairs=pairs,
                observed_value_label=observed_value_label,
                predicted_value_label=predicted_value_label,
                thresholds=thresholds,
                *args,
                **kwargs
            )
            results.add_scores(scores)

        return results
