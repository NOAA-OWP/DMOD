from typing import Collection, FrozenSet, List, Optional, TYPE_CHECKING, Union
from pydantic import Field, PrivateAttr, validator
from dmod.core.serializable import Serializable

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny


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

    _hash_val: Optional[int] = PrivateAttr(None)

    class Config:
        fields = {
            "catchment_ids": {"alias": "cat-ids"},
            "partition_id": {"alias": "id"},
            "nexus_ids": {"alias": "nex-ids"},
            "remote_upstream_nexus_ids": {"alias": "remote-up"},
            "remote_downstream_nexus_ids": {"alias": "remote-down"},
        }

        def _serialize_frozenset(value: FrozenSet[str]) -> List[str]:
            return list(value)

        field_serializers = {
            "catchment_ids": _serialize_frozenset,
            "nexus_ids":  _serialize_frozenset,
            "remote_upstream_nexus_ids":  _serialize_frozenset,
            "remote_downstream_nexus_ids":  _serialize_frozenset,
        }

    def __init__(
            self,
            # required, but for backwards compatibility, None
            partition_id: int = None,
            catchment_ids: Collection[str] = None,
            nexus_ids: Collection[str] = None,
            # non-required fields
            remote_up_nexuses: Collection[str] = None,
            remote_down_nexuses: Collection[str] = None,
            **data
        ):
        # if data exists, assume fields specified using their alias; no backwards compatibility.
        if data:
            super().__init__(**data)
            return


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

    partitions: FrozenSet[Partition]

    @validator("partitions")
    def _sort_partitions(cls, value: FrozenSet[Partition]) -> FrozenSet[Partition]:
        return frozenset(sorted(value))

    class Config:
        def _serialize_frozenset(value: FrozenSet[Partition]) -> List[Partition]:
            return list(value)

        field_serializers = {
                "partitions": _serialize_frozenset
                }

    @classmethod
    def get_serial_property_key_partitions(cls) -> str:
        return "partitions"

    def __init__(self, partitions: Collection[Partition], **data):
        super().__init__(partitions=partitions, **data)

    def __eq__(self, other: object):
        if not isinstance(other, PartitionConfig):
            return False
        other_partitions_dict = dict()
        for other_p in other.partitions:
            other_partitions_dict[other_p.partition_id] = other_p

        other_pids = set([p2.partition_id for p2 in other.partitions])
        for pid in [p.partition_id for p in self.partitions]:
            if pid not in other_pids:
                return False
        return True

    def __hash__(self) -> int:
        """
        Get the unique hash for this instance.

        Method first creates a unique string of the joined hash values (themselves cast to strings) of the instance's
        partitions.  The property method

        Returns
        -------
        int
            Hash of instance
        """
        return hash(",".join([str(p.__hash__()) for p in sorted(self.partitions)]))

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> "DictStrAny":
        # reasons why dict is overridden here:
        # pydantic will serialize from inner types outward, serializing each type as a dictionary,
        # list, or primitive and replacing its previous type with the new "serialized" type.
        # Consequently, this means hashable container types like tuples and frozensets that contain
        # values that "serialize" to a non-hashable type (non-primitive, in this case) will raise a
        # `TypeError: unhashable type: 'dict'`. In the case of PartitionConfig,
        # FronzenSet[Partition] "serializes" inner Partition types as dictionaries which are not
        # hashable. To get around this, we will momentarily swap the `partitions` field for a
        # non-hashable container type, serialize using `.dict()`, and swap back in the original
        # `partitions` container.

        # 1. take a reference to partitions: FrozenSet[Partition]
        partitions = self.partitions

        # 2. cast and set partitions to a list, a non-hashable container type
        self.partitions = list(partitions)

        # 3. serialize
        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        # 4. replace partitions with its hashable representation
        self.partitions = partitions
        return serial
