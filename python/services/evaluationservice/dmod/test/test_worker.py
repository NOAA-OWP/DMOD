#!/usr/bin/env python3
import typing
import unittest

from datetime import datetime

from dmod.evaluationservice import worker
from . import common

class TestWorker(unittest.TestCase):
    def test_main(self):
        instruction_path = common.get_resource_path("cfs_vs_cfs_evaluation.json")

        arguments = worker.Arguments(
            "-n",
            "CFS vs CFS",
            str(instruction_path)
        )
        start = datetime.now()

        # Commenting out until it is more clear as to how to test components that communicate with redis
        # worker.main(arguments=arguments)
        print(f"Elapsed Time: {str(datetime.now() - start)}")

