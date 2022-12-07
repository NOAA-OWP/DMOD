#!/usr/bin/env python
import typing
import string
import abc
import re

from collections import defaultdict
from collections import abc as abstract_collections

from math import inf as infinity

import pandas
import numpy

from .threshold import Threshold
from .communication import Verbosity
from .communication import CommunicatorGroup

ARGS = typing.Optional[typing.Sequence]
KWARGS = typing.Optional[typing.Dict[str, typing.Any]]
NUMBER = typing.Union[int, float]

METRIC = typing.Callable[[pandas.DataFrame, pandas.DataFrame, typing.Sequence["Threshold"], ARGS, KWARGS], NUMBER]
NUMERIC_OPERATOR = typing.Callable[[NUMBER, NUMBER, typing.Optional[NUMBER]], NUMBER]
NUMERIC_TRANSFORMER = typing.Callable[[NUMBER], NUMBER]
NUMERIC_FILTER = typing.Callable[[NUMBER, NUMBER], bool]
FRAME_FILTER = typing.Callable[[pandas.DataFrame], pandas.DataFrame]


EPSILON = 0.0001

WHITESPACE_PATTERN = re.compile(f"[{string.whitespace}]+")


def scale_value(metric: "Metric", raw_value: NUMBER) -> NUMBER:
    if numpy.isnan(raw_value):
        return numpy.nan

    rise = 0
    run = 1

    if metric.has_ideal_value and metric.bounded:
        if metric.ideal_value == metric.lower_bound:
            # Lower should be higher and the max scale factor is 1.0 and the minimum is 0.0
            rise = -1
            run = metric.upper_bound - metric.lower_bound
        elif metric.ideal_value == metric.upper_bound:
            # lower should stay lower, meaning that the the scale should move from 0 to 1
            rise = 1
            run = metric.upper_bound - metric.lower_bound
        elif metric.lower_bound < metric.ideal_value < metric.upper_bound and raw_value <= metric.ideal_value:
            rise = 1
            run = metric.ideal_value - metric.lower_bound
        elif metric.lower_bound < metric.ideal_value < metric.upper_bound and raw_value > metric.ideal_value:
            rise = -1
            run = metric.upper_bound - metric.ideal_value

        slope = rise / run
        y_intercept = 1 - (slope * metric.ideal_value)
        scaled_value = slope * raw_value + y_intercept

        if metric.has_upper_bound:
            scaled_value = min(scaled_value, metric.upper_bound)

        if metric.has_lower_bound:
            scaled_value = max(scaled_value, metric.lower_bound)

        return scaled_value
    return raw_value


def create_identifier(name: str) -> str:
    """
    Returns an identifier that may be compared against other strings for identification

    This will convert "Pearson Correlation Coefficient" to "pearsoncorrelationcoefficient"

    If a function tries to find a metric by name, it can compare and find the metric with values like
    "pEArSoNcOrreLaTionC oeffIcIEnT" or "pearson correlation_coefficient"

    Returns:
        An identifier that may be compared against other strings for identification
    """
    identifier = WHITESPACE_PATTERN.sub("", name)
    identifier = identifier.replace("_", "")
    identifier = identifier.replace(chr(45), "")
    identifier = identifier.replace(chr(8211), "")
    identifier = identifier.lower()
    return identifier


