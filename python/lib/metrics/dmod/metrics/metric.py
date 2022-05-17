"""
Implementations of different Metrics

References for Metrics:

* Forecast Verification - Issues, Methods and FAQ, Ebert,
    https://www.cawcr.gov.au/projects/verification/verif_web_page.html
"""

import os
import typing
import abc
import math
import inspect
import re
import string
import logging

import numpy
import pandas
import sklearn.metrics

from . import scoring
from . import threshold
from . import categorical
from .threshold import Threshold


logging.basicConfig(
    filename='metrics.log',
    level=logging.getLevelName(os.environ.get('METRIC_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "DEBUG"))),
    format=os.environ.get("LOG_FORMAT", "%(asctime)s,%(msecs)d %(levelname)s: %(message)s"),
    datefmt=os.environ.get("LOG_DATEFMT", "%H:%M:%S")
)

NUMBER = typing.Union[int, float]
DEFAULT_TRUTH_TABLES_KEY = "TRUTH_TABLES"
ROW_INDEX_KEY = typing.Optional[typing.Hashable]
KEY_AND_ROW = typing.Tuple[ROW_INDEX_KEY, pandas.Series]
INFINITY = math.inf
WHITESPACE_PATTERN = re.compile(f"[{string.whitespace}]+")


def is_type(value: object, value_type: typing.Type) -> bool:
    """
    Determines whether or not the given value matches the given type

    This can be used to evaluated types such as unions since you cannot use `isinstance`

    Args:
        value: The value to check
        value_type: The type to check against

    Returns:
        Whether or not the value matches the given type
    """
    value_is_valid = False

    try:
        type_members: typing.Tuple = typing.get_args(value_type)

        # If the given value is not a scalar value, we need to check the types against
        if isinstance(value, typing.Sequence):
            if len(value) == len(type_members):
                for type_index in range(len(type_members)):
                    value_is_valid = isinstance(value[type_index], type_members[type_index])
                    if not value_is_valid:
                        return value_is_valid
            elif len(type_members) == 1:
                value_is_valid = len(
                    [
                        inner_value
                        for inner_value in value
                        if not isinstance(inner_value, type_members[0])
                    ]
                ) == 0
        else:
            for union_arg in typing.get_args(value_type):
                try:
                    value_is_valid |= isinstance(value, union_arg)
                except Exception as comparison_error:
                    logging.warning(f"It could not be checked whether or not '{value}' is of type '{union_arg}'")
                    logging.warning(comparison_error)
    except Exception as inspection_error:
        logging.warning(f"The typing '{value_type}' could not be inspected.")
        logging.error(inspection_error)

    return value_is_valid


def _get_subclasses(klazz: typing.Type[scoring.Metric]) -> typing.Sequence[typing.Type[scoring.Metric]]:
    subclasses: typing.List[typing.Type[scoring.Metric]] = list()

    if inspect.isabstract(klazz):
        for subclass in klazz.__subclasses__():
            subclasses.extend(_get_subclasses(subclass))
    else:
        subclasses.append(klazz)

    return subclasses


def get_all_metrics() -> typing.Iterable[typing.Type[scoring.Metric]]:
    """
    Returns:
        A collection of all fully implemented metrics
    """

    collection = _get_subclasses(scoring.Metric)

    return collection


def get_metric(name: str, weight: float) -> scoring.Metric:
    cleaned_up_name = WHITESPACE_PATTERN.sub("", name)
    cleaned_up_name = cleaned_up_name.replace("_", "")
    cleaned_up_name = cleaned_up_name.replace(chr(45), "")
    cleaned_up_name = cleaned_up_name.replace(chr(8211), "")
    cleaned_up_name = cleaned_up_name.lower()

    matching_metrics: typing.Sequence[typing.Type[scoring.Metric]] = [
        metric for metric in get_all_metrics() if metric.get_identifier() == cleaned_up_name
    ]

    if len(matching_metrics) == 0:
        raise KeyError(f"There are no metrics named '{name}'")

    return matching_metrics[0](weight)


def find_truthtables_key(**kwargs) -> typing.Optional[str]:
    """
    Attempts to find the key corresponding to a TruthTables object within passed in keyword arguments

    Args:
        **kwargs: keyword arguments from another function call

    Returns:
        "TRUTH_TABLES" if there's a TruthTables in the kwargs, otherwise the first TruthTables present if it exists
    """
    # Find all TruthTables in the passed kwargs
    keys = [
        key
        for key, value in kwargs.items()
        if isinstance(value, categorical.TruthTables)
    ]

    # If the default key is in the list of found keys, return that if it's present
    if DEFAULT_TRUTH_TABLES_KEY in keys:
        return DEFAULT_TRUTH_TABLES_KEY

    # Otherwise return the first key if there are any, otherwise return None
    return keys[0] if keys else None


def find_individual_truthtable_keys(**kwargs) -> typing.Iterable[str]:
    """
    Tries to find individual truth tables passed in via keyword arguments rather than through a TruthTables object

    Args:
        **kwargs: The keyword arguments from another function all

    Returns:
        All keys pointing to a single instance of `dmod.categorical.TruthTable`
    """
    return [
        key
        for key, value in kwargs.items()
        if isinstance(value, categorical.TruthTable)
    ]


class CategoricalMetric(scoring.Metric, abc.ABC):
    """
    Base class providing common implementations for Categorical metrics relying on truth tables
    """
    @classmethod
    @abc.abstractmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        """
        Returns:
            Metadata describing the parameters of the metric
        """
        pass

    @property
    def name(self) -> str:
        """
        Returns:
            The name of the categorical metric
        """
        return self.get_metadata().name

    @abc.abstractmethod
    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        """
        Calculates the categorical metric and returns the results via row number-row pairs

        Args:
            tables: The truth tables to apply the metric to

        Returns:
            row number-row pairs
        """
        pass

    @classmethod
    def get_name(cls):
        return cls.get_metadata().name

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            lower_bound=self.get_metadata().minimum,
            upper_bound=self.get_metadata().maximum,
            ideal_value=self.get_metadata().ideal,
            failure=self.get_metadata().failure,
            greater_is_better=not self.get_metadata().scale_is_reversed
        )

    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[threshold.Threshold] = None,
            *args,
            **kwargs
    ) -> scoring.Scores:
        """
        Run the metric

        Args:
            pairs: a Pairing between all observed and predicted data
            observed_value_label: The key for the column containing raw observation data
            predicted_value_label: The key for the column containing raw prediction data
            thresholds: Thresholds used to
            *args: All undefined positional arguments; unlikely to be used
            **kwargs: All passed in keyword arguments; this is a good way to pass pre-built TruthTables

        Returns:
            The collection of score object structures
        """
        if not thresholds:
            raise ValueError(
                f"Specific thresholds are needed in order to perform categorical metrics. "
                f"'{self.name}' could not be performed."
            )

        truth_tables_key = find_truthtables_key(**kwargs)
        keys_for_truth_tables = find_individual_truthtable_keys(**kwargs)

        if truth_tables_key:
            tables: categorical.TruthTables = kwargs.get(truth_tables_key)
        elif keys_for_truth_tables:
            tables: categorical.TruthTables = categorical.TruthTables(
                tables=[
                    kwargs.get(key)
                    for key in keys_for_truth_tables
                ]
            )
        else:
            logging.warning(
                f"No truth tables were passed to '{inspect.stack()[0][3]}', so one is being constructed. "
                f"Operations may be sped up by providing tables within the keyword arguments."
            )
            # No truth tables have been added and passed around, so create one
            tables: categorical.TruthTables = categorical.TruthTables(
                pairs[observed_value_label],
                pairs[predicted_value_label],
                thresholds
            )

        if len(tables) == 0:
            raise ValueError("No truth tables were available to perform categorical metrics on")

        scores: typing.List[scoring.Score] = list()

        for row_number, row in self._get_values(tables):
            score = scoring.Score(self, row['value'], tables[row['threshold']].threshold)
            scores.append(score)

        return scoring.Scores(self, scores)


