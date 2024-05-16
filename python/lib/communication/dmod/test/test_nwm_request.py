import json
import unittest
from dmod.core.meta_data import StandardDatasetIndex
from ..communication.maas_request import NWMRequest, NWMRequestResponse
from ..test.test_nwm_request_response import TestNWMRequestResponse


class TestNWMRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = NWMRequest

        # TODO: improve coverage through more examples

        # Example 0
        self.request_strings.append('{"allocation_paradigm": "ROUND_ROBIN", "cpu_count": 1, "job_type": "nwm", "memory": 1000000, "request_body": {"nwm": {"config_data_id": "1", "data_requirements": [{"category": "CONFIG", "domain": {"continuous": {}, "data_format": "NWM_CONFIG", "discrete": {"DATA_ID": {"values": ["1"], "variable": "DATA_ID"}}}, "is_input": true}]}}, "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')

        self.request_jsons.append({
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
                                "continuous": {},
                                "data_format": "NWM_CONFIG",
                                "discrete": {StandardDatasetIndex.DATA_ID: {"values": ["1"], "variable": "DATA_ID"}}
                            },
                            "is_input": True
                        }
                    ]
                }
            },
            "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"})
        self.request_objs.append(
            NWMRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                       cpu_count=1,
                       memory=1_000_000,
                       allocation_paradigm='ROUND_ROBIN',
                       config_data_id="1"))

        # Example 1 - like example 0, but with the object initialized with the default 'parameters' value
        self.request_strings.append('{"allocation_paradigm": "SINGLE_NODE", "cpu_count": 1, "job_type": "nwm", "memory": 1000000, "request_body": {"nwm": {"config_data_id": "2", "data_requirements": [{"category": "CONFIG", "domain": {"continuous": {}, "data_format": "NWM_CONFIG", "discrete": {"DATA_ID": {"values": ["2"], "variable": "DATA_ID"}}}, "is_input": true}]}}, "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({"allocation_paradigm": "SINGLE_NODE", "cpu_count": 1, "job_type": "nwm", "memory": 1_000_000, "request_body": {"nwm": {"config_data_id": "2", "data_requirements": [{"category": "CONFIG",
                                                                                                   "domain": {
            "continuous": {}, "data_format": "NWM_CONFIG", "discrete": {StandardDatasetIndex.DATA_ID: {"values": ["2"], "variable": "DATA_ID"}}},
                                                                                                   "is_input": True}]}},
                                   'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'})
        self.request_objs.append(
            NWMRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                       cpu_count=1,
                       memory=1_000_000,
                       allocation_paradigm='SINGLE_NODE',
                       config_data_id='2'))

    def test_get_model_name_0_a(self):
        """
        Test that the correct model name is returned.
        """
        example_index = 0
        obj = self.request_objs[example_index]
        expected = "nwm"
        actual = obj.get_model_name()
        self.assertEqual(expected, actual)

    def test_get_model_name_0_b(self):
        """
        Test that the model name returned matches the class variable.
        """
        example_index = 0
        obj = self.request_objs[example_index]
        expected = obj.__class__.model_name
        actual = obj.get_model_name()
        self.assertEqual(expected, actual)

    def test_get_model_name_0_c(self):
        """
        Test that the model name matches the job type value.
        """
        example_index = 0
        obj = self.request_objs[example_index]
        self.assertEqual(obj.__class__.get_model_name(), obj.job_type)

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 0th index.
        """
        example_index = 0
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_0_b(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 0th index.
        """
        example_index = 0
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 1th index.
        """
        example_index = 1
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_1_b(self):
        """
        Assert that :meth:`NWMRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 1th index.
        """
        example_index = 1
        obj = NWMRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    # TODO: more tests for this
    def test_factory_init_correct_response_subtype_1_a(self):
        """
        Test ``factory_init_correct_response_subtype()`` that a valid response object is deserialized from the relevant
        example case string.
        """
        example_str = TestNWMRequestResponse.get_raw_response_string_example_1()
        json_obj = json.loads(example_str)
        obj = NWMRequest.factory_init_correct_response_subtype(json_obj)
        self.assertEqual(obj.__class__, NWMRequestResponse)

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
        Assert that the example object at the 1th index serializes to a dict as expected by comparing to the pre-set
        JSON dict example at the 1th index.
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
        Assert that the example object at the 1th index serializes to a JSON string as expected by comparing to the
        pre-set JSON dict example at the 1th index.
        """
        example_index = 1
        ex_json_str = self.request_objs[example_index].to_json()
        self.assertEqual(ex_json_str, self.request_strings[example_index])


if __name__ == '__main__':
    unittest.main()
