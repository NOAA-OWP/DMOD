import unittest
from ..communication.maas_request import NgenCalibrationRequest
from dmod.core.meta_data import TimeRange


class TestNgenCalibrationRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.request_cpu_counts = dict()
        self.request_strings = dict()
        self.request_jsons = dict()
        self.request_objs = dict()
        self.time_ranges = dict()
        self.calibration_config_ds = dict()

        # Example 0
        ex_idx = 0

        time_range = TimeRange.parse_from_string("2022-01-01 00:00:00 to 2022-03-01 00:00:00")
        iterations = 100
        obj_func = 'nnse'
        model_strategy = 'estimation'
        cpu_count = 4

        self.request_cpu_counts[ex_idx] = cpu_count
        self.time_ranges[ex_idx] = time_range
        self.request_strings[ex_idx] = (
            '{'
            '   "allocation_paradigm": "SINGLE_NODE", '
            '   "cpu_count": ' + str(cpu_count) + ', '
            '   "job_type": "ngen-cal", '
            '   "request_body": {'
            '       "bmi_config_data_id": "02468", '
            '       "hydrofabric_data_id": "9876543210", '
            '       "hydrofabric_uid": "0123456789", '
            '       "iterations":' + str(iterations) + ', '
            '       "model_params": {}, '                                           
            '       "model_strategy":' + model_strategy + ','
            '       "objective_function":' + obj_func + ', '
            '       "partition_config_data_id": "part1234", '
            '       "realization_config_data_id": "02468", '
            '       "time_range": ' + time_range.to_json() +
            '   }, '
            '   "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"'
            '}')

        self.request_jsons[ex_idx] = {
            'allocation_paradigm': 'SINGLE_NODE',
            'cpu_count': cpu_count,
            'job_type': 'ngen-cal',
            'request_body': {
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'realization_config_data_id': '02468',
                'partition_config_data_id': 'part1234',
                'objective_function': obj_func,
                'iterations': iterations,
                'model_strategy': model_strategy,
                'model_params': {}
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        }
        self.request_objs[ex_idx] = NgenCalibrationRequest(
                request_body={
                    'time_range': time_range,
                    'hydrofabric_data_id': '9876543210',
                    'hydrofabric_uid': "0123456789",
                    'bmi_config_data_id': '02468',
                    'partition_cfg_data_id': 'part1234',
                    'realization_config_data_id': '02468',
                    'objective_function': obj_func,
                    'iterations': iterations,
                    'model_strategy': model_strategy,
                    'model_params': {}
                },
                session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                cpu_count=cpu_count,
                allocation_paradigm='SINGLE_NODE')

        # Example 1 - example without explicit calibration params
        ex_idx = 1

        config_ds_id = "config_ds_1"
        self.calibration_config_ds[1] = config_ds_id
        self.request_cpu_counts[ex_idx] = cpu_count
        self.time_ranges[ex_idx] = time_range
        self.request_strings[ex_idx] = (
            '{'
            '   "allocation_paradigm": "SINGLE_NODE", '
            '   "cpu_count": ' + str(cpu_count) + ', '
            '   "job_type": "ngen-cal", '
            '   "request_body": {'
            '       "bmi_config_data_id": "02468", '
            '       "hydrofabric_data_id": "9876543210", '
            '       "hydrofabric_uid": "0123456789", '
            '       "ngen_cal_config_data_id":' + config_ds_id + ','
            '       "partition_config_data_id": "part1234", '
            '       "realization_config_data_id": "02468", '
            '       "time_range": ' + time_range.to_json() +
            '   }, '
            '   "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"'
            '}')

        self.request_jsons[ex_idx] = {
            'allocation_paradigm': 'SINGLE_NODE',
            'cpu_count': cpu_count,
            'job_type': 'ngen-cal',
            'request_body': {
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'realization_config_data_id': '02468',
                'partition_config_data_id': 'part1234',
                'ngen_cal_config_data_id': config_ds_id
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        }
        self.request_objs[ex_idx] = NgenCalibrationRequest(
                request_body={
                    'time_range': time_range,
                    'hydrofabric_data_id': '9876543210',
                    'hydrofabric_uid': "0123456789",
                    'bmi_config_data_id': '02468',
                    'partition_cfg_data_id': 'part1234',
                    'realization_config_data_id': '02468',
                    'ngen_cal_config_data_id': config_ds_id
                },
                session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                cpu_count=cpu_count,
                allocation_paradigm='SINGLE_NODE')

        # Example 2 (only JSON) - example that should fail to init due no objective function param being supplied
        ex_idx = 2

        self.request_cpu_counts[ex_idx] = cpu_count
        self.time_ranges[ex_idx] = time_range

        self.request_jsons[ex_idx] = {
            'allocation_paradigm': 'SINGLE_NODE',
            'cpu_count': cpu_count,
            'job_type': 'ngen-cal',
            'request_body': {
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'realization_config_data_id': '02468',
                'partition_config_data_id': 'part1234',
                'iterations': iterations,
                'model_strategy': model_strategy,
                'model_params': {}
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        }

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Test that example 0 can be initialized using factory method.
        """
        ex_idx = 0

        json_val = self.request_jsons[ex_idx]
        ex_obj = self.request_objs[ex_idx]

        init_obj = NgenCalibrationRequest.factory_init_from_deserialized_json(json_val)
        self.assertEqual(ex_obj, init_obj)

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Test that example 1 can be initialized using factory method.
        """
        ex_idx = 1

        json_val = self.request_jsons[ex_idx]
        ex_obj = self.request_objs[ex_idx]

        init_obj = NgenCalibrationRequest.factory_init_from_deserialized_json(json_val)
        self.assertEqual(ex_obj, init_obj)

    def test_init_0_a(self):
        ex_idx = 0
        request_obj = self.request_objs[ex_idx]
        self.assertIsNotNone(request_obj)

    def test_init_0_b(self):
        """
        Test that example 0 can be initialized from JSON.
        """
        ex_idx = 0

        json_val = self.request_jsons[ex_idx]
        ex_obj = self.request_objs[ex_idx]

        init_obj = NgenCalibrationRequest(**json_val)
        self.assertEqual(ex_obj, init_obj)

    def test_init_1_a(self):
        ex_idx = 1
        request_obj = self.request_objs[ex_idx]
        self.assertIsNotNone(request_obj)

    def test_init_1_b(self):
        """
        Test that example 1 can be initialized from JSON.
        """
        ex_idx = 1

        json_val = self.request_jsons[ex_idx]
        ex_obj = self.request_objs[ex_idx]

        init_obj = NgenCalibrationRequest(**json_val)
        self.assertEqual(ex_obj, init_obj)

    def test_init_2_a(self):
        """
        Test that example 2 fails to init due to no ``objective_function`` param.
        """
        ex_idx = 2

        json_val = self.request_jsons[ex_idx]
        try:
            obj = NgenCalibrationRequest(**json_val)
        except Exception as e:
            r = 1

        self.assertRaises(ValueError, NgenCalibrationRequest, **json_val)
