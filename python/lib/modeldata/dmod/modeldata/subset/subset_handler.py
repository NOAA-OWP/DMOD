from abc import ABC, abstractmethod
from hypy import Catchment, Nexus
from queue import Queue
from typing import Collection, Optional, Set, Tuple, Union
from .subset_definition import SubsetDefinition
from .hydrofabric import Hydrofabric, GeoJsonHydrofabricReader, MappedGraphHydrofabric


class SubsetValidator(ABC):
    """
    Abstraction for handling the process of validating subsets according to some implementation-specific rules.
    """

    def __init__(self, hydrofabric: Hydrofabric):
        """

        Parameters
        ----------
        hydrofabric : Hydrofabric
            The hydrofabric that will be used during validation.
        """
        self.hydrofabric: Hydrofabric = hydrofabric

    def is_valid(self, subset: SubsetDefinition) -> bool:
        """
        Return whether a given subset is valid.

        The default implementation simply returns whether ::method:`invalid_reason` returns ``None``.

        Parameters
        ----------
        subset : SubsetDefinition
            The subset in question.

        Returns
        -------
        bool
            Whether the given subset is valid.
        """
        return self.invalid_reason(subset) is None

    @abstractmethod
    def invalid_reason(self, subset: SubsetDefinition) -> Optional[str]:
        """
        Provide a string description of why the given subset is invalid.

        Note that, unless otherwise explicitly stated in the documentation for implementations, this method only returns
        a description of the first encountered characteristic that disqualifies the subset as valid.  In other words,
        there could be additional disqualifying traits.  As such, implementations should try to adhere to a
        deterministic order for checking things, and should document if they do not.

        Parameters
        ----------
        subset : SubsetDefinition
            The subset in question expected to be invalid.

        Returns
        -------
        Optional[str]
            A string description of the **first** discovered reason for the given subset not qualifying as valid, or
            ``None`` if it is a valid subset.
        """
        pass


class BasicSubsetValidator(SubsetValidator):
    """
    Simple implementation that checks existence and common-sense node relationships.

    In this type, validation requires:
        - all catchments and nexuses exist (i.e., for each id, there is a corresponding object in the hydrofabric)
        - every nexus must have at least one linked catchment included in the subset
        - every catchment must have at least one linked nexus included in the subset
            - an exception to this is the case of a subset with exactly 1 catchment and 0 nexuses
    """

    def invalid_reason(self, subset: SubsetDefinition) -> Optional[str]:
        """
        Provide a string description of why the given subset is invalid.

        Note that this method only returns a description of the first encountered characteristic that disqualifies the
        subset as valid.  In other words, there could be additional disqualifying traits.  The order of checks is
        deterministic, though this determinism is dependent upon the current implementation of SubsetDefinition, which
        deterministically represents a particular unique subset.

        In this type, validation requires:
        - all catchments and nexuses exist (i.e., for each id, there is a corresponding object in the hydrofabric)
        - every nexus must have at least one linked catchment included in the subset
        - every catchment must have at least one linked nexus included in the subset
            - an exception to this is the case of a subset with exactly 1 catchment and 0 nexuses

        Note that while the order of checks is deterministic, they are not necessarily applied in the above order.

        Parameters
        ----------
        subset : SubsetDefinition
            The subset in question expected to be invalid.

        Returns
        -------
        Optional[str]
            A string description of the **first** discovered reason for the given subset not qualifying as valid, or
            ``None`` if it is a valid subset.
        """
        # Handle the special, quick case of a single-catchment subset first
        if len(subset.catchment_ids) == 1 and len(subset.nexus_ids) == 0:
            cid = subset.catchment_ids[0]
            return None if self.hydrofabric.is_catchment_recognized(cid) else 'Unrecognized catchment: {}'.format(cid)

        for cid in subset.catchment_ids:
            catchment = self.hydrofabric.get_catchment_by_id(cid)
            if catchment is None:
                return 'Unrecognized catchment: {}'.format(cid)
            connected_nexus_found = False
            for n in [catchment.outflow, catchment.inflow]:
                if n.id in subset.nexus_ids:
                    connected_nexus_found = True
                    break
            if not connected_nexus_found:
                return 'Catchment {} has no connected nexus included in this subset'.format(cid)

        for nid in subset.nexus_ids:
            nexus = self.hydrofabric.get_nexus_by_id(nid)
            if nexus is None:
                return 'Unrecognized nexus: {}'.format(nid)
            connected_cat_found = False
            for c in [i for sub in [nexus.contributing_catchments, nexus.receiving_catchments] for i in sub]:
                if c.id in subset.catchment_ids:
                    connected_cat_found = True
                    break
            if not connected_cat_found:
                return 'Nexus {} has no connected catchment included in this subset'.format(nid)

        return None


