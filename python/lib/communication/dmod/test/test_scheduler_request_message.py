import unittest
from ..communication.maas_request import NWMRequest
from ..communication.scheduler_request import SchedulerRequestMessage


class TestSchedulerRequestMessage(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = SchedulerRequestMessage

        # Example 0
        self.request_strings.append(
            '{"model_request": {"model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}}, "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone", "cpus": 4, "mem": 500000, "allocation": "single-node"}')
        self.request_jsons.append({"model_request": {
            "model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}},
            "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone",
                                   "cpus": 4, "mem": 500000, "allocation": "single-node"})
        self.request_objs.append(
            SchedulerRequestMessage(model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}},
                 "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
                                    user_id='someone',
                                    cpus=4,
                                    mem=500000,
                                    allocation_paradigm='single-node'))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that factory init method for deserializing produces an equal object to the pre-created object for the
        examples at the 0th index.
        """
        example_index = 0
        obj = SchedulerRequestMessage.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_to_dict_0_a(self):
        """
        Assert that the example object at the 0th index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 0th index.
        """
        example_index = 0
        ex_dict = self.request_objs[example_index].to_dict()
        self.assertEqual(ex_dict, self.request_jsons[example_index])

    def test_to_json_0_a(self):
        """
        Assert that the example object at the 0th index serializes to a JSON string as expected by comparing to the
        pre-set JSON dict example at the 0th index.
        """
        example_index = 0
        ex_json_str = self.request_objs[example_index].to_json()
        self.assertEqual(ex_json_str, self.request_strings[example_index])
