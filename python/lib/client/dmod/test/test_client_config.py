import unittest
from ..client.client_config import ClientConfig, ConnectionConfig
from pathlib import Path
from typing import Dict


class TestClientConfig(unittest.TestCase):

    def setUp(self) -> None:
        self._test_config_files: Dict[int, Path] = dict()
        self._test_configs: Dict[int, ClientConfig] = dict()

        # Example 0
        ex_idx = 0
        self._test_config_files[ex_idx] = Path(__file__).parent.joinpath("testing_config.json")
        self._test_configs[ex_idx] = ClientConfig.parse_file(self._test_config_files[ex_idx])

    def tearDown(self) -> None:
        pass

    def test_request_service_0_a(self):
        ex_idx = 0
        cfg_obj = self._test_configs[ex_idx]

        self.assertIsInstance(cfg_obj.request_service, ConnectionConfig)

    def test_request_service_0_b(self):
        ex_idx = 0
        cfg_obj = self._test_configs[ex_idx]

        self.assertEqual(cfg_obj.request_service.endpoint_protocol, "wss")
