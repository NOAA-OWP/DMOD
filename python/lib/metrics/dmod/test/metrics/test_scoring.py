#!/usr/bin/env python3
import typing
import os
import unittest

import pandas
from dmod.metrics import Scores

from ...metrics.threshold import Threshold
from ...metrics import scoring
from ...metrics import metric as metrics

TEST_DIRECTORY = os.path.dirname(__file__)

OBSERVATIONS_SOURCE = os.path.join(TEST_DIRECTORY, "observations.csv")
MODEL_DATA = {
    "Model 1": os.path.join(TEST_DIRECTORY, "model_1.csv"),
    "Model 2": os.path.join(TEST_DIRECTORY, "model_2.csv"),
    "Model 3": os.path.join(TEST_DIRECTORY, "model_3.csv"),
    "Model 4": os.path.join(TEST_DIRECTORY, "model_4.csv"),
    "Model 5": os.path.join(TEST_DIRECTORY, "model_5.csv")
}

OBSERVATION_VALUE_KEY = "Observations"
MODEL_VALUE_KEY = "value"

THRESHOLD_NAME_CASE_FUNCTION: typing.Callable[[str], str] = str.title


def normalize_threshold_name(threshold_name: str) -> str:
    return THRESHOLD_NAME_CASE_FUNCTION(threshold_name)


DEFAULT_WEIGHTS: typing.Dict[str, float] = {
    normalize_threshold_name("All"): 1,
    normalize_threshold_name("Minor"): 1,
    normalize_threshold_name("Moderate"): 1,
    normalize_threshold_name("Major"): 1,
    normalize_threshold_name("Record"): 1
}

BASE_THRESHOLDS = {
    normalize_threshold_name("All"): 0,
    normalize_threshold_name("Minor"): 27,
    normalize_threshold_name("Moderate"): 36,
    normalize_threshold_name("Major"): 43,
    normalize_threshold_name("Record"): 60
}


def load_dataframe(path: str) -> pandas.DataFrame:
    frame = pandas.read_csv(path, parse_dates=['date'])
    frame.set_index("date", inplace=True)
    return frame


def get_model_data() -> typing.Dict[str, pandas.DataFrame]:
    data = {
        name: load_dataframe(path)
        for name, path in MODEL_DATA.items()
    }
    return data


def get_observations() -> pandas.DataFrame:
    data = load_dataframe(OBSERVATIONS_SOURCE)
    return data


def get_thresholds(weights: typing.Dict[str, float] = None) -> typing.Sequence[Threshold]:
    if weights is None:
        weights = DEFAULT_WEIGHTS

    weights = {
        normalize_threshold_name(name): weight for name, weight in weights.items()
    }

    for weight_name, weight in DEFAULT_WEIGHTS.items():
        if normalize_threshold_name(weight_name) not in weights:
            weights[normalize_threshold_name(weight_name)] = weight

    threshold_kwargs = [
        {
            "name": name,
            "value": value,
            "observed_value_key": OBSERVATION_VALUE_KEY,
            "predicted_value_key": MODEL_VALUE_KEY,
            "weight": weights[normalize_threshold_name(name)]
        }
        for name, value in BASE_THRESHOLDS.items()
    ]

    thresholds: typing.List[Threshold] = [Threshold(**kwargs) for kwargs in threshold_kwargs]

    return thresholds


class TestScoring(unittest.TestCase):
    def setUp(self) -> None:
        self.observations = get_observations()
        self.model_data = get_model_data()
        self.thresholds = get_thresholds()
        self.truth_tables = dict()

        for name, data in self.model_data.items():
            self.truth_tables[name] = metrics.categorical.TruthTables(
                self.observations[OBSERVATION_VALUE_KEY],
                data[MODEL_VALUE_KEY],
                self.thresholds
            )

    def test_uniform_metrics_and_thresholds(self):
        """
        Test what happens when all metrics are run for all thresholds with the same weights

        This should heavily favor "Model 2" since "Model 2" is geared to over predict, yet highly correlate.
        This means that it will ALWAYS have a PoD of 1 and will have higher non-categorical results than 'Model 1'
        since 'Model 1' doesn't reflect behavior, just the crossing of thresholds
        """

        metric_functions: typing.List[scoring.Metric] = [
            metrics.PearsonCorrelationCoefficient(1),
            metrics.ProbabilityOfDetection(1),
            metrics.FalseAlarmRatio(1),
            metrics.Precision(1),
            metrics.Accuracy(1),
            metrics.KlingGuptaEfficiency(1),
            metrics.FrequencyBias(1),
            metrics.GeneralSkill(1),
            metrics.EquitableThreatScore(1),
            metrics.NormalizedNashSutcliffeEfficiency(1),
        ]

        scheme: scoring.ScoringScheme = scoring.ScoringScheme(metric_functions)

        metric_results: typing.Dict[str, scoring.MetricResults] = dict()

        for name, data in self.model_data.items():
            pairs = self.observations.join(data).dropna(subset=[MODEL_VALUE_KEY])
            results = scheme.score(
                pairs=pairs,
                observed_value_label=OBSERVATION_VALUE_KEY,
                predicted_value_label=MODEL_VALUE_KEY,
                thresholds=self.thresholds,
                truth_tables=self.truth_tables[name]
            )

            for threshold, values in results:
                for value in values:
                    print(value)
            metric_results[name] = results

        ordered_results: typing.List[scoring.MetricResults] = sorted(
            metric_results.values(),
            key=lambda metric_result: metric_result.total,
            reverse=True
        )

        # First should be "Model 1" - while it doesn't correlate to the observations very much, the metrics are
        # biased heavily towards categorical measures, which "Model 1" is perfect at
        self.assertEqual(ordered_results[0], metric_results['Model 1'])

        # Next should be "Model 2" - it correlates highly to the observations and always detects events,
        # even though it over predicts
        self.assertEqual(ordered_results[1], metric_results['Model 2'])

        # Next should be "Model 3" - even though it has less error than "Model 2" and also has a strong correlation,
        # it underpredicts meaning that there are more misses in the truth table
        self.assertEqual(ordered_results[2], metric_results['Model 3'])

        # Next should be "Model 5" - while it never predicts anything and doesn't react to the observations,
        # it also never has any false positives.
        self.assertEqual(ordered_results[3], metric_results['Model 5'])

        # Last should be "Model 4" - "Model 4" always surpasses record and doesn't have any sort of correlation to
        # the observation. This means that it constantly raises false alarms.
        self.assertEqual(ordered_results[4], metric_results['Model 4'])


def main():
    """
    Define your initial application code here
    """
    unittest.main()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
