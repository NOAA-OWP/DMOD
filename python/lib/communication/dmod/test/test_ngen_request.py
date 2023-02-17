import json
import unittest
from ..communication.maas_request import NGENRequest, NGENRequestResponse
from ..test.test_ngen_request_response import TestNGENRequestResponse
from dmod.core.meta_data import DataFormat, TimeRange


class TestNGENRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.request_strings = []
        self.request_jsons = []
        self.request_objs = []

        self.tested_serializeable_type = NGENRequest

        # TODO: improve coverage through more examples
        
        self.time_ranges = []

        def create_time_range(begin, end, var=None) -> TimeRange:
            serialized = {'begin': begin, 'end': end, 'datetime_pattern': '%Y-%m-%d %H:%M:%S',
                          'subclass': TimeRange.__name__, 'variable': 'Time' if var is None else var}
            return TimeRange.factory_init_from_deserialized_json(serialized)

        # Example 0
        time_range = create_time_range('2022-01-01 00:00:00', '2022-03-01 00:00:00')
        cpu_count_ex_0 = 4
        self.time_ranges.append(time_range)
        self.request_strings.append(
            '{"model": '
                '{"allocation_paradigm": "SINGLE_NODE", "bmi_config_data_id": "02468", "config_data_id": "02468", "cpu_count": ' + str(cpu_count_ex_0) + ', '
                '"hydrofabric_data_id": "9876543210", "hydrofabric_uid": "0123456789", "name": "ngen", "time_range": '
                + time_range.to_json() + '}, '
            '"session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({
            'model': {
                'name': 'ngen',
                'allocation_paradigm': 'SINGLE_NODE',
                'cpu_count': cpu_count_ex_0,
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'config_data_id': '02468'
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        self.request_objs.append(
            NGENRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                        cpu_count=cpu_count_ex_0,
                        allocation_paradigm='SINGLE_NODE',
                        time_range=time_range,
                        hydrofabric_uid="0123456789",
                        hydrofabric_data_id='9876543210',
                        bmi_cfg_data_id='02468',
                        config_data_id='02468'))

        # Example 1 - like example 0, but with the object initialized with specific catchment subset
        time_range = create_time_range('2022-01-01 00:00:00', '2022-04-01 00:00:00')
        cpu_count_ex_1 = 2
        cat_ids_list = ['cat-1', 'cat-2', 'cat-3']
        cat_ids_str = '["{}", "{}", "{}"]'.format(*cat_ids_list)
        #cat_ids_list = ['cat-1', 'cat-2', 'cat-3']
        #cat_ids_list = []
        self.time_ranges.append(time_range)
        self.request_strings.append(
            '{"model": '
                '{"allocation_paradigm": "ROUND_ROBIN", "bmi_config_data_id": "02468", "catchments": ' + cat_ids_str + ', "config_data_id": "02468", '
                '"cpu_count": ' + str(cpu_count_ex_1) + ', "hydrofabric_data_id": "9876543210", '
                '"hydrofabric_uid": "0123456789", "name": "ngen", "time_range": ' + time_range.to_json() + '}, '
            '"session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}')
        self.request_jsons.append({
            'model': {
                'name': 'ngen',
                'allocation_paradigm': 'ROUND_ROBIN',
                'cpu_count': cpu_count_ex_1,
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'config_data_id': '02468',
                'bmi_config_data_id': '02468',
                'catchments': cat_ids_list
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        self.request_objs.append(
            NGENRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                        cpu_count=cpu_count_ex_1,
                        allocation_paradigm='ROUND_ROBIN',
                        time_range=time_range,
                        hydrofabric_uid="0123456789",
                        hydrofabric_data_id='9876543210',
                        config_data_id='02468',
                        bmi_cfg_data_id='02468',
                        catchments=cat_ids_list))

        # Example 2 - like example 0, but with a CPU count of 1 (which should not require partitioning)
        time_range = create_time_range('2022-01-01 00:00:00', '2022-03-01 00:00:00')
        cpu_count_ex_2 = 1
        self.time_ranges.append(time_range)
        self.request_strings.append(
            '{"model": {"allocation_paradigm": "SINGLE_NODE", "bmi_config_data_id": "02468", "config_data_id": "02468", '
            '"cpu_count": ' + str(cpu_count_ex_2) + ', "hydrofabric_data_id": "9876543210", '
            '"hydrofabric_uid": "0123456789", "name": "ngen", "time_range": ' + time_range.to_json() + '}, '
            '"session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}'
        )
        self.request_jsons.append({
            'model': {
                'name': 'ngen',
                'allocation_paradigm': 'SINGLE_NODE',
                'cpu_count': cpu_count_ex_2,
                'time_range': time_range.to_dict(),
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'bmi_config_data_id': '02468',
                'config_data_id': '02468'
            },
            'session-secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        self.request_objs.append(
            NGENRequest(session_secret='f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c',
                        cpu_count=cpu_count_ex_2,
                        allocation_paradigm='SINGLE_NODE',
                        time_range=time_range,
                        hydrofabric_uid="0123456789",
                        hydrofabric_data_id='9876543210',
                        bmi_cfg_data_id='02468',
                        config_data_id='02468'))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Assert that :meth:`NGENRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 0th index.
        """
        example_index = 0
        obj = NGENRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(self.request_objs[example_index], obj)

    def test_factory_init_from_deserialized_json_0_b(self):
        """
        Assert that :meth:`NGENRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 0th index.
        """
        example_index = 0
        obj = NGENRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Assert that :meth:`NGENRequest.factory_init_from_deserialized_json` produces an equal object to the
        pre-created object for the examples at the 1th index.
        """
        example_index = 1
        obj = NGENRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj, self.request_objs[example_index])

    def test_factory_init_from_deserialized_json_1_b(self):
        """
        Assert that :meth:`NGENRequest.factory_init_from_deserialized_json` produces an object having the appropriate
        session secret value for the examples at the 1th index.
        """
        example_index = 1
        obj = NGENRequest.factory_init_from_deserialized_json(self.request_jsons[example_index])
        self.assertEqual(obj.session_secret, self.request_objs[example_index].session_secret)

    # TODO: more tests for this
    def test_factory_init_correct_response_subtype_1_a(self):
        """
        Test ``factory_init_correct_response_subtype()`` that a valid response object is deserialized from the relevant
        example case string.
        """
        example_str = TestNGENRequestResponse.get_raw_response_string_example_1()
        json_obj = json.loads(example_str)
        obj = NGENRequest.factory_init_correct_response_subtype(json_obj)
        self.assertEqual(obj.__class__, NGENRequestResponse)

    def test_data_requirements_0_a(self):
        example_index = 0
        obj = self.request_objs[example_index]
        self.assertIsNotNone(obj.partition_cfg_data_requirement)

    def test_data_requirements_0_b(self):
        example_index = 0
        obj = self.request_objs[example_index]
        partition_reqs = [r for r in obj.data_requirements if r.domain.data_format == DataFormat.NGEN_PARTITION_CONFIG]
        self.assertEqual(len(partition_reqs), 1)

    def test_data_requirements_2_a(self):
        example_index = 2
        obj = self.request_objs[example_index]
        self.assertIsNone(obj.partition_cfg_data_requirement)

    def test_data_requirements_2_b(self):
        example_index = 2
        obj = self.request_objs[example_index]
        partition_reqs = [r for r in obj.data_requirements if r.domain.data_format == DataFormat.NGEN_PARTITION_CONFIG]
        self.assertEqual(len(partition_reqs), 0)

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