class Metric(
    abc.ABC,
    typing.Callable[[pandas.DataFrame, str, str, typing.Optional[typing.Sequence[Threshold]], ARGS, KWARGS], "Scores"]
):
    """
    A functional that may be called to evaluate metrics based around thresholds, providing access to attributes
    such as its name and bounds
    """
    def __init__(
        self,
        weight: NUMBER,
        lower_bound: NUMBER = -infinity,
        upper_bound: NUMBER = infinity,
        ideal_value: NUMBER = numpy.nan,
        failure: NUMBER = None,
        greater_is_better: bool = True
    ):
        """
        Constructor

        Args:
            weight: The relative, numeric significance of the metric itself
            lower_bound: The lowest acknowledged value - this doesn't necessarily need to be the lower bound of the statistical function
            upper_bound: The highest acknowledged value - this doesn't necessarily need to be the upper bound of the statistical function
            ideal_value: The value deemed to be perfect for the metric
            failure: A value indicating a complete failure for the metric, triggering a failure among all accompanying metrics
            greater_is_better: Whether or not a higher value is perferred over a lower value
        """
        if weight is None or not (isinstance(weight, int) or isinstance(weight, float)) or numpy.isnan(weight):
            raise ValueError("Weight must be supplied and must be numeric")

        self.__lower_bound = lower_bound if lower_bound is not None else -infinity
        self.__upper_bound = upper_bound if upper_bound is not None else infinity
        self.__ideal_value = ideal_value if ideal_value is not None else numpy.nan
        self.__weight = weight
        self.__greater_is_better = greater_is_better if greater_is_better is not None else True
        self.__failure = failure

    @classmethod
    @abc.abstractmethod
    def get_descriptions(cls):
        """
        Returns:
            A description of how the metric works and how it's supposed be be interpreted
        """
        pass

    @classmethod
    def get_identifier(cls) -> str:
        """
        Returns an identifier that may be compared against other strings for identification

        This will convert "Pearson Correlation Coefficient" to "pearsoncorrelationcoefficient"

        If a function tries to find a metric by name, it can compare and find the metric with values like
        "pEArSoNcOrreLaTionC oeffIcIEnT" or "pearson correlation_coefficient"

        Returns:
            An identifier that may be compared against other strings for identification
        """
        return create_identifier(cls.get_name())

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the metric
        """
        return self.get_name()

    @property
    def fails_on(self) -> NUMBER:
        """
        Returns:
            The value that might trigger a failing evaluation
        """
        return self.__failure

    @property
    def weight(self) -> NUMBER:
        """
        Returns:
            The relative numeric significance of the metric
        """
        return self.__weight

    @property
    def ideal_value(self) -> NUMBER:
        """
        Returns:
            The perfect value
        """
        return self.__ideal_value

    @property
    def lower_bound(self) -> NUMBER:
        """
        The lowest possible value to consider when scaling the result

        NOTE: While the lower and upper bound generally correspond to the upper and lower bound of the metric,
              the lower bound on this corresponds to the lowers number that has any affect on the scaling process.
              For instance, a metric might have a bounds of [-1, 1], but we only want to consider [0, 1] for scoring
              purposes, where anything under 0 is translated as 0

        Returns:
            The lowest value to consider when scaling
        """
        return self.__lower_bound

    @property
    def upper_bound(self) -> NUMBER:
        """
        The highest possible value to consider when scaling the result

        NOTE: While the lower and upper bound generally correspond to the upper and lower bound of the metric,
              the lower bound on this corresponds to the lowers number that has any affect on the scaling process.
              For instance, a metric might have a bounds of [-1, 1], but we only want to consider [0, 1] for scoring
              purposes, where anything under 0 is translated as 0

        Returns:
            The highest value to consider when scaling
        """
        return self.__upper_bound

    @property
    def greater_is_better(self) -> bool:
        """
        Returns:
            Whether or not a greater value is considered better
        """
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

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        pass

    @abc.abstractmethod
    def __call__(
        self,
        pairs: pandas.DataFrame,
        observed_value_label: str,
        predicted_value_label: str,
        thresholds: typing.Sequence[Threshold] = None,
        communicators: CommunicatorGroup = None,
        *args,
        **kwargs
    ) -> "Scores":
        pass

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "Metric(name=" + self.name + ")"


class Score(object):
    def __init__(self, metric: Metric, value: NUMBER, threshold: Threshold = None, sample_size: int = None):
        self.__metric = metric
        self.__value = value
        self.__threshold = threshold or Threshold.default()
        self.__sample_size = sample_size or numpy.nan

    @property
    def value(self) -> NUMBER:
        return self.__value

    @property
    def scaled_value(self) -> NUMBER:
        return scale_value(self.__metric, self.__value) * self.__metric.weight

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

        return bool(failed)

    @property
    def sample_size(self):
        return self.__sample_size

    def __len__(self):
        return self.__sample_size

    def __str__(self) -> str:
        return f"{self.metric} => ({self.threshold}: {self.scaled_value})"

    def __repr__(self) -> str:
        return self.__str__()


class Scores(abstract_collections.Sized, abstract_collections.Iterable):
    def __len__(self) -> int:
        return len(self.__results)

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

        return sum([
            score.scaled_value
            for score in self.__results.values()
            if not numpy.isnan(score.sample_size)
               and score.sample_size > 0
               and not numpy.isnan(score.scaled_value)
        ])

    @property
    def performance(self) -> float:
        valid_scores: typing.List[Score] = [
            score
            for score in self
            if not numpy.isnan(score.sample_size)
               and score.sample_size > 0
        ]
        max_possible = sum([score.threshold.weight for score in valid_scores])
        return self.total / max_possible if max_possible else numpy.nan

    def to_dict(self) -> dict:
        score_representation = {
            "total": self.total,
            "grade": "{:.2f}%".format(self.performance) if not numpy.isnan(self.performance) else None,
            "scores": dict()
        }

        for threshold, score in self.__results.items():  # type: Threshold, Score
            score_representation['scores'][str(threshold)] = {
                "value": score.value,
                "scaled_value": score.scaled_value,
                "sample_size": score.sample_size,
                "failed": score.failed,
                "weight": score.threshold.weight,
                "grade": score.scaled_value / score.threshold.weight if score.threshold.weight else numpy.NaN,
            }

        return score_representation

    def __getitem__(self, key: typing.Union[str, Threshold]) -> Score:
        if isinstance(key, Threshold):
            key = key.name

        for threshold, score in self.__results.items():
            if threshold.name == key:
                return score

        raise ValueError(f"There is not a score for '{key}'")

    def __iter__(self):
        return iter(self.__results.values())

    def __str__(self) -> str:
        return ", ".join([str(score) for score in self.__results])

    def __repr__(self) -> str:
        return self.__str__()


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

    def rows(self, include_metadata: bool = None) -> typing.List[typing.Dict[str, typing.Any]]:
        if include_metadata is None:
            include_metadata = False

        rows = list()

        for threshold, scores in self.__results.items():
            threshold_rows: typing.List[dict] = list()

            threshold_values = list(threshold.value) if isinstance(threshold.value, pandas.Series) else threshold.value
            threshold_value_is_sequence = isinstance(threshold.value, typing.Sequence)
            threshold_value_is_sequence &= not isinstance(threshold.value, str)

            threshold_value = threshold_values[0] if threshold_value_is_sequence else threshold.value

            for score in scores:
                row_values = dict()
                row_values['threshold_name'] = threshold.name
                row_values['threshold_weight'] = threshold.weight
                row_values['result'] = score.value
                row_values['scaled_result'] = score.scaled_value
                row_values['metric'] = score.metric.name
                row_values['metric_weight'] = score.metric.weight

                if include_metadata:
                    row_values['threshold_value'] = threshold_value
                    row_values['desired_metric_value'] = score.metric.ideal_value
                    row_values['failing_metric_value'] = score.metric.fails_on
                    row_values['metric_lower_bound'] = score.metric.lower_bound
                    row_values['metric_upper_bound'] = score.metric.upper_bound

                threshold_rows.append(row_values)

            rows.extend(threshold_rows)
        return rows

    def to_dataframe(self, include_metadata: bool = None) -> pandas.DataFrame:
        rows = self.rows(include_metadata)
        return pandas.DataFrame(rows)

    @property
    def maximum_value_per_threshold(self) -> NUMBER:
        total_value_per_threshold = 0
        for threshold_scores in self.__results.values():
            for score in threshold_scores:
                total_value_per_threshold += score.metric.weight
            break
        return total_value_per_threshold

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
    def populated_thresholds(self) -> typing.Dict[Threshold, typing.List[Score]]:
        populated_keys: typing.List[str] = list()
        for threshold, scores in self.__results.items():
            has_populated_scores = len([score for score in scores if not numpy.isnan(score.value)]) > 0
            if has_populated_scores:
                populated_keys.append(threshold.name)
        return {
            threshold: scores
            for threshold, scores in self.__results.items()
            if threshold.name in populated_keys
        }

    @property
    def total_of_populated_thresholds(self) -> NUMBER:
        populated_total = numpy.nan
        count = 0
        for threshold in self.populated_thresholds:
            threshold_score = self.score_threshold(threshold)

            if numpy.isnan(threshold_score):
                threshold_score = 0
            else:
                threshold_factor = threshold_score / self.maximum_value_per_threshold
                threshold_score = threshold.weight * threshold_factor
            count += 1
            populated_total = self.__aggregator(populated_total, threshold_score, count)

        return populated_total

    @property
    def total(self) -> NUMBER:
        total_score = numpy.nan
        count = 0
        max_per_threshold = self.maximum_value_per_threshold

        for threshold in self.__results.keys():
            threshold_score = self.score_threshold(threshold)

            if numpy.isnan(threshold_score):
                threshold_score = 0
            else:
                threshold_factor = threshold_score / max_per_threshold
                threshold_score = threshold.weight * threshold_factor
            count += 1

            total_score = self.__aggregator(total_score, threshold_score, count)

        return total_score

    def keys(self) -> typing.KeysView:
        return self.__results.keys()

    def values(self) -> typing.ValuesView:
        return self.__results.values()

    @property
    def weight(self):
        return self.__weight

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

    def __iter__(self) -> typing.Iterator[typing.Tuple[Threshold, typing.List[Score]]]:
        return iter(self.__results.items())


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
        aggregator: NUMERIC_OPERATOR = None,
        communicators: CommunicatorGroup = None
    ):
        self.__aggregator = aggregator or ScoringScheme.get_default_aggregator()
        self.__metrics = metrics or list()
        self.__communicators = communicators or CommunicatorGroup()

    def score(
        self,
        pairs: pandas.DataFrame,
        observed_value_label: str,
        predicted_value_label: str,
        thresholds: typing.Sequence[Threshold] = None,
        weight: NUMBER = None,
        metadata: dict = None,
        *args,
        **kwargs
    ) -> MetricResults:
        if len(self.__metrics) == 0:
            raise ValueError(
                "No metrics were attached to the scoring scheme - values cannot be scored and aggregated"
            )

        weight = 1 if not weight or numpy.isnan(weight) else weight

        results = MetricResults(aggregator=self.__aggregator, weight=weight)

        for metric in self.__metrics:  # type: Metric
            self.__communicators.info(f"Calling {metric.name}", verbosity=Verbosity.LOUD, publish=True)
            scores = metric(
                pairs=pairs,
                observed_value_label=observed_value_label,
                predicted_value_label=predicted_value_label,
                thresholds=thresholds,
                *args,
                **kwargs
            )
            results.add_scores(scores)

            if self.__communicators.send_all():
                message = {
                    "metric": scores.metric.name,
                    "description": scores.metric.get_descriptions(),
                    "weight": scores.metric.weight,
                    "total": scores.total,
                    "scores": scores.to_dict()
                }

                if metadata:
                    message['metadata'] = metadata

                self.__communicators.write(reason="metric", data=message, verbosity=Verbosity.ALL)

        return results
