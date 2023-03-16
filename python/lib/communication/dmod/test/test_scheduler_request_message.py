import json
import unittest
from dmod.core.meta_data import TimeRange
from ..communication.maas_request import NGENRequest, NWMRequest
from ..communication.scheduler_request import SchedulerRequestMessage


class TestSchedulerRequestMessage(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = SchedulerRequestMessage

        # Example 0 - NWMRequest
        raw_json_str_0 = '{"allocation_paradigm": "ROUND_ROBIN", "model_request": {"model": {"nwm": {"allocation_paradigm": "ROUND_ROBIN", "config_data_id": "1", "cpu_count": 1, "data_requirements": [{"domain": {"data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "DATA_ID", "values": ["1"]}]}, "is_input": true, "category": "CONFIG"}]}}, "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone", "cpus": 4, "mem": 500000}'
        raw_json_obj_0 = json.loads(raw_json_str_0)
        sorted_json_str_0 = json.dumps(raw_json_obj_0, sort_keys=True)
        self.request_strings.append(sorted_json_str_0)
        self.request_jsons.append({"allocation_paradigm": "ROUND_ROBIN", "model_request": {
            "model": {"nwm": {"allocation_paradigm": "ROUND_ROBIN", "config_data_id": "1", "cpu_count": 1, "data_requirements": [{"domain": {
                "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "DATA_ID", "values": ["1"]}]},
                "is_input": True,
                "category": "CONFIG"}]}},
            "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone",
            "cpus": 4, "mem": 500000})


        self.request_objs.append(
            SchedulerRequestMessage(model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"allocation_paradigm": "ROUND_ROBIN", "config_data_id": "1", "cpu_count": 1, "data_requirements": [{"domain": {"data_format": "NWM_CONFIG",
                                                                                            "continuous": [],
                                                                                            "discrete": [
                                                                                                {"variable": "DATA_ID",
                                                                                                 "values": ["1"]}]},
                                                                                 "is_input": True,
                                                                                 "category": "CONFIG"}]}},
                 "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
                user_id='someone',
                cpus=4,
                mem=500000,
                allocation_paradigm='ROUND_ROBIN'))

        # Example 1 - NGenRequest
        raw_json_str_1 = '{"allocation_paradigm": "SINGLE_NODE", "cpus": 288, "mem": 500000, "model_request": {"model": {"allocation_paradigm": "SINGLE_NODE", "bmi_config_data_id": "simple-bmi-cfe-1", "config_data_id": "huc01-simple-realization-config-1", "cpu_count": 288, "hydrofabric_data_id": "hydrofabric-huc01-copy-288", "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81", "name": "ngen", "time_range": {"begin": "2012-05-01 00:00:00", "datetime_pattern": "%Y-%m-%d %H:%M:%S", "end": "2012-05-31 23:00:00", "subclass": "TimeRange", "variable": "TIME"}}, "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919"}, "user_id": "someone"}'
        raw_json_obj_1 = json.loads(raw_json_str_1)
        sorted_json_str_1 = json.dumps(raw_json_obj_1, sort_keys=True)
        self.request_strings.append(sorted_json_str_1)
        self.request_jsons.append({"allocation_paradigm": "SINGLE_NODE", "cpus": 288, "mem": 500000, "model_request": {
            "model": {"allocation_paradigm": "SINGLE_NODE", "bmi_config_data_id": "simple-bmi-cfe-1", "config_data_id": "huc01-simple-realization-config-1",
                      "cpu_count": 288, "hydrofabric_data_id": "hydrofabric-huc01-copy-288",
                      "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81", "name": "ngen",
                      "time_range": {"begin": "2012-05-01 00:00:00", "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                     "end": "2012-05-31 23:00:00", "subclass": "TimeRange", "variable": "TIME"}},
            "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919"},
                                   "user_id": "someone"})

        time_range = TimeRange.factory_init_from_deserialized_json({"begin": "2012-05-01 00:00:00",
                                                                    "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                                                    "end": "2012-05-31 23:00:00",
                                                                    "subclass": "TimeRange",
                                                                    "variable": "TIME"})
        model_request = NGENRequest(time_range=time_range,
                                    cpu_count=288,
                                    allocation_paradigm='SINGLE_NODE',
                                    config_data_id='huc01-simple-realization-config-1',
                                    session_secret='675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919',
                                    hydrofabric_data_id='hydrofabric-huc01-copy-288',
                                    hydrofabric_uid='72c2a0220aa7315b50e55b6c5b68f927ac1d9b81',
                                    bmi_cfg_data_id='simple-bmi-cfe-1')
        self.request_objs.append(SchedulerRequestMessage(model_request=model_request, user_id='someone',
                                                         allocation_paradigm='SINGLE_NODE', cpus=288, mem=500000))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that factory init method for deserializing produces an equal object to the pre-created object for the
        examples at the 0th index.
        """
        example_index = 0
        obj = SchedulerRequestMessage.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Assert that factory init method for deserializing produces an equal object to the pre-created object for the
        examples at the 1st index.
        """
        example_index = 1
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

    def test_to_dict_1_a(self):
        """
        Assert that the example object at the 1st index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 1st index.
        """
        example_index = 1
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

    def test_to_json_1_a(self):
        """
        Assert that the example object at the 1st index serializes to a JSON string as expected by comparing to the
        pre-set JSON dict example at the 1st index.
        """
        example_index = 1
        ex_json_str = self.request_objs[example_index].to_json()
        self.assertEqual(ex_json_str, self.request_strings[example_index])
