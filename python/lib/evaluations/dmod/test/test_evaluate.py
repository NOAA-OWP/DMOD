import unittest
import os
import json
import typing

from datetime import datetime

import numpy

import dmod.metrics.scoring as scoring

from ..evaluations import evaluate

from ..evaluations import specification

from .common import RESOURCE_DIRECTORY
from .common import EPSILON

CFS_TO_CMS_CONFIG_PATH = os.path.join(RESOURCE_DIRECTORY, "cfs_vs_cms_evaluation.json")
CFS_TO_CFS_CONFIG_PATH = os.path.join(RESOURCE_DIRECTORY, "cfs_vs_cfs_evaluation.json")


def get_expected_evaluation_results() -> typing.Dict[typing.Tuple[str, str], dict]:
    expected_results = {
        ("0214655255", "cat-27"): {
            "maximum_valid_score": 204,
            "total":  7.07788,
            "thresholds": {
                "p50_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.0,
                        "scaled_value": 1.0,
                        "metric_weight": 10,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 1.0,
                        "scaled_value": 1.0,
                        "metric_weight": 10,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.278977,
                        "scaled_value": 0.278977,
                        "metric_weight": 15,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.373682,
                        "scaled_value": 0.373682,
                        "metric_weight": 15,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.583159696,
                        "scaled_value": 0.583159696,
                        "metric_weight": 18,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    }
                ],
                "p75_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.022857142857142857,
                        "scaled_value": 9.77142857142857,
                        "metric_weight": 10,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 0.9434482758620689,
                        "scaled_value": 9.434482758620689,
                        "metric_weight": 10,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.2789775068724476,
                        "scaled_value": 4.184662603086714,
                        "metric_weight": 15,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.373682,
                        "scaled_value": 5.60523,
                        "metric_weight": 15,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.5831596961286304,
                        "scaled_value": 1.496874530315347,
                        "metric_weight": 18,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    }
                ],
                "p80_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.04791344667697063,
                        "scaled_value": 9.520865533230294,
                        "metric_weight": 10,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 0.8676056338028169,
                        "scaled_value": 8.676056338028168,
                        "metric_weight": 10,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.2789775068724476,
                        "scaled_value": 4.184662603086714,
                        "metric_weight": 15,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.373682,
                        "scaled_value": 5.60523,
                        "metric_weight": 15,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.5831596961286304,
                        "scaled_value": 1.496874530315347,
                        "metric_weight": 18,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    }
                ],
                "Flood": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 18,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    }
                ],
                "Action": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 18,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    }
                ],
            }
        },
        ("0214657975", "cat-52"): {
            "maximum_valid_score": 204,
            "total": 12.018,
            "thresholds": {
                "p50_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.0,
                        "scaled_value": 1.0,
                        "metric_weight": 10,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 1.0,
                        "scaled_value": 1.0,
                        "metric_weight": 10,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.6588182003575915,
                        "scaled_value": 0.6588182,
                        "metric_weight": 15,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.623952,
                        "scaled_value": 0.623952,
                        "metric_weight": 15,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.6851455871369385,
                        "scaled_value": 0.6851455871369385,
                        "metric_weight": 18,
                        "threshold_weight": 1,
                        "threshold_name": "p50_va"
                    }
                ],
                "p75_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.03443328550932568,
                        "scaled_value": 9.655667144906744,
                        "metric_weight": 10,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 1.0,
                        "scaled_value": 10.0,
                        "metric_weight": 10,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.6588182003575915,
                        "scaled_value": 9.882273005363873,
                        "metric_weight": 15,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.623952,
                        "scaled_value": 9.359285,
                        "metric_weight": 15,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.6851455871369385,
                        "scaled_value": 12.332620568464893,
                        "metric_weight": 18,
                        "threshold_weight": 10,
                        "threshold_name": "p75_va"
                    }
                ],
                "p80_va": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": 0.09037900874635568,
                        "scaled_value": 9.096209912536445,
                        "metric_weight": 10,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": 1.0,
                        "scaled_value": 10.0,
                        "metric_weight": 10,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": 0.6588182003575915,
                        "scaled_value": 9.882273005363873,
                        "metric_weight": 15,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": 0.623952,
                        "scaled_value": 9.359285,
                        "metric_weight": 15,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": 0.6851455871369385,
                        "scaled_value": 12.332620568464893,
                        "metric_weight": 18,
                        "threshold_weight": 5,
                        "threshold_name": "p80_va"
                    }
                ],
                "Flood": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 18,
                        "threshold_weight": 2,
                        "threshold_name": "flood"
                    }
                ],
                "Action": [
                    {
                        "name": "False Alarm Ratio",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": "Probability Of Detection",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 10,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": "Kling-Gupta Efficiency",
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": 'Normalized Nash-Sutcliffe Efficiency',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 15,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    },
                    {
                        "name": 'Pearson Correlation Coefficient',
                        "failed": False,
                        "value": numpy.nan,
                        "scaled_value": numpy.nan,
                        "metric_weight": 18,
                        "threshold_weight": 3,
                        "threshold_name": "action"
                    }
                ],
            }
        }
    }

    return expected_results


