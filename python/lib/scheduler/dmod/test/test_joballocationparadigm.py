import unittest
from ..scheduler.job.job import AllocationParadigm
from dmod.communication import SchedulerRequestMessage


class TestJobAllocationParadigm(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    # Test that the default selection agrees with the default paradigm value string from SchedulerRequestMessage
    def test_get_default_selection_1_a(self):
        default_val = AllocationParadigm.get_default_selection()
        default_sch_msg_str = SchedulerRequestMessage.default_allocation_paradigm_str()
        default_msg_val = AllocationParadigm.get_from_name(default_sch_msg_str, strict=True)
        self.assertEqual(default_msg_val, default_val)

    # Test that a bogus name returns the default when not strict
    def test_get_from_name_1_a(self):
        test_name = 'blah_blah_blah'
        parse_value = AllocationParadigm.get_from_name(test_name, strict=False)
        self.assertEqual(parse_value, AllocationParadigm.get_default_selection())

    # Test that a bogus name returns None when strict
    def test_get_from_name_1_b(self):
        test_name = 'blah_blah_blah'
        parse_value = AllocationParadigm.get_from_name(test_name, strict=True)
        self.assertIsNone(parse_value)

    # Test that a good name (but not an exact match) returns the expected type when strict is false
    def test_get_from_name_2_a(self):
        base_type = AllocationParadigm.SINGLE_NODE
        test_name = base_type.name.lower()
        parse_value = AllocationParadigm.get_from_name(test_name, strict=False)
        self.assertEqual(parse_value, base_type)

    # Test that a good name (but not an exact match) returns the expected type when strict is true
    def test_get_from_name_2_b(self):
        base_type = AllocationParadigm.SINGLE_NODE
        test_name = base_type.name.lower()
        parse_value = AllocationParadigm.get_from_name(test_name, strict=True)
        self.assertEqual(parse_value, base_type)

    # Test that a good name (an exact match) returns the expected type when strict is false
    def test_get_from_name_3_a(self):
        base_type = AllocationParadigm.FILL_NODES
        test_name = base_type.name
        parse_value = AllocationParadigm.get_from_name(test_name, strict=False)
        self.assertEqual(parse_value, base_type)

    #Test that a good name (an exact match) returns the expected type when strict is true
    def test_get_from_name_3_b(self):
        base_type = AllocationParadigm.FILL_NODES
        test_name = base_type.name
        parse_value = AllocationParadigm.get_from_name(test_name, strict=True)
        self.assertEqual(parse_value, base_type)
