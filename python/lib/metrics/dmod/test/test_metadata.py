"""
Unit tests to make sure that metric metadata can be read
"""
import unittest
import math

from ..metrics import metric as metrics


class TestMetadata(unittest.TestCase):
    """
    Unit tests to make sure that metric metadata can be read
    """
    def test_metadata_retrieval(self):
        """
        Test to make sure that metadata can be found for all metrics
        """
        found_metrics = metrics.get_all_metrics()

        self.assertEqual(len(found_metrics), 13)

        self.assertIn(metrics.KlingGuptaEfficiency, found_metrics)
        self.assertIn(metrics.NormalizedNashSutcliffeEfficiency, found_metrics)
        self.assertIn(metrics.PearsonCorrelationCoefficient, found_metrics)
        self.assertIn(metrics.Precision, found_metrics)
        self.assertIn(metrics.ProbabilityOfDetection, found_metrics)
        self.assertIn(metrics.VolumeError, found_metrics)
        self.assertIn(metrics.Accuracy, found_metrics)
        self.assertIn(metrics.CriticalSuccessIndex, found_metrics)
        self.assertIn(metrics.EquitableThreatScore, found_metrics)
        self.assertIn(metrics.FalseAlarmRatio, found_metrics)
        self.assertIn(metrics.FrequencyBias, found_metrics)
        self.assertIn(metrics.GeneralSkill, found_metrics)

    def test_kling_gupta_efficiency(self):
        """
        Test to make sure that the metadata on the Kling-Gupta Efficiency is correct
        """
        metric = metrics.KlingGuptaEfficiency(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1.0)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)

    def test_pearson_correlation_coefficient(self):
        """
        Test to make sure that the metadata on the Pearson Correlation Coefficient is correct
        """
        metric = metrics.PearsonCorrelationCoefficient(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1.0)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertEqual(metric.fails_on, 0)

        self.assertTrue(metric.greater_is_better)

    def test_normalized_nash_sutcliffe_efficiency(self):
        """
        Test to make sure that the metadata on the Normalized Nash-Sutcliffe Efficiency is correct
        """
        metric = metrics.NormalizedNashSutcliffeEfficiency(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1.0)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)

    def test_volume_error(self):
        """
        Test to make sure that the metadata on the Volume Error is correct
        """
        metric = metrics.VolumeError(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertFalse(metric.bounded)

        self.assertFalse(metric.has_lower_bound)
        self.assertTrue(math.isinf(metric.lower_bound))
        self.assertTrue(metric.lower_bound < 0)

        self.assertFalse(metric.has_upper_bound)
        self.assertTrue(math.isinf(metric.upper_bound))
        self.assertTrue(metric.upper_bound > 0)

        self.assertFalse(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 0.0)

        self.assertIsNone(metric.fails_on)

        self.assertFalse(metric.greater_is_better)

    def test_probability_of_detection(self):
        """
        Test to make sure that the metadata on the Probability of Detection is correct
        """
        metric = metrics.ProbabilityOfDetection(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1.0)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertEqual(metric.fails_on, 0.0)

        self.assertTrue(metric.greater_is_better)

    def test_false_alarm_ratio(self):
        """
        Test to make sure that the metadata on the False Alarm Ratio is correct
        """
        metric = metrics.FalseAlarmRatio(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0.0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1.0)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 0.0)

        self.assertEqual(metric.fails_on, 1.0)

        self.assertFalse(metric.greater_is_better)

    def test_frequency_bias(self):
        """
        Test to make sure that the metadata on the Frequency Bias is correct
        """
        metric = metrics.FrequencyBias(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertFalse(metric.has_upper_bound)
        self.assertTrue(math.isinf(metric.upper_bound))
        self.assertTrue(metric.upper_bound > 0)

        self.assertFalse(metric.fully_bounded)
        self.assertTrue(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)

    def test_accuracy(self):
        """
        Test to make sure that the metadata on the Accuracy is correct
        """
        metric = metrics.Accuracy(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)

    def test_critical_success_index(self):
        """
        Test to make sure that the metadata on the Critical Success Index is correct
        """
        metric = metrics.CriticalSuccessIndex(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)

    def test_equitable_threat_score(self):
        """
        Test to make sure that the metadata on the Equitable Threat Score is correct
        """
        metric = metrics.EquitableThreatScore(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertEqual(metric.fails_on, 0.0)

        self.assertTrue(metric.greater_is_better)

    def test_general_skill(self):
        """
        Test to make sure that the metadata on the General Skill is correct
        """
        metric = metrics.GeneralSkill(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertEqual(metric.fails_on, 0.0)

        self.assertTrue(metric.greater_is_better)

    def test_precision(self):
        """
        Test to make sure that the metadata on the Precision is correct
        """
        metric = metrics.Precision(1)
        self.assertEqual(metric.weight, 1)
        self.assertTrue(len(metric.get_descriptions()) > 10)
        self.assertTrue(len(metric.get_name()) > 5)

        self.assertTrue(metric.bounded)
        self.assertTrue(metric.has_lower_bound)
        self.assertEqual(metric.lower_bound, 0)

        self.assertTrue(metric.has_upper_bound)
        self.assertEqual(metric.upper_bound, 1)

        self.assertTrue(metric.fully_bounded)
        self.assertFalse(metric.partially_bounded)

        self.assertTrue(metric.has_ideal_value)
        self.assertEqual(metric.ideal_value, 1.0)

        self.assertIsNone(metric.fails_on)

        self.assertTrue(metric.greater_is_better)
