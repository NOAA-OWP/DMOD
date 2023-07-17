import unittest
from ..communication.maas_request.ngen.ngen_cal_request_estimation_config import NgenCalRequestEstimationConfig
from dmod.core.meta_data import TimeRange


class TestNgenCalRequestEstimationConfig(unittest.TestCase):

    def setUp(self) -> None:
        self.config_strings = dict()
        self.config_jsons = dict()
        self.config_objs = dict()
        self.time_ranges = dict()
        self.calibration_config_ds = dict()

        # Example 0
        ex_idx = 0

        time_range = TimeRange.parse_from_string("2022-01-01 00:00:00 to 2022-03-01 00:00:00")
        iterations = 100
        obj_func = 'nnse'
        model_strategy = 'estimation'
        cpu_count = 4

        self.time_ranges[ex_idx] = time_range
        self.config_strings[ex_idx] = (
                '{'
                '   "bmi_config_data_id": "02468", '
                '   "hydrofabric_data_id": "9876543210", '
                '   "hydrofabric_uid": "0123456789", '
                '   "iterations":' + str(iterations) + ', '
                '   "model_params": {}, '
                '   "model_strategy":' + model_strategy + ','
                '   "objective_function":' + obj_func + ', '
                '   "partition_config_data_id": "part1234", '
                '   "realization_config_data_id": "02468", '
                '   "time_range": ' + time_range.to_json() +
                '}'
        )
        self.config_jsons[ex_idx] = {
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
        }
        self.config_objs[ex_idx] = NgenCalRequestEstimationConfig(
            time_range=time_range,
            hydrofabric_data_id='9876543210',
            hydrofabric_uid="0123456789",
            bmi_config_data_id='02468',
            partition_cfg_data_id='part1234',
            realization_config_data_id='02468',
            objective_function=obj_func,
            iterations=iterations,
            model_strategy=model_strategy,
            model_params={}
        )

        # Example 1 - example without explicit calibration params
        ex_idx = 1

        config_ds_id = "config_ds_1"
        self.calibration_config_ds[1] = config_ds_id
        self.time_ranges[ex_idx] = time_range
        self.config_strings[ex_idx] = (
                '{'
                '   "bmi_config_data_id": "02468", '
                '   "hydrofabric_data_id": "9876543210", '
                '   "hydrofabric_uid": "0123456789", '
                '   "ngen_cal_config_data_id":' + config_ds_id + ','
                '   "partition_config_data_id": "part1234", '
                '   "realization_config_data_id": "02468", '
                '   "time_range": ' + time_range.to_json() +
                '}'
        )
        self.config_jsons[ex_idx] = {
            'time_range': time_range.to_dict(),
            'hydrofabric_data_id': '9876543210',
            'hydrofabric_uid': '0123456789',
            'bmi_config_data_id': '02468',
            'realization_config_data_id': '02468',
            'partition_config_data_id': 'part1234',
            'ngen_cal_config_data_id': config_ds_id
        }
        self.config_objs[ex_idx] = NgenCalRequestEstimationConfig(
            time_range=time_range,
            hydrofabric_data_id='9876543210',
            hydrofabric_uid="0123456789",
            bmi_config_data_id='02468',
            partition_cfg_data_id='part1234',
            realization_config_data_id='02468',
            ngen_cal_config_data_id=config_ds_id
        )

        # Example 2 (JSON only) - like Example 0, but leaving out objective_function so that init should fail
        ex_idx = 2

        self.config_jsons[ex_idx] = {
            'time_range': time_range.to_dict(),
            'hydrofabric_data_id': '9876543210',
            'hydrofabric_uid': '0123456789',
            'bmi_config_data_id': '02468',
            'realization_config_data_id': '02468',
            'partition_config_data_id': 'part1234',
            #'objective_function': obj_func,
            'iterations': iterations,
            'model_strategy': model_strategy,
            'model_params': {}
        }

        # Example 3 (JSON only) - like Example 2, but leaving out iterations instead
        ex_idx = 3

        self.config_jsons[ex_idx] = {
            'time_range': time_range.to_dict(),
            'hydrofabric_data_id': '9876543210',
            'hydrofabric_uid': '0123456789',
            'bmi_config_data_id': '02468',
            'realization_config_data_id': '02468',
            'partition_config_data_id': 'part1234',
            'objective_function': obj_func,
            #'iterations': iterations,
            'model_strategy': model_strategy,
            'model_params': {}
        }

        # Example 4 (JSON only) - like Example 2, but leaving out model_strategy instead
        ex_idx = 4

        self.config_jsons[ex_idx] = {
            'time_range': time_range.to_dict(),
            'hydrofabric_data_id': '9876543210',
            'hydrofabric_uid': '0123456789',
            'bmi_config_data_id': '02468',
            'realization_config_data_id': '02468',
            'partition_config_data_id': 'part1234',
            'objective_function': obj_func,
            'iterations': iterations,
            #'model_strategy': model_strategy,
            'model_params': {}
        }

    def test_composite_config_source_ids_1_a(self):
        """
        Test that example 1 has the calibration dataset id included in the source ids.
        """
        ex_idx = 1

        config_obj = self.config_objs[ex_idx]
        expected_ds_id = self.calibration_config_ds[ex_idx]
        source_ids = config_obj.composite_config_source_ids

        self.assertTrue(expected_ds_id in source_ids)

    def test_composite_config_source_ids_1_b(self):
        """
        Test that example 1 looks like example 0, except for having the calibration config dataset id.
        """
        ex_idx = 1

        config_obj = self.config_objs[ex_idx]
        expected_ds_id = self.calibration_config_ds[ex_idx]
        source_ids = config_obj.composite_config_source_ids

        other_source_ids = self.config_objs[0].composite_config_source_ids
        other_source_ids.sort()

        source_ids.remove(expected_ds_id)
        source_ids.sort()

        self.assertEqual(source_ids, other_source_ids)

    def test_init_2_a(self):
        """
        Test that example 2 fails to init due to no ``objective_function`` param.
        """
        ex_idx = 2
        json_val = self.config_jsons[ex_idx]
        self.assertRaises(ValueError, NgenCalRequestEstimationConfig, **json_val)

    def test_init_3_a(self):
        """
        Test that example 2 fails to init due to no ``iterations`` param.
        """
        ex_idx = 3
        json_val = self.config_jsons[ex_idx]
        self.assertRaises(ValueError, NgenCalRequestEstimationConfig, **json_val)

    def test_init_4_a(self):
        """
        Test that example 2 fails to init due to no ``model_strategy`` param.
        """
        ex_idx = 4
        json_val = self.config_jsons[ex_idx]
        self.assertRaises(ValueError, NgenCalRequestEstimationConfig, **json_val)
