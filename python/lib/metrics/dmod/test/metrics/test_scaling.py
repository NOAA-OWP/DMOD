#!/usr/bin/env python3
import unittest

from ...metrics import metric as metrics
from ...metrics.scoring import scale_value

from ...metrics.common import EPSILON


class TestResultScaling(unittest.TestCase):
    def test_pearson_scaling(self):
        metric = metrics.PearsonCorrelationCoefficient(1)

        perfect_value = 1.0
        mid_value = 0.5
        low_value = 0.0
        lowest_value = -0.75

        scaled_perfect_value = scale_value(metric, perfect_value)
        scaled_mid_value = scale_value(metric, mid_value)
        scaled_low_value = scale_value(metric, low_value)
        scaled_lowest_value = scale_value(metric, lowest_value)

        self.assertAlmostEqual(scaled_perfect_value, 1.0, delta=EPSILON)
        self.assertAlmostEqual(scaled_mid_value, 0.5, delta=EPSILON)
        self.assertAlmostEqual(scaled_low_value, 0.0, delta=EPSILON)
        self.assertAlmostEqual(scaled_lowest_value, 0.0, delta=EPSILON)

    def test_false_alarm_scaling(self):
        metric = metrics.FalseAlarmRatio(1)

        perfect_value = 0.0
        mid_value = 0.5
        low_value = 0.75
        lowest_value = 1.0

        scaled_perfect_value = scale_value(metric, perfect_value)
        scaled_mid_value = scale_value(metric, mid_value)
        scaled_low_value = scale_value(metric, low_value)
        scaled_lowest_value = scale_value(metric, lowest_value)

        self.assertAlmostEqual(scaled_perfect_value, 1.0, delta=EPSILON)
        self.assertAlmostEqual(scaled_mid_value, 0.5, delta=EPSILON)
        self.assertAlmostEqual(scaled_low_value, 0.25, delta=EPSILON)
        self.assertAlmostEqual(scaled_lowest_value, 0.0, delta=EPSILON)

    def test_volume_scaling(self):
        metric = metrics.VolumeError(1)

        perfect_value = 123456
        mid_value = 2563432
        low_value = 234234255
        lowest_value = 435342234

        scaled_perfect_value = scale_value(metric, perfect_value)
        scaled_mid_value = scale_value(metric, mid_value)
        scaled_low_value = scale_value(metric, low_value)
        scaled_lowest_value = scale_value(metric, lowest_value)

        self.assertAlmostEqual(scaled_perfect_value, perfect_value, delta=EPSILON)
        self.assertAlmostEqual(scaled_mid_value, mid_value, delta=EPSILON)
        self.assertAlmostEqual(scaled_low_value, low_value, delta=EPSILON)
        self.assertAlmostEqual(scaled_lowest_value, lowest_value, delta=EPSILON)



def main():
    """
    Define your initial application code here
    """
    unittest.main()


# Run the following if the script was run directly
if __name__ == "__main__":
    main()
