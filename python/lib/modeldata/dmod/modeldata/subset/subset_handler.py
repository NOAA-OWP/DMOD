from abc import ABC, abstractmethod
from hypy import Catchment, HydroLocation, Nexus
from queue import Queue
from typing import Collection, Dict, Optional, Set, Union
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

    @abstractmethod
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
        pass


class SubsetHandlerImpl(SubsetHandler):

    @classmethod
    def read_hydrofabric_files(cls, catchment_data, nexus_data, cross_walk):
        id_error_msg = 'Unexpected format of {} file {}, without \'id\' or \'ID\' column'

        catchment_hydro_fabric = gpd.read_file(catchment_data)
        catchment_hydro_fabric.columns = catchment_hydro_fabric.columns.astype(str).str.lower()
        if 'id' not in catchment_hydro_fabric.columns:
            raise RuntimeError(id_error_msg.format('catchment hydrofabric', catchment_data))
        catchment_hydro_fabric.set_index('id', inplace=True)

        nexus_hydro_fabric = gpd.read_file(nexus_data)
        nexus_hydro_fabric.columns = nexus_hydro_fabric.columns.astype(str).str.lower()
        if 'id' not in nexus_hydro_fabric.columns:
            raise RuntimeError(id_error_msg.format('nexus hydrofabric', catchment_data))
        nexus_hydro_fabric.set_index('id', inplace=True)

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
            hf[nex_id] = Nexus(nexus_id=nex_id, hydro_location=HydroLocation(realized_nexus=nex_id),
                               receiving_catchments=list(receiving), contributing_catchments=list(contributing))
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

    def is_catchment_recognized(self, catchment_id: str) -> bool:
        return catchment_id in self._hydrofabric_graph
