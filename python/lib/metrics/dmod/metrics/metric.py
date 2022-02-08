import typing
import abc
import math

import numpy
import pandas
import sklearn.metrics

import dmod.metrics.scoring as scoring
import dmod.metrics.threshold as threshold
import dmod.metrics.categorical as categorical
from dmod.metrics.threshold import Threshold

NUMBER = typing.Union[int, float]
DEFAULT_TRUTH_TABLES_KEY = "TRUTH_TABLES"
ROW_INDEX_KEY = typing.Optional[typing.Hashable]
KEY_AND_ROW = typing.Tuple[ROW_INDEX_KEY, pandas.Series]
INFINITY = math.inf


def find_truthtables_key(**kwargs) -> typing.Optional[str]:
    keys = [
        key
        for key, value in kwargs.items()
        if isinstance(value, categorical.TruthTables)
    ]

    if DEFAULT_TRUTH_TABLES_KEY in keys:
        return DEFAULT_TRUTH_TABLES_KEY

    return keys[0] if keys else None


def find_individual_truthtable_keys(**kwargs) -> typing.List[str]:
    return [
        key
        for key, value in kwargs.items()
        if isinstance(value, categorical.TruthTable)
    ]


class CategoricalMetric(scoring.Metric, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        pass

    @property
    def name(self) -> str:
        return self.get_metadata().name

    @abc.abstractmethod
    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        pass

    def __init__(self, weight: NUMBER):
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
        if not thresholds:
            raise ValueError("Specific thresholds are needed in order to determine the false alarm ratio")

        truth_tables_key = find_truthtables_key(**kwargs)

        if truth_tables_key:
            tables: categorical.TruthTables = kwargs.get(truth_tables_key)
        else:
            # No truth tables have been added and passed around, so create one
            tables: categorical.TruthTables = categorical.TruthTables(
                pairs[observed_value_label],
                pairs[predicted_value_label],
                thresholds
            )

        scores: typing.List[scoring.Score] = list()

        for row_number, row in self._get_values(tables):
            score = scoring.Score(self, row['value'], tables[row['threshold']].threshold)
            scores.append(score)

        return scoring.Scores(self, scores)


class PearsonCorrelationCoefficient(scoring.Metric):
    @property
    def name(self) -> str:
        return "Pearson Correlation Coefficient"

    def __init__(self, weight: NUMBER):
        super().__init__(
            weight=weight,
            lower_bound=-1,
            upper_bound=1,
            ideal_value=1
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
    @property
    def name(self) -> str:
        return "Kling-Gupta Efficiency"

    def __init__(self, weight: NUMBER):
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
        rho_values = PearsonCorrelationCoefficient(self.weight)(
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

                gamma = predicted_std / observed_std
                beta = predicted_mean / observed_mean

                rho = rho_values[kling_threshold]

                result = 1.0 - math.sqrt((rho.value - 1)**2 + (gamma - 1)**2 + (beta - 1)**2)
            scores.append(scoring.Score(self, result, kling_threshold))

        return scoring.Scores(self, scores)


class NormalizedNashSutcliffeEfficiency(scoring.Metric):
    @property
    def name(self) -> str:
        return "Normalized Nash–Sutcliffe Efficiency"

    def __init__(self, weight: NUMBER):
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
    @property
    def name(self) -> str:
        return "Volume Error"

    def __init__(self, weight: NUMBER):
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
    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.probability_of_detection.iterrows()

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("probability_of_detection")


class FalseAlarmRatio(CategoricalMetric):
    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.false_alarm_ratio.iterrows()

    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("false_alarm_ratio")


class FrequencyBias(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("frequency_bias")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.frequency_bias.iterrows()


class Accuracy(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("accuracy")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.accuracy.iterrows()


class EquitableThreatScore(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("equitable_threat_score")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.equitable_threat_score.iterrows()


class GeneralSkill(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("general_skill")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.general_skill.iterrows()


class Precision(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("precision")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.precision.iterrows()


class Hits(CategoricalMetric):
    @classmethod
    def get_metadata(cls) -> categorical.CategoricalMetricMetadata:
        return categorical.TruthTable.get_metric_metadata("hits")

    def _get_values(self, tables: categorical.TruthTables) -> typing.Iterable[KEY_AND_ROW]:
        return tables.hits.iterrows()
