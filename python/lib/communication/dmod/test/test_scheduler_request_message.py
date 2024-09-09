import json
import unittest
from dmod.core.meta_data import TimeRange
from ..communication.maas_request import NGENRequest, NWMRequest
from ..communication.scheduler_request import SchedulerRequestMessage


class TestSchedulerRequestMessage(unittest.TestCase):

    # TODO: add test to make sure SchedulerRequestMessage picks up memory from model request

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = SchedulerRequestMessage

        # Example 0 - NWMRequest
        memory_ex_0 = 1_000_000
        raw_json_str_0 = '{"allocation_paradigm": "ROUND_ROBIN", "model_request": {"allocation_paradigm": "ROUND_ROBIN", "cpu_count": 1, "job_type": "nwm", "memory": ' + str(memory_ex_0) + ',"request_body": {"nwm": {"config_data_id": "1", "data_requirements": [{"category": "CONFIG", "domain": {"continuous": {}, "data_format": "NWM_CONFIG", "discrete": {"DATA_ID": {"values": ["1"], "variable": "DATA_ID"}}}, "is_input": true}]}}, "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone", "cpus": 4, "mem": ' + str(memory_ex_0) + '}'
        raw_json_obj_0 = json.loads(raw_json_str_0)
        sorted_json_str_0 = json.dumps(raw_json_obj_0, sort_keys=True)
        self.request_strings.append(sorted_json_str_0)
        self.request_jsons.append({
            "allocation_paradigm": "ROUND_ROBIN",
            "model_request": {
                "allocation_paradigm": "ROUND_ROBIN",
                "cpu_count": 1,
                "job_type": "nwm",
                "memory": memory_ex_0,
                "request_body": {
                    "nwm": {
                        "config_data_id": "1",
                        "data_requirements": [
                            {
                                "category": "CONFIG",
                                "domain": {
                                    "continuous": {},
                                    "data_format": "NWM_CONFIG",
                                    "discrete": {"DATA_ID": {"values": ["1"], "variable": "DATA_ID"}}
                                },
                                "is_input": True
                            }
                        ]
                    }
                },
                "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"
            },
            "user_id": "someone",
            "cpus": 4,
            "mem": memory_ex_0
        })


        self.request_objs.append(
            SchedulerRequestMessage(model_request=NWMRequest.factory_init_from_deserialized_json(
                {
                    "allocation_paradigm": "ROUND_ROBIN",
                    "cpu_count": 1,
                    "job_type": "nwm",
                    "memory": 1_000_000,
                    "request_body": {
                        "nwm": {
                            "config_data_id": "1",
                            "data_requirements": [
                                {
                                    "category": "CONFIG",
                                    "domain": {
                                        "continuous": [],
                                        "data_format": "NWM_CONFIG",
                                        "discrete": [{"values": ["1"], "variable": "DATA_ID"}]
                                    },
                                    "is_input": True
                                }
                            ]
                        }
                    },
                    "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
                user_id='someone',
                cpus=4,
                memory=memory_ex_0,
                allocation_paradigm='ROUND_ROBIN'))

        # Example 1 - NGenRequest
        cpu_count_ex_1 = 288
        memory_ex_1 = 2_500_000
        cat_ids_list = ['cat-1', 'cat-2', 'cat-3']
        cat_ids_str = '["{}", "{}", "{}"]'.format(*cat_ids_list)
        time_range = TimeRange.factory_init_from_deserialized_json({"begin": "2012-05-01 00:00:00",
                                                                    "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                                                    "end": "2012-05-31 23:00:00",
                                                                    "subclass": "TimeRange",
                                                                    "variable": "TIME"})
        raw_json_str_1 = '{"allocation_paradigm": "SINGLE_NODE", "cpus": ' + str(cpu_count_ex_1) + ', "mem": ' + str(memory_ex_1) + ', "model_request": {"allocation_paradigm": "ROUND_ROBIN", "cpu_count": ' + str(cpu_count_ex_1) + ', "job_type": "ngen", "memory": ' + str(memory_ex_1) + ', "request_body": {"bmi_config_data_id": "simple-bmi-cfe-1", "hydrofabric_data_id": "hydrofabric-huc01-copy-288", "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81", "realization_config_data_id": "huc01-simple-realization-config-1", "time_range": ' + str(time_range) +'}, "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919", "worker_version": "latest"}, "user_id": "someone"}'
        raw_json_obj_1 = json.loads(raw_json_str_1)
        sorted_json_str_1 = json.dumps(raw_json_obj_1, sort_keys=True)
        self.request_strings.append(sorted_json_str_1)
        self.request_jsons.append(
            {
                "allocation_paradigm": "SINGLE_NODE",
                "cpus": cpu_count_ex_1,
                "mem": memory_ex_1,
                "model_request": {
                    "allocation_paradigm": "ROUND_ROBIN",
                    "cpu_count": cpu_count_ex_1,
                    "job_type": "ngen",
                    "memory": memory_ex_1,
                    "request_body": {
                        "bmi_config_data_id": "simple-bmi-cfe-1",
                        "hydrofabric_data_id": "hydrofabric-huc01-copy-288",
                        "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81",
                        "realization_config_data_id": "huc01-simple-realization-config-1",
                        "time_range": time_range.to_dict()
                    },
                    "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919",
                    "worker_version": "latest"
                },
                "user_id": "someone"
            })
        model_request = NGENRequest(
            allocation_paradigm='ROUND_ROBIN',
            cpu_count=288,
            memory=memory_ex_1,
            session_secret='675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919',
            request_body={
                'time_range': time_range,
                'realization_config_data_id': 'huc01-simple-realization-config-1',
                'hydrofabric_data_id': 'hydrofabric-huc01-copy-288',
                'hydrofabric_uid': '72c2a0220aa7315b50e55b6c5b68f927ac1d9b81',
                'bmi_config_data_id': 'simple-bmi-cfe-1'
            }
        )
        self.request_objs.append(SchedulerRequestMessage(model_request=model_request, user_id='someone',
                                                         allocation_paradigm='SINGLE_NODE', cpus=288, memory=memory_ex_1))

        # Example 2 - like example 1, but without explicit memory at SchedulerRequest level (only inner model request)
        cpu_count_ex_2 = 288
        memory_ex_2 = 2_500_000
        cat_ids_list = ['cat-1', 'cat-2', 'cat-3']
        cat_ids_str = '["{}", "{}", "{}"]'.format(*cat_ids_list)
        time_range = TimeRange.factory_init_from_deserialized_json({"begin": "2012-05-01 00:00:00",
                                                                    "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                                                    "end": "2012-05-31 23:00:00",
                                                                    "subclass": "TimeRange",
                                                                    "variable": "TIME"})
        raw_json_str_2 = '{"allocation_paradigm": "SINGLE_NODE", "cpus": ' + str(cpu_count_ex_2) + ', "model_request": {"allocation_paradigm": "ROUND_ROBIN", "cpu_count": ' + str(cpu_count_ex_2) + ', "job_type": "ngen", "memory": ' + str(memory_ex_2) + ', "request_body": {"bmi_config_data_id": "simple-bmi-cfe-1", "hydrofabric_data_id": "hydrofabric-huc01-copy-288", "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81", "realization_config_data_id": "huc01-simple-realization-config-1", "time_range": ' + str(time_range) +'}, "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919", "worker_version": "latest"}, "user_id": "someone"}'
        raw_json_obj_2 = json.loads(raw_json_str_2)
        sorted_json_str_2 = json.dumps(raw_json_obj_2, sort_keys=True)
        self.request_strings.append(sorted_json_str_2)
        self.request_jsons.append(
            {
                "allocation_paradigm": "SINGLE_NODE",
                "cpus": cpu_count_ex_2,
                #"mem": memory_ex_2,
                "model_request": {
                    "allocation_paradigm": "ROUND_ROBIN",
                    "cpu_count": cpu_count_ex_2,
                    "job_type": "ngen",
                    "memory": memory_ex_2,
                    "request_body": {
                        "bmi_config_data_id": "simple-bmi-cfe-1",
                        "hydrofabric_data_id": "hydrofabric-huc01-copy-288",
                        "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81",
                        "realization_config_data_id": "huc01-simple-realization-config-1",
                        "time_range": time_range.to_dict()
                    },
                    "session_secret": "675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919",
                    "worker_version": "latest"
                },
                "user_id": "someone"
            })
        model_request = NGENRequest(
            allocation_paradigm='ROUND_ROBIN',
            cpu_count=cpu_count_ex_2,
            memory=memory_ex_2,
            session_secret='675b2f8826f69f97c01fe4d7add30420322cd21a790ddc68a5b3c149966de919',
            request_body={
                'time_range': time_range,
                'realization_config_data_id': 'huc01-simple-realization-config-1',
                'hydrofabric_data_id': 'hydrofabric-huc01-copy-288',
                'hydrofabric_uid': '72c2a0220aa7315b50e55b6c5b68f927ac1d9b81',
                'bmi_config_data_id': 'simple-bmi-cfe-1'
            }
        )
        self.request_objs.append(SchedulerRequestMessage(model_request=model_request, user_id='someone',
                                                         allocation_paradigm='SINGLE_NODE', cpus=cpu_count_ex_2))

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

    def test_memory_2_a(self):
        example_index = 2
        base_obj = self.request_objs[example_index]
        test_obj = SchedulerRequestMessage(model_request=base_obj.model_request, user_id=base_obj.user_id,
                                           allocation_paradigm=base_obj.allocation_paradigm, cpus=base_obj.cpus)
        self.assertEqual(test_obj.memory, base_obj.model_request.memory)
