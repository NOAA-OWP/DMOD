import unittest
from dmod.core.meta_data import TimeRange
from ..communication.maas_request import ModelExecRequest, NGENRequest, NWMRequest


class TestModelExecRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []
        self.request_class_types = []

        # Example 0 - NWM request
        self.request_class_types.append(NWMRequest)
        self.request_strings.append('{"allocation_paradigm": "ROUND_ROBIN", "cpu_count": 1, "job_type": "nwm", "request_body": {"nwm": {"config_data_id": "1", "data_requirements": [{"category": "CONFIG", "domain": {"continuous": [], "data_format": "NWM_CONFIG", "discrete": [{"values": ["1"], "variable": "DATA_ID"}]}, "is_input": true}]}}, "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')

        self.request_jsons.append({
            "allocation_paradigm": "ROUND_ROBIN",
            "cpu_count": 1,
            "job_type": "nwm",
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
            "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"})
        self.request_objs.append(
            NWMRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                       cpu_count=1,
                       allocation_paradigm='ROUND_ROBIN',
                       config_data_id="1"))

        # Example 1 - NGen request
        self.request_class_types.append(NGENRequest)
        def create_time_range(begin, end, var=None) -> TimeRange:
            serialized = {'begin': begin, 'end': end, 'datetime_pattern': '%Y-%m-%d %H:%M:%S',
                          'subclass': TimeRange.__name__, 'variable': 'Time' if var is None else var}
            return TimeRange.factory_init_from_deserialized_json(serialized)

        time_range = create_time_range('2022-01-01 00:00:00', '2022-03-01 00:00:00')
        cpu_count_ex_0 = 4
        self.request_strings.append(
            '{"allocation_paradigm": "SINGLE_NODE", "cpu_count": ' + str(cpu_count_ex_0) + ', "job_type": "ngen", '
                                                                                           '"request_body": '
                                                                                           '{"bmi_config_data_id": "02468", "hydrofabric_data_id": "9876543210", "hydrofabric_uid": "0123456789", '
                                                                                           '"partition_config_data_id": "part1234", "realization_config_data_id": "02468", '
                                                                                           '"time_range": ' + time_range.to_json() + '}, '
                                                                                                                                     '"session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({
            'allocation_paradigm': 'SINGLE_NODE',
            'cpu_count': cpu_count_ex_0,
            'job_type': 'ngen',
            'request_body': {
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'realization_config_data_id': '02468',
                'partition_config_data_id': 'part1234'
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        self.request_objs.append(
            NGENRequest(request_body={
                'time_range': time_range,
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': "0123456789",
                'bmi_config_data_id': '02468',
                'partition_cfg_data_id': 'part1234',
                'realization_config_data_id': '02468'},
                session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                cpu_count=cpu_count_ex_0,
                allocation_paradigm='SINGLE_NODE'))

    def test_factory_init_correct_subtype_from_deserialized_json_0_a(self):
        """
        Test function for example 0, an ::class:`NWMRequest`.
        """
        ex_idx = 0
        ex_json = self.request_jsons[ex_idx]
        expected_type = self.request_class_types[ex_idx]
        actual_obj = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(ex_json)
        self.assertIsInstance(actual_obj, expected_type)

    def test_factory_init_correct_subtype_from_deserialized_json_0_b(self):
        """
        Test function for example 0, ensuring the object is deserialized as expected.
        """
        ex_idx = 0
        ex_json = self.request_jsons[ex_idx]
        expected_obj = self.request_objs[ex_idx]
        actual_obj = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(ex_json)
        self.assertEqual(expected_obj, actual_obj)

    def test_factory_init_correct_subtype_from_deserialized_json_1_a(self):
        """
        Test function for example 0, an ::class:`NGENRequest`.
        """
        ex_idx = 1
        ex_json = self.request_jsons[ex_idx]
        expected_type = self.request_class_types[ex_idx]
        actual_obj = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(ex_json)
        self.assertIsInstance(actual_obj, expected_type)

    def test_factory_init_correct_subtype_from_deserialized_json_1_b(self):
        """
        Test function for example 0, ensuring the object is deserialized as expected.
        """
        ex_idx = 1
        ex_json = self.request_jsons[ex_idx]
        expected_obj = self.request_objs[ex_idx]
        actual_obj = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(ex_json)
        self.assertEqual(expected_obj, actual_obj)
