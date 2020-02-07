import unittest
from ..scheduler.scheduler import Scheduler
from . import EmptyResourceManager

class TestScheduler(unittest.TestCase):

    def setUp(self) -> None:
        #Various resource manager states
        self.empty_resources = EmptyResourceManager()

        #Create a scheduler with no resources
        self.scheduler = Scheduler(resource_manager=self.empty_resources)

    def test_return42(self):
        """

        """
        ret = self.scheduler.return42()
        self.assertEqual(ret, 42)
