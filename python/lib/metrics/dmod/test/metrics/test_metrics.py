#!/usr/bin/env python3
import os
import typing
import unittest

import pandas
import numpy

from ...metrics import metric as metrics

TEST_DIRECTORY = os.path.dirname(__file__)
EPSILON = 0.0001

OBSERVATION_VALUE_KEY = "Observations"
MODEL_VALUE_KEY = "value"

MODEL_DATA_PATH = os.path.join(TEST_DIRECTORY, "model_1.csv")
OBSERVATION_DATA_PATH = os.path.join(TEST_DIRECTORY, "observations.csv")


def get_thresholds() -> typing.List[metrics.Threshold]:
    thresholds: typing.List[metrics.Threshold] = list()

    thresholds.append(metrics.Threshold.default())

    thresholds.append(
        metrics.Threshold(
            name="Minor",
            value=27,
            weight=1,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        metrics.Threshold(
            name="Moderate",
            value=36,
            weight=1,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        metrics.Threshold(
            name="Major",
            value=43,
            weight=1,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    thresholds.append(
        metrics.Threshold(
            name="Record",
            value=60,
            weight=1,
            observed_value_key=OBSERVATION_VALUE_KEY,
            predicted_value_key=MODEL_VALUE_KEY
        )
    )

    return thresholds


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.observations = pandas.read_csv(
            OBSERVATION_DATA_PATH,
            index_col="date",
            parse_dates=["date"]
        )
        self.model = pandas.read_csv(
            MODEL_DATA_PATH,
            index_col="date",
            parse_dates=["date"]
        )
        self.pairs = self.observations.join(self.model).dropna(subset=[MODEL_VALUE_KEY])
        self.thresholds = get_thresholds()
        self.truth_tables = metrics.categorical.TruthTables(
            self.observations[OBSERVATION_VALUE_KEY],
            self.model[MODEL_VALUE_KEY],
            self.thresholds
        )

    def test_pearson_correlation_coefficient(self):
        metric = metrics.PearsonCorrelationCoefficient(5)
        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 0.922621, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 0.8309918, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 0.408608, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.866025, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_kling_gupta_efficiency(self):
        metric = metrics.KlingGuptaEfficiency(5)
        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 0.211113, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 0.821679, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 0.337877, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, -7.238951, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_normalized_nash_sutcliffe_efficiency(self):
        metric = metrics.NormalizedNashSutcliffeEfficiency(5)
        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 0.358983, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 0.6668423, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value,  0.484302, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.008368, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_volume_error(self):
        metric = metrics.VolumeError(5)
        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, -1447200000000000.0, delta=EPSILON)
        self.assertAlmostEqual(-58.85, scores['Minor'].value, delta=EPSILON)
        self.assertAlmostEqual(-14.45, scores['Moderate'].value, delta=EPSILON)
        self.assertAlmostEqual(-27.75, scores['Major'].value, delta=EPSILON)
        self.assertAlmostEqual(0.0, scores['Record'].value, delta=EPSILON)

    def test_probability_of_detection(self):
        metric = metrics.ProbabilityOfDetection(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.33333, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_false_alarm_ratio(self):
        metric = metrics.FalseAlarmRatio(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 0, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 0, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 0, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_frequency_bias(self):
        metric = metrics.FrequencyBias(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.33333, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_accuracy(self):
        metric = metrics.Accuracy(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(1, scores['All'].value, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.962962, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_equitable_threat_score(self):
        metric = metrics.EquitableThreatScore(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertTrue(numpy.isnan(scores['All'].value))
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.3207547, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_general_skill(self):
        metric = metrics.GeneralSkill(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertTrue(numpy.isnan(scores['All'].value))
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 0.485714, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_precision(self):
        metric = metrics.Precision(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))
        self.assertAlmostEqual(scores['All'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, 1, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

    def test_lineartemporaltrendabsoluteerror(self):
        metric = metrics.LinearTemporalTrendAbsoluteError(5)

        scores = metric(
            self.pairs,
            OBSERVATION_VALUE_KEY,
            MODEL_VALUE_KEY,
            self.thresholds,
            TRUTH_TABLES=self.truth_tables
        )

        self.assertEqual(len(scores), len(self.thresholds))

        self.assertAlmostEqual(scores['All'].value, -0.000028666, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].value, -0.02156, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].value, 0.0224, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].value, -0.25714, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].value))

        self.assertAlmostEqual(scores['All'].scaled_value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Minor'].scaled_value, 1, delta=EPSILON)
        self.assertAlmostEqual(scores['Moderate'].scaled_value, 0.97753, delta=EPSILON)
        self.assertAlmostEqual(scores['Major'].scaled_value, 1, delta=EPSILON)
        self.assertTrue(numpy.isnan(scores['Record'].scaled_value))


def main():
    """
    Define your initial application code here
    """
    unittest.main()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
