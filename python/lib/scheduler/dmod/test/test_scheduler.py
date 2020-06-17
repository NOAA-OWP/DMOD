import unittest
from ..scheduler.scheduler import Scheduler
from . import EmptyResourceManager, MockResourceManager

class TestScheduler(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = "image_and_domain.yaml"
        self.user_name = 'test'
        self.requested_cpus = 10
        self.requested_memory = 1000000
        #Various resource manager states
        self.empty_resources = EmptyResourceManager()
        self.mock_resources = MockResourceManager()
        #Create a scheduler with no resources
        self.scheduler = Scheduler(images_and_domains_yaml=yaml_file, resource_manager=self.empty_resources)

    def tearDown(self) -> None:
        self.scheduler.docker_client.close()

    def test_return42(self):
        """

        """
        ret = self.scheduler.return42()
        self.assertEqual(ret, 42)



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
