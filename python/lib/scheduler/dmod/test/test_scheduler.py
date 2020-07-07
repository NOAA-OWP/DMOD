import unittest
from pathlib import Path
from ..scheduler.scheduler import Launcher
from . import mock_job

class TestLauncher(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = Path(__file__).parent/"image_and_domain.yaml"
        self.user_name = 'test'

        #Create a launcher
        self.launcher = Launcher(images_and_domains_yaml=yaml_file)

    def tearDown(self) -> None:
        self.launcher.docker_client.close()

    def test_start_job(self) -> None:
        job = mock_job(allocations=1)
        self.launcher.start_job(job)
    #TODO test
    @unittest.skip("Not implemented")
    def test_create_service(self):
        pass
    @unittest.skip("Not implemented")
    def test_build_host_list(self):
        pass
    @unittest.skip("Not implemented")
    def test_job_allocation_and_setup(self):
        pass
