import unittest
from ..client.client_config import ClientConfig
from ..client.dmod_client import DmodClient
from ..client.request_clients import JobClient
from pathlib import Path
from typing import Dict


class TestDmodClient(unittest.TestCase):

    def setUp(self) -> None:
        self._test_config_files: Dict[int, Path] = dict()
        self._test_configs: Dict[int, ClientConfig] = dict()
        self._test_clients: Dict[int, DmodClient] = dict()

        # Example 0
        ex_idx = 0
        self._test_config_files[ex_idx] = Path(__file__).parent.joinpath("testing_config.json")
        self._test_configs[ex_idx] = ClientConfig.parse_file(self._test_config_files[ex_idx])
        self._test_clients[ex_idx] = DmodClient(client_config=self._test_configs[ex_idx])

    def tearDown(self) -> None:
        pass

    def test_job_client_0_a(self):
        """ Make sure a valid job client is initialized for config example 0. """
        ex_idx = 0
        client = self._test_clients[ex_idx]

        self.assertIsInstance(client.job_client, JobClient)