class PearsonCorrelationCoefficient(scoring.Metric):
    @classmethod
    def get_name(cls):
        return "Pearson Correlation Coefficient"

    @classmethod
    def get_descriptions(cls):
        return "A measure of linear correlation between two sets of data"

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            lower_bound=0,
            upper_bound=1,
            ideal_value=1,
            failure=0.0
        )

    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[threshold.Threshold] = None,
            *args,
            **kwargs
    ) -> scoring.Scores:
        if not thresholds:
            thresholds = [threshold.Threshold.default()]

        scores: typing.List[scoring.Score] = list()

        for pearson_threshold in thresholds:
            result = numpy.nan
            filtered_pairs = pearson_threshold(pairs)

            if not filtered_pairs.empty:
                result = numpy.corrcoef(filtered_pairs[observed_value_label], filtered_pairs[predicted_value_label])
                if result is not None and len(result) > 0:
                    result = result[0][1]
            scores.append(
                scoring.Score(self, result, pearson_threshold)
            )

        return scoring.Scores(self, scores)


class KlingGuptaEfficiency(scoring.Metric):
    @classmethod
    def get_descriptions(cls):
        return "A goodness-of-fit measure providing a diagnostically interesting decomposition of the " \
               "Nash-Sutcliffe efficiency"

    @classmethod
    def get_name(cls) -> str:
        return "Kling-Gupta Efficiency"

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            lower_bound=0,
            upper_bound=1,
            ideal_value=1
        )

    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[Threshold] = None,
            alpha_scale: float = None,
            beta_scale: float = None,
            gamma_scale: float = None,
            *args,
            **kwargs
    ) -> scoring.Scores:
        if alpha_scale is None or numpy.isnan(alpha_scale):
            alpha_scale = 1

        if beta_scale is None or numpy.isnan(beta_scale):
            beta_scale = 1

        if gamma_scale is None or numpy.isnan(gamma_scale):
            gamma_scale = 1

        alpha_values = PearsonCorrelationCoefficient(self.weight)(
            pairs,
            observed_value_label,
            predicted_value_label,
            thresholds,
            *args,
            **kwargs
        )

        scores: typing.List[scoring.Score] = list()

        for kling_threshold in thresholds:
            result = numpy.nan
            filtered_pairs = kling_threshold(pairs)

            if not filtered_pairs.empty:
                observed_values: pandas.Series = filtered_pairs[observed_value_label]
                predicted_values: pandas.Series = filtered_pairs[predicted_value_label]

                observed_mean = observed_values.mean()
                predicted_mean = predicted_values.mean()

                observed_std = observed_values.std()
                predicted_std = predicted_values.std()

                # The ratio between the standard deviation of the simulated values and the standard deviation of the
                # observed ones. Ideal value is Alpha=1
                alpha = alpha_values[kling_threshold].value
                alpha *= alpha_scale

                # The ratio between the mean of the simulated values and the mean of the observed ones.
                # Ideal value is Beta=1
                beta = predicted_mean / observed_mean
                beta *= beta_scale

                # The ratio between the coefficient of variation (CV) of the simulated values to the coefficient of
                # variation of the observed ones. Ideal value is Gamma=1
                gamma = predicted_std / observed_std
                gamma *= gamma_scale

                initial_result = math.sqrt((alpha - 1)**2 + (beta - 1)**2 + (gamma - 1)**2)
                result = 1.0 - initial_result
            scores.append(scoring.Score(self, result, kling_threshold))

        return scoring.Scores(self, scores)


