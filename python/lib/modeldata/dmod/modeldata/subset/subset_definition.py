from numbers import Number
from typing import Collection, Tuple, Dict, Union
from dmod.core.serializable import Serializable


class SubsetDefinition(Serializable):
    """
    Simple type to encapsulate the essential metadata parameters for defining a subset of catchments.

    Both equality and hash rely upon catchment ids and nexus ids, assuming the same elements in the same order.
    Conceptually, this also implies no duplicates can be allowed.  As such, initialization values first have any
    duplicates removed and then use sorted results to create the internal representations.  These are stored in tuples
    to be immutable.
    """

    __slots__ = ["_catchment_ids", "_nexus_ids"]

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return cls(**json_obj)
        except Exception as e:
            return None

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str]):
        self._catchment_ids = tuple(sorted(set(catchment_ids)))
        self._nexus_ids = tuple(sorted(set(nexus_ids)))

    def __eq__(self, other):
        return isinstance(other, SubsetDefinition) \
               and self.catchment_ids == other.catchment_ids \
               and self.nexus_ids == other.nexus_ids

    def __hash__(self):
        joined_cats = ','.join(self.catchment_ids)
        joined_nexs = ','.join(self.nexus_ids)
        joined_all = ','.join((joined_cats, joined_nexs))
        return hash(joined_all)

    @property
    def catchment_ids(self) -> Tuple[str]:
        return self._catchment_ids

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

    @property
    def nexus_ids(self) -> Tuple[str]:
        return self._nexus_ids

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        return {'catchment_ids': list(self.catchment_ids), 'nexus_ids': list(self.nexus_ids)}
