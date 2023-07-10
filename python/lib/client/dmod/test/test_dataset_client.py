import unittest
from ..client.request_clients import DataCategory, DatasetClient, DatasetManagementResponse, MaaSDatasetManagementResponse
from ..client._reader import AsyncReader
from pathlib import Path
from typing import List, Optional


class SimpleMockDatasetClient(DatasetClient):
    """
    Mock subtype, primarily for testing base implementation of ::method:`_parse_list_of_dataset_names_from_response`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def create_dataset(self, name: str, category: DataCategory) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False

    async def delete_dataset(self, name: str, **kwargs) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False

    async def download_dataset(self, dataset_name: str, dest_dir: Path) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False

    async def download_from_dataset(self, dataset_name: str, item_name: str, dest: Path) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False

    async def list_datasets(self, category: Optional[DataCategory] = None) -> List[str]:
        """ Mock implementation, always returning an empty list. """
        return []

    async def upload_to_dataset(self, dataset_name: str, paths: List[Path]) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False

    async def upload_data_to_dataset(self, dataset_name: str, item_name: str, data: AsyncReader) -> bool:
        """ Mock implementation, always returning ``False``. """
        return False


class TestDatasetClient(unittest.TestCase):

    def setUp(self) -> None:
        self.client = SimpleMockDatasetClient()

        self.example_responses = []
        self.example_dataset_names_lists = []

        dataset_names_list = []
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_responses.append(DatasetManagementResponse.factory_init_from_deserialized_json(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}}))

        dataset_names_list = ['dataset_1', 'dataset_2']
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_responses.append(DatasetManagementResponse.factory_init_from_deserialized_json(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}}))

        dataset_names_list = []
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_responses.append(MaaSDatasetManagementResponse.factory_init_from_deserialized_json(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}}))

        dataset_names_list = ['dataset_1', 'dataset_2', 'dataset_3']
        self.example_dataset_names_lists.append(dataset_names_list)
        self.example_responses.append(MaaSDatasetManagementResponse.factory_init_from_deserialized_json(
            {'success': True, 'reason': 'List Assembled', 'message': '',
             'data': {'datasets': list(dataset_names_list), 'action': 'LIST_ALL', 'is_awaiting': False}}))

    def test__parse_list_of_dataset_names_from_response_0_a(self):
        """ Test example 0 with base ::class:`DatasetManagementResponse` and empty list is parsed correctly """
        ex_indx = 0

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client._parse_list_of_dataset_names_from_response(response)
        self.assertEqual(expected_names, dataset_names)

    def test__parse_list_of_dataset_names_from_response_1_a(self):
        """ Test example 1 with base ::class:`DatasetManagementResponse` and non-empty list is parsed correctly """
        ex_indx = 1

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client._parse_list_of_dataset_names_from_response(response)
        self.assertEqual(expected_names, dataset_names)

    def test__parse_list_of_dataset_names_from_response_2_a(self):
        """ Test example 2 with subtype ::class:`MaaSDatasetManagementResponse` and empty list is parsed correctly """
        ex_indx = 2

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client._parse_list_of_dataset_names_from_response(response)
        self.assertEqual(expected_names, dataset_names)

    def test__parse_list_of_dataset_names_from_response_3_a(self):
        """ Test example 3 w/ subtype ::class:`MaaSDatasetManagementResponse` and non-empty list is parsed correctly """
        ex_indx = 3

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client._parse_list_of_dataset_names_from_response(response)
        self.assertEqual(expected_names, dataset_names)
