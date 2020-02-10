import unittest
from ..scheduler.scheduler import Scheduler
from . import EmptyResourceManager

class TestScheduler(unittest.TestCase):

    def setUp(self) -> None:
        self.user_name = 'test'
        self.requested_cpus = 10
        self.requested_memory = 1000000
        #Various resource manager states
        self.empty_resources = EmptyResourceManager()

        #Create a scheduler with no resources
        self.scheduler = Scheduler(resource_manager=self.empty_resources)

    def tearDown(self) -> None:
        self.scheduler.docker_client.close()

    def test_return42(self):
        """

        """
        ret = self.scheduler.return42()
        self.assertEqual(ret, 42)

    def test_single_node_1(self):
        """
            Test single node scheduling when no resources are available
        """
        test = self.scheduler.single_node(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_node_1(self):
        """
            Test fill node scheduling when no resources are available
        """
        test = self.scheduler.fill_nodes(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_1(self):
        """
            Test round_robin scheduling when no resources are available
        """
        test = self.scheduler.round_robin(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)
