import unittest
from pathlib import Path
from ..scheduler.scheduler import Launcher
from . import mock_job
from .utils import logTest
import logging


class IntegrationTestLauncher(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = Path(__file__).parent/"image_and_domain.yaml"
        self.user_name = 'test'
        self.clean_up = []
        #Create a launcher
        self.launcher = Launcher(images_and_domains_yaml=yaml_file)

    def tearDown(self) -> None:
        for service in self.clean_up:
            service.remove()
        self.launcher.docker_client.close()

    @logTest(logging.DEBUG)
    @unittest.skip
    def test_start_job_1_a(self) -> None:
        job = mock_job(model='ngen', allocations=1)
        success, services_tuple = self.launcher.start_job(job)
        self.assertTrue(success)
        self.assertIsNotNone(services_tuple)
        for service in services_tuple:
            self.clean_up.append(service)
        for service in services_tuple:
            self.assertIsNotNone(service)

        job = mock_job(model='nwm', allocations=1)
        success, services_tuple = self.launcher.start_job(job)
        self.assertTrue(success)
        self.assertIsNotNone(services_tuple)
        for service in services_tuple:
            self.clean_up.append(service)
        for service in services_tuple:
            self.assertIsNotNone(service)

    #TODO test
    @unittest.skip("Not implemented")
    def test_create_service_1_a(self):
        pass
