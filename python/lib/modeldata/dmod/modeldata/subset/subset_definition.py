from typing import Collection, Tuple
from pydantic import validator
from dmod.core.serializable import Serializable


class SubsetDefinition(Serializable):
    """
    Simple type to encapsulate the essential metadata parameters for defining a subset of catchments.

    Both equality and hash rely upon catchment ids and nexus ids, assuming the same elements in the same order.
    Conceptually, this also implies no duplicates can be allowed.  As such, initialization values first have any
    duplicates removed and then use sorted results to create the internal representations.  These are stored in tuples
    to be immutable.
    """

    catchment_ids: Tuple[str]
    nexus_ids: Tuple[str]

    @validator("catchment_ids", "nexus_ids")
    def _sort_and_dedupe_fields(cls, value: Tuple[str]) -> Tuple[str]:
        return tuple(sorted(set(value)))

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str], **data):
        super().__init__(catchment_ids=catchment_ids, nexus_ids=nexus_ids, **data)

    def __eq__(self, other: object):
        return (
            isinstance(other, SubsetDefinition)
            and self.catchment_ids == other.catchment_ids
            and self.nexus_ids == other.nexus_ids
        )

    def __hash__(self):
        joined_cats = ",".join(self.catchment_ids)
        joined_nexs = ",".join(self.nexus_ids)
        joined_all = ",".join((joined_cats, joined_nexs))
        return hash(joined_all)

    @property
    def id(self):
        """
        The unique id of this instance.

        The unique identifier for this instance, which in the base implementation is just the unique hash value.

        Returns
        -------
        The unique id of this instance.
        """
        return self.__hash__()