class NormalizedNashSutcliffeEfficiency(scoring.Metric):
    @classmethod
    def get_descriptions(cls):
        return "A normalized statistic that measures the relative magnitude of noise compared to information"

    @classmethod
    def get_name(cls) -> str:
        return "Normalized Nash-Sutcliffe Efficiency"

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            lower_bound=0,
            upper_bound=1,
            ideal_value=1
        )

    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[Threshold] = None,
            *args,
            **kwargs
    ) -> scoring.Scores:
        scores: typing.List[scoring.Score] = list()

        for nnse_threshold in thresholds:
            normalized_nash_sutcliffe_efficiency = numpy.nan
            thresholded_pairs = nnse_threshold(pairs)

            if not thresholded_pairs.empty:
                observed_values: pandas.Series[numpy.float32] = thresholded_pairs[observed_value_label]

                numerator = thresholded_pairs.apply(
                    lambda row: (row[observed_value_label] - row[predicted_value_label])**2,
                    axis=1
                ).sum()

                mean_observation = observed_values.mean()

                denominator = thresholded_pairs.apply(
                    lambda row: (row[observed_value_label] - mean_observation)**2,
                    axis=1
                ).sum()

                nash_suttcliffe_efficiency = numerator / denominator

                normalized_nash_sutcliffe_efficiency = 1 / (2 - nash_suttcliffe_efficiency)

            scores.append(
                scoring.Score(
                    self,
                    normalized_nash_sutcliffe_efficiency,
                    nnse_threshold
                )
            )

        return scoring.Scores(self, scores)


