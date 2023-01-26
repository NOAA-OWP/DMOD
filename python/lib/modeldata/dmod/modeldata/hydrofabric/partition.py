from numbers import Number
from typing import Collection, Dict, FrozenSet, List, Tuple, Union
from pydantic import Field
from dmod.core.serializable import Serializable


class Partition(Serializable):
    """
    A NextGen-style partition of a partitioned hydrofabric.

    Note that, to be consistent with other tools, the serialized representation includes keys for nexus ids and remote
    upstream/downstream nexus collections.  However, this basic type only actually contains the included catchments as
    part of its own internal state.  What nexuses are actually involved must be determined by assessing the partition
    in the context of the related hydrofabric.
    """

    partition_id: int
    catchment_ids: FrozenSet[str]
    nexus_ids: FrozenSet[str]
    """
    Note that, at the time this is committed, partition ids should always be integers.  This is so they can easily
    correspond to MPI ranks.  However, because of how the expected
    """
    remote_upstream_nexus_ids: FrozenSet[str] = Field(default_factory=frozenset)
    remote_downstream_nexus_ids: FrozenSet[str] = Field(default_factory=frozenset)

    class Config:
        fields = {
            "catchment_ids": {"alias": "cat-ids"},
            "partition_id": {"alias": "id"},
            "nexus_ids": {"alias": "nex-ids"},
            "remote_up_nexuses": {"alias": "remote-up"},
            "remote_down_nexuses": {"alias": "remote-down"},
        }

    def __init__(self, partition_id: int, catchment_ids: Collection[str], nexus_ids: Collection[str],
                 remote_up_nexuses: Collection[str] = None, remote_down_nexuses: Collection[str] = None, **data):

        self._hash_val = None

        if remote_up_nexuses is None or remote_down_nexuses is None:
            super().__init__(
                partition_id=partition_id,
                catchment_ids=catchment_ids,
                nexus_ids=nexus_ids,
                **data
            )
            return

        super().__init__(
            partition_id=partition_id,
            catchment_ids=catchment_ids,
            nexus_ids=nexus_ids,
            remote_upstream_nexus_ids=remote_up_nexuses,
            remote_downstream_nexus_ids=remote_down_nexuses
        )


    def __eq__(self, other: object):
        if not isinstance(other, self.__class__) or other.partition_id != self.partition_id:
            return False
        else:
            return other.__hash__() == self.__hash__()

    def __lt__(self, other: "Partition"):
        # Go first by id, so this is clearly true
        if self.partition_id < other.partition_id:
            return True
        # Again, going by id first, having greater id is also clear
        elif self.partition_id > other.partition_id:
            return False
        # Also can't be (strictly) less-than AND equal-to
        elif self == other:
            return False
        # At this stage, ids must be equal, but instances are not
        # Here, go by a sorted string representation of catchment ids lists
        else:
            return ','.join(sorted(self.catchment_ids)) < ','.join(sorted(other.catchment_ids))

    def __hash__(self):
        if self._hash_val is None:
            cat_id_list = sorted(self.catchment_ids)
            cat_id_list.insert(0, str(self.partition_id))
            self._hash_val = hash(','.join(cat_id_list))
        return self._hash_val

class PartitionConfig(Serializable):
    """
    A type to easily encapsulate the JSON object that is output from the NextGen partitioner.
    """

    _KEY_PARTITIONS = 'partitions'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return PartitionConfig([Partition.factory_init_from_deserialized_json(serial_p) for serial_p in json_obj[cls._KEY_PARTITIONS]])
        except:
            return None

    @classmethod
    def get_serial_property_key_partitions(cls) -> str:
        return cls._KEY_PARTITIONS

    def __init__(self, partitions: Collection[Partition]):
        self._partitions = frozenset(partitions)

    def __eq__(self, other):
        if not isinstance(other, PartitionConfig):
            return False
        other_partitions_dict = dict()
        for other_p in other._partitions:
            other_partitions_dict[other_p.partition_id] = other_p

        other_pids = set([p2.partition_id for p2 in other.partitions])
        for pid in [p.partition_id for p in self.partitions]:
            if pid not in other_pids:
                return False
        return True

    def __hash__(self):
        """
        Get the unique hash for this instance.

        Method first creates a unique string of the joined hash values (themselves cast to strings) of the instance's
        partitions.  The property method

        Returns
        -------

        """
        #
        return hash(','.join([str(p.__hash__()) for p in sorted(self._partitions)]))

    @property
    def partitions(self) -> List[Partition]:
        """
        Get the (sorted) list of partitions for this config.

        Returns
        -------
        List[Partition]
            The (sorted) list of partitions for this config.
        """
        return sorted(self._partitions)

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        return {self._KEY_PARTITIONS: [p.to_dict() for p in self.partitions]}
