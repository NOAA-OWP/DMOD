from numbers import Number
from typing import Collection, Dict, FrozenSet, List, Union
from dmod.core.serializable import Serializable


class Partition(Serializable):
    """
    A NextGen-style partition of a partitioned hydrofabric.

    Note that, to be consistent with other tools, the serialized representation includes keys for nexus ids and remote
    upstream/downstream nexus collections.  However, this basic type only actually contains the included catchments as
    part of its own internal state.  What nexuses are actually involved must be determined by assessing the partition
    in the context of the related hydrofabric.
    """

    __slots__ = ["_catchment_ids", "_hash_val", "_nexus_ids", "_partition_id", "_remote_downstream_nexus_ids",
                 "_remote_upstream_nexus_ids"]

    _KEY_CATCHMENT_IDS = 'cat-ids'
    _KEY_PARTITION_ID = 'id'
    # Note that these need to be included in the JSON, but initially aren't actually used at the JSON level
    _KEY_NEXUS_IDS = 'nex-ids'
    _KEY_REMOTE_UPSTREAM_NEXUS_IDS = 'remote-up'
    _KEY_REMOTE_DOWNSTREAM_NEXUS_IDS = 'remote-down'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            # TODO: later these may be required, but for now, keep optional
            if cls._KEY_REMOTE_UPSTREAM_NEXUS_IDS in json_obj:
                remote_up = json_obj[cls._KEY_REMOTE_UPSTREAM_NEXUS_IDS]
            else:
                remote_up = []
            if cls._KEY_REMOTE_DOWNSTREAM_NEXUS_IDS in json_obj:
                remote_down = json_obj[cls._KEY_REMOTE_UPSTREAM_NEXUS_IDS]
            else:
                remote_down = []
            return Partition(catchment_ids=json_obj[cls._KEY_CATCHMENT_IDS], nexus_ids=json_obj[cls._KEY_NEXUS_IDS],
                             remote_up_nexuses=remote_up, remote_down_nexuses=remote_down,
                             partition_id=int(json_obj[cls._KEY_PARTITION_ID]))
        except:
            return None

    def __init__(self, partition_id: int, catchment_ids: Collection[str], nexus_ids: Collection[str],
                 remote_up_nexuses: Collection[str] = tuple(), remote_down_nexuses: Collection[str] = tuple()):
        self._partition_id = partition_id
        self._catchment_ids = frozenset(catchment_ids)
        self._nexus_ids = frozenset(nexus_ids)
        self._remote_upstream_nexus_ids = frozenset(remote_up_nexuses)
        self._remote_downstream_nexus_ids = frozenset(remote_down_nexuses)

        self._hash_val = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__) or other.partition_id != self.partition_id:
            return False
        else:
            return other.__hash__() == self.__hash__()

    def __lt__(self, other):
        # Go first by id, so this is clearly true
        if self._partition_id < other._partition_id:
            return True
        # Again, going by id first, having greater id is also clear
        elif self._partition_id > other._partition_id:
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

    @property
    def catchment_ids(self) -> FrozenSet[str]:
        """
        Get the frozen set of ids for all catchments in this partition.

        Returns
        -------
        Set[str]
            The frozen set of string ids for all catchments in this partition.
        """
        return self._catchment_ids

    @property
    def nexus_ids(self) -> FrozenSet[str]:
        """
        Get the frozen set of ids for all nexuses in this partition.

        Returns
        -------
        Set[str]
            The frozen set of string ids for all nexuses in this partition.
        """
        return self._nexus_ids

    @property
    def partition_id(self) -> int:
        """
        Get the id of this partition.

        Note that, at the time this is committed, partition ids should always be integers.  This is so they can easily
        correspond to MPI ranks.  However, because of how the expected

        Returns
        -------
        str
            The id of this partition, as a string.
        """
        return self._partition_id

    @property
    def remote_downstream_nexus_ids(self) -> FrozenSet[str]:
        """
        Get the frozen set of ids for all remote downstream nexuses in this partition.

        Returns
        -------
        Set[str]
            The frozen set of string ids for all remote downstream nexuses in this partition.
        """
        return self._remote_downstream_nexus_ids

    @property
    def remote_upstream_nexus_ids(self) -> FrozenSet[str]:
        """
        Get the frozen set of ids for all remote upstream nexuses in this partition.

        Returns
        -------
        Set[str]
            The frozen set of string ids for all remote upstream nexuses in this partition.
        """
        return self._remote_upstream_nexus_ids

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Get the instance represented as a dict (i.e., a JSON-like object).

        Note that, as described in the main docstring for the class, there are extra keys in the dict/JSON currently
        that don't correspond to any attributes of the instance.  This is for consistency with other tools.

        Returns
        -------
        dict
            The instance as a dict
        """
        return {
            self._KEY_PARTITION_ID: str(self.partition_id),
            self._KEY_CATCHMENT_IDS: list(self.catchment_ids),
            self._KEY_NEXUS_IDS: list(self.nexus_ids),
            self._KEY_REMOTE_UPSTREAM_NEXUS_IDS: list(self.remote_upstream_nexus_ids),
            self._KEY_REMOTE_DOWNSTREAM_NEXUS_IDS: list(self.remote_downstream_nexus_ids)
        }


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