class VolumeError(scoring.Metric):
    @classmethod
    def get_descriptions(cls):
        return "The difference between the observed volume and the predicted volume"

    @classmethod
    def get_name(cls) -> str:
        return "Volume Error"

    def __init__(self, weight: NUMBER):
        """
        Constructor

        Args:
            weight: The relative significance of the metric
        """
        super().__init__(
            weight=weight,
            ideal_value=0
        )

    def __call__(
            self,
            pairs: pandas.DataFrame,
            observed_value_label: str,
            predicted_value_label: str,
            thresholds: typing.Sequence[Threshold] = None,
            *args,
            **kwargs
    ) -> scoring.Scores:
        scores: typing.List[scoring.Score] = list()

        for volume_threshold in thresholds:
            filtered_pairs = volume_threshold(pairs)
            difference = 0
            if not filtered_pairs.empty:
                dates: typing.List[int] = [value.astype("int") for value in filtered_pairs.index.values]
                area_under_observations = sklearn.metrics.auc(dates, filtered_pairs[observed_value_label])
                area_under_predictions = sklearn.metrics.auc(dates, filtered_pairs[predicted_value_label])
                difference = area_under_predictions - area_under_observations
            scores.append(scoring.Score(self, difference, volume_threshold))

        return scoring.Scores(self, scores)


class ProbabilityOfDetection(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return "The probability that something was detected. Sensitive to hits, but ignores false alarms. " \
               "Very sensitive to the climatological frequency of the event. Good for rare events."

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.probability_of_detection.iterrows()

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("probability_of_detection")


class FalseAlarmRatio(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return "The probability that something was falsely reported as happening. Sensitive to false alarms, " \
               "but ignores misses. Very sensitive to the climatological frequency of the event. " \
               "Should be used in conjunction with the probability of detection."

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.false_alarm_ratio.iterrows()

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("false_alarm_ratio")


class FrequencyBias(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return "Measures the ratio of the frequency of forecast events to the frequency of observed events. " \
               "Indicates whether the forecast system has a tendency to underforecast (BIAS<1) or overforecast (BIAS>1)"

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("frequency_bias")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.frequency_bias.iterrows()


class Accuracy(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return 'Overall, what fraction of the forecasts were correct? Can be misleading since it is heavily ' \
               'influenced by the most common category, usually "no event" in the case of rare weather.'

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("accuracy")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.accuracy.iterrows()


class CriticalSuccessIndex(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return 'How well did the forecast "yes" events correspond to the observed "yes" events? It can be thought ' \
               'of as the accuracy when correct negatives have been removed from consideration, that is, TS is only ' \
               'concerned with forecasts that count. Sensitive to hits, penalizes both misses and false alarms.'

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("critical_success_index")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.critical_success_index.iterrows()


class EquitableThreatScore(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return 'How well did the forecast "yes" events correspond to the observed "yes" events ' \
               '(accounting for hits due to chance)? Sensitive to hits. Because it penalises both misses and false ' \
               'alarms in the same way, it does not distinguish the source of forecast error.'

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("equitable_threat_score")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.equitable_threat_score.iterrows()


class GeneralSkill(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return 'What was the accuracy of the forecast relative to that of random chance?'

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("general_skill")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.general_skill.iterrows()


class Precision(CategoricalMetric):
    @classmethod
    def get_descriptions(cls):
        return 'The ratio of the number of times predictions correctly predicted an event to the total number of ' \
               'times the predictions stated there would be an event.'

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("precision")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.precision.iterrows()
