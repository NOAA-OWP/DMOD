#!/usr/bin/env python3

import io

from unittest import TestCase

import xarray

from ...evaluations import specification
from ...evaluations.evaluate import evaluate
from ...evaluations import writing
from ..test_evaluate import TestEvaluate

from ..common import EPSILON


def get_evaluation_results() -> specification.EvaluationResults:
    return evaluate(TestEvaluate.get_cfs_to_cfs_specification())


class TestNetcdfWriting(TestCase):
    def setUp(self) -> None:
        self._evaluation_results = get_evaluation_results()

    def test_buffered_writing(self):
        writer = writing.get_writer("netcdf")
        output_buffer = io.BytesIO()
        writer.write(self._evaluation_results, output_buffer)
        output_buffer.seek(0)
        dataset = xarray.load_dataset(output_buffer)

        self.assertAlmostEqual(dataset.attrs['grade'], 63.626837, delta=EPSILON)
        self.assertAlmostEqual(dataset.attrs['mean'], 13.3616359, delta=EPSILON)
        self.assertAlmostEqual(dataset.attrs['median'], 13.3616359, delta=EPSILON)
        self.assertAlmostEqual(dataset.attrs['standard_deviation'], 0.450631, delta=EPSILON)
        self.assertAlmostEqual(dataset.attrs['result'], 26.72327187164, delta=EPSILON)
