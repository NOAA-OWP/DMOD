import unittest
from ..modeldata.hydrofabric.partition import Partition, PartitionConfig

class TestPartition(unittest.TestCase):

    @classmethod
    @property
    def partition_instance(cls) -> Partition:
        return Partition(
                nexus_ids=["2"],
                catchment_ids=["42"],
                partition_id=0,
                remote_up_nexuses=["1"],
                remote_down_nexuses=["3"]
                )

    @classmethod
    @property
    def serialized_partition(cls) -> dict:
        return {
                "cat-ids": ["42"],
                "id": 0,
                "remote-up": ["1"],
                "nex-ids": ["2"],
                "remote-down": ["3"]
                }


    def test_programmatically_create_partition(self):
        """Test creating an instance programmatically"""
        o = self.partition_instance

        self.assertEqual(len(o.catchment_ids), 1)
        self.assertEqual(len(o.remote_upstream_nexus_ids), 1)
        self.assertEqual(len(o.nexus_ids), 1)
        self.assertEqual(len(o.remote_downstream_nexus_ids), 1)

        self.assertIn
        self.assertEqual(o.partition_id, 0)
        self.assertIn("42", o.catchment_ids)
        self.assertIn("1", o.remote_upstream_nexus_ids)
        self.assertIn("2", o.nexus_ids)
        self.assertIn("3", o.remote_downstream_nexus_ids)

    def test_factory_init_from_deserialized_json(self):
        """
        Test creating an instance from a dictionary, then re-serializing equals the original dict.
        """
        data = self.serialized_partition
        o = Partition.factory_init_from_deserialized_json(data)
        self.assertIsNotNone(o)
        self.assertDictEqual(data, o.to_dict()) # type: ignore

    def test_eq(self):
        """
        Test equality of instances. Tests instances created programmatically and from dict
        deserialization.
        """
        o1 = self.partition_instance
        o2 = self.partition_instance

        o3 = Partition.factory_init_from_deserialized_json(self.serialized_partition)
        self.assertEqual(o1, o1)
        self.assertEqual(o1, o2)
        self.assertEqual(o1, o3)

    def test_hash(self):
        """
        Test instances hash to the same value based on their data, not the order of their data.
        """
        catchment_ids = ["1", "2", "3"]
        rev_catchment_ids = catchment_ids[::-1]

        o1 = Partition(
                # these fields are used by __hash__
                catchment_ids=catchment_ids,
                partition_id=0,

                nexus_ids=["2"],
                remote_up_nexuses=["1"],
                remote_down_nexuses=["3"]
                )

        o2 = Partition(
                # these fields are used by __hash__
                catchment_ids=rev_catchment_ids,
                partition_id=0,

                nexus_ids=["2"],
                remote_up_nexuses=["1"],
                remote_down_nexuses=["3"]
                )

        self.assertNotEqual(catchment_ids, rev_catchment_ids)
        self.assertEqual(hash(o1), hash(o2))
