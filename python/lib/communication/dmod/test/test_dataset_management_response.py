import unittest
from ..communication.dataset_management_message import DatasetManagementResponse, ManagementAction


class TestDatasetManagementResponse(unittest.TestCase):

    def setUp(self) -> None:
        self.example_json = []
        self.example_obj = []
        self.example_dataset_names_lists = []

        dataset_names_list = []
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_json.append(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}})
        self.example_obj.append(DatasetManagementResponse(success=True, reason="List Assembled",
                                                          datasets=dataset_names_list, action=ManagementAction.LIST_ALL,
                                                          is_awaiting=False))

        dataset_names_list = ['dataset_1', 'dataset_2']
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_json.append(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}})
        self.example_obj.append(DatasetManagementResponse(success=True, reason="List Assembled",
                                                          datasets=dataset_names_list, action=ManagementAction.LIST_ALL,
                                                          is_awaiting=False))

    def test_factory_init_from_deserialized_json_0_a(self):
        """
        Make sure the object for example 0 deserializes equivalently.
        """
        ex_idx = 0
        ex_json = self.example_json[ex_idx]
        expected = self.example_obj[ex_idx]
        actual = DatasetManagementResponse.factory_init_from_deserialized_json(ex_json)
        self.assertEqual(expected, actual)

    def test_factory_init_from_deserialized_json_0_b(self):
        """
        Make sure the object for example 0 deserializes correctly by checking the list of datasets for a ``LIST_ALL``.
        """
        ex_idx = 0
        ex_json = self.example_json[ex_idx]
        obj = DatasetManagementResponse.factory_init_from_deserialized_json(ex_json)
        actual_datasets = obj.data.datasets
        expected_dataset = self.example_dataset_names_lists[ex_idx]
        self.assertEqual(expected_dataset, actual_datasets)

    def test_factory_init_from_deserialized_json_1_a(self):
        """
        Make sure the object for example 1 deserializes equivalently.
        """
        ex_idx = 1
        ex_json = self.example_json[ex_idx]
        expected = self.example_obj[ex_idx]
        actual = DatasetManagementResponse.factory_init_from_deserialized_json(ex_json)
        self.assertEqual(expected, actual)

    def test_factory_init_from_deserialized_json_1_b(self):
        """
        Make sure the object for example 0 deserializes correctly by checking the list of datasets for a ``LIST_ALL``.
        """
        ex_idx = 0
        ex_json = self.example_json[ex_idx]
        obj = DatasetManagementResponse.factory_init_from_deserialized_json(ex_json)
        actual_datasets = obj.data.datasets
        expected_dataset = self.example_dataset_names_lists[ex_idx]
        self.assertEqual(expected_dataset, actual_datasets)