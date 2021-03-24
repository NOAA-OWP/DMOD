from abc import ABC, abstractmethod
from hypy import Catchment
from queue import Queue
from typing import Collection, Optional, Set
from .subset_definition import SubsetDefinition


class SubsetService(ABC):

    def __init__(self, hydrofabric_graph):
        """

        Parameters
        ----------
        hydrofabric_graph
            The graph of catchments and nexuses

        """
        self._hydrofabric_graph = hydrofabric_graph

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
        pass

    def get_subset_for(self, catchment_ids: Collection[str]) -> SubsetDefinition:
        """
        Get the subset for a particular collection of catchments and each's downstream nexus.

        Parameters
        ----------
        catchment_ids : Collection[str]
            The string ids of the desired catchments

        Returns
        -------

        """
        nex_ids: Set[str] = set()
        for cid in catchment_ids:
            catchment = self.get_catchment_by_id(cid)
            nex_ids.add(catchment.outflow.id)
        return SubsetDefinition(catchment_ids=catchment_ids, nexus_ids=nex_ids)

    def get_upstream_subset(self, catchment_id: str, link_limit: Optional[int] = None) -> SubsetDefinition:
        """
        Get the subset starting from a particular catchment and going upstream.

        Function traverses the graph of Catchments and Nexuses, building a subset of the encountered entities as it
        goes. As one might expect, the traverses the connections represented by ::attribute:`Catchment.inflow` and
        ::attribute:`Nexus.contributing_catchments`.  Additionally, a containing catchment is also considered to be
        upstream, so ::attribute:`Catchement.containing_catchment` is traversed also if set.

        It is possible to restrict how many links away from the original catchment to proceed.  Each attribute
        traversal, whether ending up in a catchment or nexus, is considered an incremental link.  If ``None`` or a
        negative value is supplied, the graph is traversed completely across all recursive upstream relationships as
        described above.

        Parameters
        ----------
        catchment_id: str
            The id of an originating catchment from which to proceed upstream.

        link_limit: Optional[int]
            An optional restriction of how far from the originating catchment entities may be to be added to the subset.

        Returns
        -------
        SubsetDefinition
            The generated subset definition object.

        """
        if link_limit < 0:
            link_limit = None
        cat_ids: Set[str] = set()
        nex_ids: Set[str] = set()
        # Nodes are a tuple of the catchment/nexus object, the link count to it, and bool indication if catchment
        # Third item should be faster than checking instance type repeatedly
        graph_nodes = Queue()
        graph_nodes.put((self.get_catchment_by_id(catchment_id), 0, True))

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
