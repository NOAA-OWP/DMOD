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
            remote_down_nexuses=["3"],
        )

    @classmethod
    @property
    def serialized_partition(cls) -> dict:
        return {
            "cat-ids": ["42"],
            "id": 0,
            "remote-up": ["1"],
            "nex-ids": ["2"],
            "remote-down": ["3"],
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
        self.assertDictEqual(data, o.to_dict())  # type: ignore

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
            remote_down_nexuses=["3"],
        )

        o2 = Partition(
            # these fields are used by __hash__
            catchment_ids=rev_catchment_ids,
            partition_id=0,
            nexus_ids=["2"],
            remote_up_nexuses=["1"],
            remote_down_nexuses=["3"],
        )

        self.assertNotEqual(catchment_ids, rev_catchment_ids)
        self.assertEqual(hash(o1), hash(o2))

    def test_to_dict(self):
        """Test serializing to dict"""
        o = Partition.factory_init_from_deserialized_json(self.serialized_partition)

        self.assertIsNotNone(o)
        self.assertDictEqual(o.to_dict(), self.serialized_partition)  # type: ignore


class TestPartitionConfig(unittest.TestCase):
    @classmethod
    @property
    def partition_config_instance(cls) -> PartitionConfig:
        return PartitionConfig(partitions=[TestPartition.partition_instance])

    @classmethod
    @property
    def serialized_partition_config(cls) -> dict:
        return {"partitions": [TestPartition.serialized_partition]}

    def test_programmatically_create_partition(self):
        """Test creating an instance programmatically"""
        o = self.partition_config_instance

        self.assertEqual(len(o.partitions), 1)

    def test_factory_init_from_deserialized_json(self):
        """Test creating an instance programmatically"""
        data = self.serialized_partition_config
        o = PartitionConfig.factory_init_from_deserialized_json(data)

        self.assertIsNotNone(o)
        self.assertDictEqual(data, o.to_dict())  # type: ignore

    def test_to_dict(self):
        o = PartitionConfig.factory_init_from_deserialized_json(
            self.serialized_partition_config
        )
        self.assertIsNotNone(o)
        self.assertDictEqual(self.serialized_partition_config, o.to_dict())  # type: ignore

    def test_hash(self):
        """
        Test instances hash to the same value based on their data, not the order of their data.
        """
        self.assertEqual(
            hash(self.partition_config_instance), hash(self.partition_config_instance)
        )

        # from dictionary
        o = PartitionConfig.factory_init_from_deserialized_json(
            self.partition_config_instance.to_dict()
        )
        self.assertEqual(hash(self.partition_config_instance), hash(o))

        catchment_ids = ["1", "2", "3"]

        o1 = PartitionConfig(
            partitions=[
                Partition(
                    nexus_ids=["1"],
                    remote_up_nexuses=["2"],
                    remote_down_nexuses=["3"],
                    partition_id=0,
                    catchment_ids=catchment_ids,
                )
            ]
        )

        o2 = PartitionConfig(
            partitions=[
                Partition(
                    nexus_ids=["2222"],
                    remote_up_nexuses=["1111"],
                    remote_down_nexuses=["3333"],
                    partition_id=0,
                    catchment_ids=catchment_ids,
                )
            ]
        )

        # same partition and catchment ids
        # NOTE: this is the expected behavior
        self.assertEqual(hash(o1), hash(o2))

    def test_duplicate_partitions_removed_during_init(self):
        catchment_ids = ["1", "2", "3"]
        rev_catchment_ids = catchment_ids[::-1]

        o1 = Partition(
            nexus_ids=["2"],
            remote_up_nexuses=["1"],
            remote_down_nexuses=["3"],
            partition_id=0,
            catchment_ids=catchment_ids,
        )

        o2 = Partition(
            nexus_ids=["2"],
            remote_up_nexuses=["1"],
            remote_down_nexuses=["3"],
            partition_id=0,
            catchment_ids=rev_catchment_ids,
        )

        duplicate_partition_inst = PartitionConfig(partitions=[o1, o1])
        self.assertEqual(len(duplicate_partition_inst.partitions), 1)

        duplicate_partition_same_data_inst = PartitionConfig(partitions=[o1, o2])
        self.assertEqual(len(duplicate_partition_same_data_inst.partitions), 1)
        catchment_ids = ["1", "2", "3"]

        o1 = Partition(
            nexus_ids=["2"],
            remote_up_nexuses=["1"],
            remote_down_nexuses=["3"],
            partition_id=0,
            catchment_ids=catchment_ids,
        )

        o3 = Partition(
            nexus_ids=["2222"],
            remote_up_nexuses=["1111"],
            remote_down_nexuses=["3333"],
            partition_id=0,
            catchment_ids=catchment_ids,
        )

        same_catchment_id_and_partition_id = PartitionConfig(partitions=[o1, o3])

        # NOTE: this is the expected behavior
        self.assertEqual(len(same_catchment_id_and_partition_id.partitions), 1)

