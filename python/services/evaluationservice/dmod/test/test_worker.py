#!/usr/bin/env python3
import typing
import unittest

from ..evaluationservice import worker
from . import common


class TestWorker(unittest.TestCase):
    def test_main(self):
        instruction_path = common.get_resource_path("cfs_vs_cfs_evaluation.json")
        arguments = worker.Arguments(
            "-n",
            "CFS vs CFS",
            str(instruction_path)
        )
        worker.main(arguments=arguments)
