import unittest
import json
from ..modeldata.subset import SubsetDefinition


class TestSubsetDefinition(unittest.TestCase):

    def setUp(self) -> None:
        self.example_subset_objects = dict()
        self.ex_json = dict()
        self.ex_cat_id_lists = dict()
        self.ex_nex_id_lists = dict()

        self.ex_cat_id_lists[1] = ['cat-1', 'cat-2', 'cat-3']
        self.ex_nex_id_lists[1] = ['nex-1', 'nex-2', 'nex-3']
        self.example_subset_objects[1] = SubsetDefinition(self.ex_cat_id_lists[1], self.ex_nex_id_lists[1])
        self.ex_json[1] = '{"catchment_ids": ["cat-1", "cat-2", "cat-3"], "nexus_ids": ["nex-1", "nex-2", "nex-3"]}'

        self.ex_cat_id_lists[2] = ['cat-1', 'cat-3', 'cat-2', 'cat-3']
        self.ex_nex_id_lists[2] = ['nex-1', 'nex-2', 'nex-3']
        self.example_subset_objects[2] = SubsetDefinition(self.ex_cat_id_lists[2], self.ex_nex_id_lists[2])
        self.ex_json[2] = '{"catchment_ids": ["cat-1", "cat-2", "cat-3"], "nexus_ids": ["nex-1", "nex-2", "nex-3"]}'

    def tearDown(self) -> None:
        pass

    # Simple test of catchment_ids property
    def test_catchment_ids_1_a(self):
        ex = 1
        subset = self.example_subset_objects[ex]
        self.assertEqual(subset.catchment_ids, tuple(sorted(set(self.ex_cat_id_lists[ex]))))

    # Test that expected items are equal, even if the init params are not the same objects
    def test_equals_1_a(self):
        self.assertEqual(self.example_subset_objects[1], self.example_subset_objects[2])

    def test_factory_init_from_deserialized_json_1_a(self):
        ex = 1
        json_val = json.loads(self.ex_json[ex])
        self.assertEqual(SubsetDefinition.factory_init_from_deserialized_json(json_val), self.example_subset_objects[ex])

    # Simple test of nexus property
    def test_nexus_ids_1_a(self):
        ex = 1
        subset = self.example_subset_objects[ex]
        self.assertEqual(subset.nexus_ids, tuple(sorted(set(self.ex_nex_id_lists[ex]))))

    def test_to_json(self):
        ex = 1
        self.assertEqual(self.example_subset_objects[ex].to_json(), self.ex_json[ex])
