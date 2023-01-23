import unittest
from ..communication.dataset_management_message import DatasetQuery, QueryType


class TestDatasetQuery(unittest.TestCase):

    def setUp(self) -> None:
        self.ex_query_types = []
        self.ex_json_data = []
        self.examples = []

        self.ex_query_types.append(QueryType.LIST_FILES)
        self.ex_json_data.append({"query_type": 'LIST_FILES'})
        self.examples.append(DatasetQuery(query_type=QueryType.LIST_FILES))

    def test_factory_init_from_deserialized_json_0_a(self):
        """ Basic test of functionality. """
        ex_indx = 0
        expected_object = self.examples[ex_indx]
        data = self.ex_json_data[ex_indx]

        query_object = DatasetQuery.factory_init_from_deserialized_json(data)
        self.assertEqual(expected_object, query_object)

    def test_to_dict_0_a(self):
        """ Basic test of functionality. """
        ex_indx = 0
        query_object = self.examples[ex_indx]
        expected_data = self.ex_json_data[ex_indx]

        data_dict = query_object.to_dict()
        self.assertEqual(expected_data, data_dict)
