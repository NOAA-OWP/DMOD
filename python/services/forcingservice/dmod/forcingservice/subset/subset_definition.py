from typing import Collection, Tuple


class SubsetDefinition:
    """
    Simple type to encapsulate the essential metadata parameters for defining a subset of catchments.
    """

    __slots__ = ["_catchment_ids", "_catchment_ids_tuple", "_nexus_ids", "_nexus_ids_tuple"]

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str]):
        self._catchment_ids = set(catchment_ids)
        self._nexus_ids = set(nexus_ids)
        self._catchment_ids_tuple = tuple(self._catchment_ids)
        self._nexus_ids_tuple = tuple(self._nexus_ids)

    @property
    def catchment_ids(self) -> Tuple[str]:
        return self._catchment_ids_tuple

    @property
    def nexus_ids(self) -> Tuple[str]:
        return self._nexus_ids_tuple
