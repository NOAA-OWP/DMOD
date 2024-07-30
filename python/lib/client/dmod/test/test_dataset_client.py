import unittest
from ..client.request_clients import (DataCategory, DataDomain, DataServiceClient, DatasetManagementResponse,
                                      MaaSDatasetManagementResponse, ManagementAction, ResultIndicator)
from pathlib import Path
from typing import List, Optional, Sequence, Union


class SimpleMockDataServiceClient(DataServiceClient):
    """
    Mock subtype, primarily for testing base implementation of ::method:`extract_dataset_names`.
    """

    def __init__(self, *args, **kwargs):
        #super().__init__(*args, **kwargs)
        pass

    async def create_dataset(self, name: str, category: DataCategory, domain: DataDomain,
                             upload_paths: Optional[List[Path]] = None, data_root: Optional[Path] = None,
                             **kwargs) -> DatasetManagementResponse:
        """ Mock implementation, always returning an unsuccessful result. """
        return DatasetManagementResponse(success=False, action=ManagementAction.CREATE, reason="Mock")

    async def delete_dataset(self, name: str, **kwargs) -> DatasetManagementResponse:
        """ Mock implementation, always returning ``False``. """
        return DatasetManagementResponse(success=False, action=ManagementAction.DELETE, reason="Mock")

    async def retrieve_from_dataset(self, dataset_name: str, dest_dir: Path,
                                    item_names: Optional[Union[str, Sequence[str]]] = None, **kwargs) -> ResultIndicator:
        """ Mock implementation, always returning ``False``. """
        return DatasetManagementResponse(success=False, action=ManagementAction.REQUEST_DATA, reason="Mock")

    async def list_datasets(self, category: Optional[DataCategory] = None, **kwargs) -> List[str]:
        """ Mock implementation, always returning an empty list. """
        return []

    async def upload_to_dataset(self, dataset_name: str, paths: Union[Path, List[Path]],
                                data_root: Optional[Path] = None, **kwargs) -> ResultIndicator:
        """ Mock implementation, always returning ``False``. """
        return DatasetManagementResponse(success=False, action=ManagementAction.ADD_DATA, reason="Mock")


class TestDatasetClient(unittest.TestCase):

    def setUp(self) -> None:
        self.client = SimpleMockDataServiceClient()

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

    def test_extract_dataset_names_0_a(self):
        """ Test example 0 with base ::class:`DatasetManagementResponse` and empty list is parsed correctly """
        ex_indx = 0

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client.extract_dataset_names(response)
        self.assertEqual(expected_names, dataset_names)

    def test_extract_dataset_names_1_a(self):
        """ Test example 1 with base ::class:`DatasetManagementResponse` and non-empty list is parsed correctly """
        ex_indx = 1

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client.extract_dataset_names(response)
        self.assertEqual(expected_names, dataset_names)

    def test_extract_dataset_names_2_a(self):
        """ Test example 2 with subtype ::class:`MaaSDatasetManagementResponse` and empty list is parsed correctly """
        ex_indx = 2

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client.extract_dataset_names(response)
        self.assertEqual(expected_names, dataset_names)

    def test_extract_dataset_names_3_a(self):
        """ Test example 3 w/ subtype ::class:`MaaSDatasetManagementResponse` and non-empty list is parsed correctly """
        ex_indx = 3

        expected_names = self.example_dataset_names_lists[ex_indx]
        response = self.example_responses[ex_indx]

        dataset_names = self.client.extract_dataset_names(response)
        self.assertEqual(expected_names, dataset_names)
