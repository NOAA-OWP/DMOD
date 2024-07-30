import datetime
import unittest
from ..scheduler.resources.resource_allocation import ResourceAllocation


class TestResourceAllocation(unittest.TestCase):

    # TODO: need more tests

    def setUp(self) -> None:
        self.examples = [
            ResourceAllocation(resource_id='id_01', hostname='host_01', cpus_allocated=4, requested_memory=5000),
            ResourceAllocation(resource_id='id_01', hostname='host_01', cpus_allocated=4, requested_memory=5000)
        ]
        self.examples[1].unique_id_separator = '|'

    def tearDown(self) -> None:
        pass

    # Test that a serialized representation gets factory deserialized to an object with the right resource id
    def test_factory_init_from_dict_1_a(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.resource_id, example_allocation.resource_id)

    # Test that a serialized representation gets factory deserialized to an object with the right hostname
    def test_factory_init_from_dict_1_b(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.hostname, example_allocation.hostname)

    # Test that a serialized representation gets factory deserialized to an object with the right CPU count
    def test_factory_init_from_dict_1_c(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.cpu_count, example_allocation.cpu_count)

    # Test that a serialized representation gets factory deserialized to an object with the right memory
    def test_factory_init_from_dict_1_d(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.memory, example_allocation.memory)

    # Test that a serialized representation gets factory deserialized to an object with the right pool id
    def test_factory_init_from_dict_1_e(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.pool_id, example_allocation.pool_id)

    # Test that a serialized representation gets factory deserialized to an object with the right unique id
    def test_factory_init_from_dict_1_f(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.unique_id, example_allocation.unique_id)

    # Test that a serialized representation gets factory deserialized to an object with the right unique id separator
    def test_factory_init_from_dict_1_g(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.unique_id_separator, example_allocation.unique_id_separator)

    # Test that a serialized representation gets factory deserialized to an object with the right created
    def test_factory_init_from_dict_1_h(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.created, example_allocation.created)

    # Test that a serialized representation of an object gets factory deserialized to an equivalent object
    def test_factory_init_from_dict_1_i(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized, example_allocation)

    # Test that a serialized representation gets factory deserialized to an object with the right unique id separator
    def test_factory_init_from_dict_2_g(self):
        example_index = 1
        example_allocation = self.examples[example_index]

        serialized = example_allocation.to_dict()
        deserialized = example_allocation.factory_init_from_dict(serialized)
        self.assertEqual(deserialized.unique_id_separator, example_allocation.unique_id_separator)

    # Test that to_dict produces a dictionary
    def test_to_dict_1_a(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertTrue(isinstance(result, dict))

    # Test that to_dict produces a dictionary with correct resource_id
    def test_to_dict_1_b(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertEqual(result['node_id'], example_allocation.resource_id)

    # Test that to_dict produces a dictionary with correct hostname
    def test_to_dict_1_c(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertEqual(result['Hostname'], example_allocation.hostname)

    # Test that to_dict produces a dictionary with correct CPU allocation
    def test_to_dict_1_d(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertEqual(result['cpus_allocated'], example_allocation.cpu_count)

    # Test that to_dict produces a dictionary with correct memory allocation
    def test_to_dict_1_e(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertEqual(result['mem'], example_allocation.memory)

    # Test that to_dict produces a dictionary with correct created value
    def test_to_dict_1_f(self):
        example_index = 0
        example_allocation = self.examples[example_index]

        result = example_allocation.to_dict()
        self.assertEqual(datetime.datetime.fromtimestamp(result['Created']), example_allocation.created)