class TestEvaluate(unittest.TestCase):
    @classmethod
    def get_cfs_to_cms_specification(cls) -> specification.EvaluationSpecification:
        with open(CFS_TO_CMS_CONFIG_PATH) as config_file:
            raw_config = json.load(config_file)

        return specification.EvaluationSpecification.create(raw_config)

    @classmethod
    def get_cfs_to_cfs_specification(cls) -> specification.EvaluationSpecification:
        with open(CFS_TO_CFS_CONFIG_PATH) as config_file:
            raw_config = json.load(config_file)

        return specification.EvaluationSpecification.create(raw_config)

    def setUp(self) -> None:
        self.__cfs_to_cms_specification = self.get_cfs_to_cms_specification()
        self.__cfs_to_cfs_specification = self.get_cfs_to_cfs_specification()

    def test_load_cfs_to_cfs(self):
        cfs_to_cfs_evaluator = evaluate.Evaluator(self.__cfs_to_cfs_specification)
        self.make_assertions(cfs_to_cfs_evaluator)

    def test_load_cfs_to_cms(self):
        cfs_to_cms_evaluator = evaluate.Evaluator(self.__cfs_to_cms_specification)
        self.make_assertions(cfs_to_cms_evaluator)

    def make_assertions(self, evaluator: evaluate.Evaluator):
        evaluation_results = evaluator.evaluate()

        self.assertEqual(len(evaluation_results), 2)

        expected_results = get_expected_evaluation_results()

        for location_pair, results in evaluation_results:  # type: (str, str), scoring.MetricResults
            self.assertIn(location_pair, expected_results)

            matching_expected_results = expected_results.pop(location_pair)
            self.assertIsNotNone(matching_expected_results)

            self.assertAlmostEqual(
                    matching_expected_results.pop('maximum_valid_score'),
                    results.maximum_valid_score,
                    delta=EPSILON
            )

            self.assertAlmostEqual(matching_expected_results.pop('total'), results.total, delta=EPSILON)

            for threshold, scores in results:  # type: scoring.Threshold, typing.List[scoring.Score]
                self.assertIn(threshold.name, matching_expected_results['thresholds'])
                expected_threshold_scores = matching_expected_results['thresholds'].pop(threshold.name)
                expected_threshold_scores = {
                    score_details['name']: score_details
                    for score_details in expected_threshold_scores
                }

                for score in scores:  # type: scoring.Score
                    self.assertIn(score.metric.name, expected_threshold_scores)
                    expected_score_results = expected_threshold_scores.pop(score.metric.name)

                    if numpy.isnan(score.value):
                        self.assertTrue(numpy.isnan(expected_score_results['value']))
                    else:
                        self.assertAlmostEqual(score.value, expected_score_results['value'], delta=EPSILON)

                    if numpy.isnan(score.scaled_value):
                        self.assertTrue(numpy.isnan(expected_score_results['scaled_value']))
                    else:
                        self.assertAlmostEqual(
                                score.scaled_value,
                                expected_score_results['scaled_value'],
                                delta=EPSILON
                        )

                    self.assertEqual(score.metric.weight, expected_score_results['metric_weight'])
                    self.assertEqual(score.threshold.weight, expected_score_results['threshold_weight'])

                self.assertEqual(len(expected_threshold_scores), 0)

            # This should have a length of 1; all the threshold values should have been removed, but the collection
            # of thresholds should still be there
            self.assertEqual(len(matching_expected_results), 1)

        self.assertEqual(len(expected_results), 0)

        fail_message = f"{os.linesep}{json.dumps(evaluation_results.to_dict(), indent=4)}"

        expected_grade = 66.39966
        self.assertAlmostEqual(expected_grade, evaluation_results.grade, delta=EPSILON, msg=fail_message)

        expected_mean = 10.6239458
        self.assertAlmostEqual(expected_mean, evaluation_results.mean, delta=EPSILON, msg=fail_message)

        expected_median = 10.6239458
        self.assertAlmostEqual(expected_median, evaluation_results.median, delta=EPSILON, msg=fail_message)

        expected_std = 1.39406
        self.assertAlmostEqual(expected_std, evaluation_results.standard_deviation, delta=EPSILON, msg=fail_message)

        expected_value = 21.24789
        self.assertAlmostEqual(expected_value, evaluation_results.value, delta=EPSILON, msg=fail_message)


if __name__ == '__main__':
    unittest.main()
