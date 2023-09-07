import unittest
from ..core.serializable import BasicResultIndicator


class TestBasicResultIndicator(unittest.TestCase):

    def setUp(self) -> None:
        self.ex_objs = []

        # Example 0: Successful, with no message and no data
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful"))

        # Example 1: Successful, with message but no data
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked"))

        # Example 2: Successful, with message and list of ints in data
        data_item = list(range(5))
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked",
                                                 data=data_item))

        # Example 3: Failed, with message and dict of int values in data (keys are value as string, prefixed by "i-")
        data_item = {f"i-{i!s}": i for i in range(5)}
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked",
                                                 data=data_item))

        # Example 4: Successful, with message and list of floats in data
        data_item = [0.0, 1.0]
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked",
                                                 data=data_item))

        # Example 5: Successful, with message and list of strings in data
        data_item = ["one", "two"]
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked",
                                                 data=data_item))

        # Example 6: Successful, with message and list of bools in data
        data_item = [True, False]
        self.ex_objs.append(BasicResultIndicator(success=True, reason="Successful", message="This worked",
                                                 data=data_item))

    def tearDown(self) -> None:
        pass

    def test_data_0_a(self):
        """ Test that an object that is not initialized with a ``data`` param gets a ``None`` value for it. """
        ex_idx = 0
        obj = self.ex_objs[ex_idx]

        self.assertIsNone(obj.data)

    def test_data_2_a(self):
        """ Test that an object with a ``data`` param has it. """
        ex_idx = 2
        obj = self.ex_objs[ex_idx]

        self.assertIsInstance(obj.data, list)

    def test_data_2_b(self):
        """ Test that an object with a ``data`` param has expected ``int`` values. """
        ex_idx = 2
        obj = self.ex_objs[ex_idx]

        self.assertEqual(obj.data, [0, 1, 2, 3, 4])

    def test_data_3_b(self):
        """ Test that an object with a ``data`` diction param has expected values. """
        ex_idx = 3
        obj = self.ex_objs[ex_idx]

        self.assertEqual(obj.data, {"i-0": 0, "i-1": 1, "i-2": 2, "i-3": 3, "i-4": 4})

    def test_data_4_b(self):
        """ Test that an object with a ``data`` param has expected float values. """
        ex_idx = 4
        obj = self.ex_objs[ex_idx]

        self.assertEqual(obj.data, [0.0, 1.0])

    def test_data_5_b(self):
        """ Test that an object with a ``data`` param has expected string values. """
        ex_idx = 5
        obj = self.ex_objs[ex_idx]

        self.assertEqual(obj.data, ["one", "two"])

    def test_data_6_b(self):
        """ Test that an object with a ``data`` param has expected bool values. """
        ex_idx = 6
        obj = self.ex_objs[ex_idx]

        self.assertEqual(obj.data, [True, False])
