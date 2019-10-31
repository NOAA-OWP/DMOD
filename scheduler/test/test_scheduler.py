import unittest

from scheduler.scheduler import Scheduler
from scheduler.scheduler import check_for_incoming_req
# from scheduler.request import Request

# from scheduler.utils import keynamehelper
# from scheduler.imports import generate, parsing_nested

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler
 
    def test_3(self):
        returnValue = check_for_incoming_req()
        self.assertEqual(returnValue, 1)
 
    """
    def test_4(self):
        self.func.increment_state()
        self.assertEqual(self.func.state, 1)
 
    def test_5(self):
        self.func.increment_state()
        self.func.increment_state()
        self.func.clear_state()
        self.assertEqual(self.func.state, 0)
    """
 
if __name__ == '__main__':
    unittest.main()
