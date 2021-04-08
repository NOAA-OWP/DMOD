import geopandas as gpd
import pandas as pd

from abc import ABC, abstractmethod
from hypy import Catchment, Nexus
from queue import Queue
from typing import Collection, Dict, Optional, Set, Union
from .subset_definition import SubsetDefinition


class SubsetHandler(ABC):

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
        goes. It uses the connections represented by ::attribute:`Catchment.inflow` and
        ::attribute:`Nexus.contributing_catchments`.

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


class SubsetHandlerImpl(SubsetHandler):

    @classmethod
    def read_hydrofabric_files(cls, catchment_data, nexus_data, cross_walk):
        id_error_msg = 'Unexpected format of {} file {}, without \'id\' or \'ID\' column'

        def get_present_id_col(column_names):
            if 'id' in column_names:
                return 'id'
            elif 'ID' in column_names:
                return 'ID'
            else:
                return None

        catchment_hydro_fabric = gpd.read_file(catchment_data)
        cat_id_col = get_present_id_col(catchment_hydro_fabric.columns)
        if cat_id_col is None:
            raise RuntimeError(id_error_msg.format('catchment hydrofabric', catchment_data))
        catchment_hydro_fabric.set_index(cat_id_col, inplace=True)

        nexus_hydro_fabric = gpd.read_file(nexus_data)
        nex_id_col = get_present_id_col(nexus_hydro_fabric)
        if nex_id_col is None:
            raise RuntimeError(id_error_msg.format('nexus hydrofabric', catchment_data))
        nexus_hydro_fabric.set_index(nex_id_col, inplace=True)

        x_walk = pd.read_json(cross_walk, dtype=str)
        return catchment_hydro_fabric, nexus_hydro_fabric, x_walk

    def __init__(self, catchment_data, nexus_data, cross_walk):
        self._catchment_geo_df, self._nexus_geo_df, self._x_walk_df = self.read_hydrofabric_files(catchment_data,
                                                                                                  nexus_data,
                                                                                                  cross_walk)
        super(SubsetHandlerImpl, self).__init__(hydrofabric_graph=self._generate_hydrofabric_graph())

    def _generate_hydrofabric_graph(self) -> Dict[str, Union[Catchment, Nexus]]:
        """
        Generate the hydrofabric graph and a dictionary of the elements by their ids.

        Generate a hydrofabric graph of associated ::class:`Catchment` and ::class:`Nexus` objects from the data
        provided in the parsed catchment and nexus geodataframes.  As part of the graph's construction, create a
        dictionary data structure, keyed by catchment/nexus id, of the individual graph nodes (i.e., each
        ::class:`Catchment` or ::class:`Nexus` object) for easy lookups.  Return this dictionary once generation is
        complete.

        Returns
        -------
        Dict[str, Union[Catchment, Nexus]]
            A dictionary of the nodes of the graph keyed by each's string id value.
        """
        # Keys of nexus id to lists of catchment ids for the catchments receiving water from this nexus
        nexus_receiving_cats = dict()
        # Keys of nexus id to lists of catchment ids for the catchments contributing water to this nexus
        nexus_contrib_cats = dict()
        known_catchment_ids = set()
        known_nexus_ids = set()
        cat_to = dict()
        cat_from = dict()

        for cat_id in self._catchment_geo_df.index:
            known_catchment_ids.add(cat_id)
            # TODO: do we need to account for more than one downstream?
            to_nex_id = self._catchment_geo_df.loc[cat_id]['toid'].strip()
            known_nexus_ids.add(to_nex_id)
            cat_to[cat_id] = to_nex_id
            if to_nex_id in nexus_contrib_cats:
                nexus_contrib_cats[to_nex_id].add(cat_id)
            else:
                nexus_contrib_cats[to_nex_id] = {cat_id}
            # TODO: do we need to account for contained/containing/conjoined?
        for nex_id in self._nexus_geo_df.index:
            known_nexus_ids.add(nex_id)
            to_cats = self._nexus_geo_df.loc[nex_id]['toid']
            # Handle the first one with conditional check separate, to optimize later ones
            first_cat_id = to_cats.split(',')[0].strip()
            if nex_id in nexus_receiving_cats and to_cats:
                nexus_receiving_cats[nex_id].add(first_cat_id)
            else:
                nexus_receiving_cats[nex_id] = {first_cat_id}
            known_catchment_ids.add(first_cat_id)
            cat_from[first_cat_id] = nex_id
            # Now add any remaining
            for cat_id in to_cats[1:]:
                clean_cat_id = cat_id.strip()
                nexus_receiving_cats[nex_id].add(clean_cat_id)
                known_catchment_ids.add(clean_cat_id)
                cat_from[cat_id] = nex_id

        hf = dict()
        # Create the catchments first, just without any upstream/downstream connections
        for cat_id in known_catchment_ids:
            # TODO: do params need to be something different?
            hf[cat_id] = Catchment(catchment_id=cat_id, params=dict())
        # Create the nexuses next, applying the right collections of catchments for contrib and receiv
        for nex_id in known_nexus_ids:
            contributing = set()
            for cid in nexus_contrib_cats[nex_id]:
                contributing.add(hf[cid])
            receiving = set()
            for cid in nexus_receiving_cats[nex_id]:
                receiving.add(hf[cid])
            # TODO: fix as hydro_location should probably not be None
            hf[nex_id] = Nexus(nexus_id=nex_id, hydro_location=None, receiving_catchments=list(receiving),
                               contributing_catchments=list(contributing))
        # Now go back and apply the right to/from relationships for catchments
        for cat_id, nex_id in cat_to.items():
            hf[cat_id]._outflow = hf[nex_id]
        for cat_id, nex_id in cat_from.items():
            hf[cat_id]._inflow = hf[nex_id]
        # TODO: again, do we need to worry about contained/containing/conjoined?
        # Finally ...
        return hf

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
        return self._hydrofabric_graph[catchment_id]