class SubsetHandler:

    def __init__(self, hydrofabric: Hydrofabric, validator: Optional[SubsetValidator] = None):
        """

        Parameters
        ----------
        hydrofabric
            The hydrofabric of catchments and nexuses

        """
        self._hydrofabric = hydrofabric
        self._validator = validator if validator else BasicSubsetValidator(hydrofabric)

    @abstractmethod
    def get_catchment_by_id(self, catchment_id: str) -> Catchment:
        """
        Get the catchment object for the given id.

        Parameters
        ----------
        catchment_id : str
            The catchment id.

        Returns
        -------
        Catchment
            The appropriate catchment object from the hydrograph.
        """
        return self._hydrofabric.get_catchment_by_id(catchment_id)

    def get_subset_for(self, catchment_ids: Collection[str]) -> SubsetDefinition:
        """
        Get the subset for a particular collection of catchments and each's downstream nexus.

        Parameters
        ----------
        catchment_ids : Union[str, Collection[str]]
            The string ids of the desired catchments

        Returns
        -------

        """
        nex_ids: Set[str] = set()
        if isinstance(catchment_ids, str):
            catchment_ids = [catchment_ids]
        for cid in catchment_ids:
            catchment = self.get_catchment_by_id(cid)
            nex_ids.add(catchment.outflow.id)
        return SubsetDefinition(catchment_ids=catchment_ids, nexus_ids=nex_ids)

    def get_upstream_subset(self, catchment_ids: Union[str, Collection[str]],
                            link_limit: Optional[int] = None) -> SubsetDefinition:
        """
        Get the subset starting from a particular catchment and going upstream.

        Function traverses the graph of Catchments and Nexuses, building a subset of the encountered entities as it
        goes. It uses the connections represented by ::attribute:`Catchment.inflow` and
        ::attribute:`Nexus.contributing_catchments`.

        It is possible to restrict how many links away from the original catchment to proceed.  Each attribute
        traversal, whether ending up in a catchment or nexus, is considered an incremental link.  If ``None`` or a
        negative value is supplied, the graph is traversed completely across all recursive upstream relationships as
        described above.

        Parameters
        ----------
        catchment_ids: Union[str, Collection[str]]
            Collection of ids of one or more originating catchment from which to proceed upstream.

        link_limit: Optional[int]
            An optional restriction of how far from the originating catchment entities may be to be added to the subset.

        Returns
        -------
        SubsetDefinition
            The generated subset definition object.

        """
        if link_limit and link_limit < 0:
            link_limit = None
        if isinstance(catchment_ids, str):
            catchment_ids = [catchment_ids]
        cat_ids: Set[str] = set()
        nex_ids: Set[str] = set()
        # Nodes are a tuple of the catchment/nexus object, the link count to it, and bool indication if catchment
        # Third item should be faster than checking instance type repeatedly
        graph_nodes = Queue()
        for cid in catchment_ids:
            graph_nodes.put((self.get_catchment_by_id(cid), 0, True))

        while graph_nodes.qsize() > 0:
            item, link_dist, is_catchment = graph_nodes.get()
            if item is None:
                continue
            if is_catchment and item.id not in cat_ids:
                cat_ids.add(item.id)
                if link_limit is None or link_dist < link_limit:
                    new_dist = link_dist + 1
                    graph_nodes.put((item.inflow, new_dist, False))
            elif not is_catchment and item.id not in nex_ids:
                nex_ids.add(item.id)
                if link_limit is None or link_dist < link_limit:
                    new_dist = link_dist + 1
                    for c in item.contributing_catchments:
                        graph_nodes.put((c, new_dist, True))

        return SubsetDefinition(catchment_ids=cat_ids, nexus_ids=nex_ids)

    def is_catchment_recognized(self, catchment_id: str) -> bool:
        """
        Test whether a catchment is recognized in the current hydrograph.

        Parameters
        ----------
        catchment_id : str
            The id of the catchment.

        Returns
        -------
        bool
            Whether the catchment is recognized.
        """
        return self._hydrofabric.is_catchment_recognized(catchment_id)

    def validate(self, subset: SubsetDefinition) -> Tuple[bool, Optional[str]]:
        """
        Validate the subset and give feedback if invalid.

        Check whether the given subset is valid and, in the case when the subset is invalid, obtain at least a partial
        description of why it is invalid.  Return these as a tuple.

        Parameters
        ----------
        subset : SubsetDefinition
            The subset in question.

        Returns
        -------
        Tuple[bool, Optional[str]]
            Whether the subset is valid and, if not, a partial description of why not (or ``None`` if it is valid).
        """
        description = self._validator.invalid_reason(subset)
        return description is None, description

