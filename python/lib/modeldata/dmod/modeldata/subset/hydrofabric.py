import geopandas as gpd
import pandas as pd
from abc import ABC, abstractmethod
from hypy import Catchment, HydroLocation, Nexus
from typing import Any, Dict, Optional, Tuple, Union


class Hydrofabric(ABC):

    @abstractmethod
    def get_all_catchment_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained catchments.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained catchments.
        """
        pass

    @abstractmethod
    def get_all_nexus_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained nexuses.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained nexuses.
        """
        pass

    @abstractmethod
    def get_catchment_by_id(self, catchment_id: str) -> Optional[Catchment]:
        """
        Get the catchment object for the given id.

        Parameters
        ----------
        catchment_id : str
            The catchment id.

        Returns
        -------
        Optional[Catchment]
            The appropriate catchment object, or ``None`` if this hydrofabric does not contain a catchment with this id.
        """
        pass

    @abstractmethod
    def get_nexus_by_id(self, nexus_id: str) -> Optional[Nexus]:
        """
        Get the nexus object for the given id.

        Parameters
        ----------
        nexus_id : str
            The nexus id.

        Returns
        -------
        Optional[Nexus]
            The appropriate nexus object, or ``None`` if this hydrofabric does not contain a nexus with this id.
        """
        pass

    @abstractmethod
    def is_catchment_recognized(self, catchment_id: str) -> bool:
        """
        Test whether a catchment is recognized.

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

    @abstractmethod
    def is_nexus_recognized(self, nexus_id: str) -> bool:
        """
        Test whether a nexus is recognized.

        Parameters
        ----------
        nexus_id : str
            The id of the nexus.

        Returns
        -------
        bool
            Whether the nexus is recognized.
        """
        pass


class GeoJsonHydrofabricReader:
    """
    Util type for reading hydrofabric data from GeoJSON.
    """
    def __init__(self, catchment_data, nexus_data, cross_walk):
        id_error_msg = 'Unexpected format of {} file {}, without \'id\' or \'ID\' column'

        self.catchment_geodataframe = gpd.read_file(catchment_data)
        self.catchment_geodataframe.columns = self.catchment_geodataframe.columns.astype(str).str.lower()
        if 'id' not in self.catchment_geodataframe.columns:
            raise RuntimeError(id_error_msg.format('catchment hydrofabric', catchment_data))
        self.catchment_geodataframe.set_index('id', inplace=True)

        self.nexus_geodataframe = gpd.read_file(nexus_data)
        self.nexus_geodataframe.columns = self.nexus_geodataframe.columns.astype(str).str.lower()
        if 'id' not in self.nexus_geodataframe.columns:
            raise RuntimeError(id_error_msg.format('nexus hydrofabric', nexus_data))
        self.nexus_geodataframe.set_index('id', inplace=True)

        self.crosswalk_dataframe = pd.read_json(cross_walk, dtype=str)

        self._hydrofabric_graph = None

    @property
    def hydrofabric_graph(self) -> Dict[str, Union[Catchment, Nexus]]:
        """
        Lazily get the hydrofabric object graph as a dictionary of the elements by their ids.

        Using data in ::attribute:`catchment_geodataframe` and ::attribute:`nexus_geodataframe`, method generates (when
        necessary) a hydrofabric object graph of associated ::class:`Catchment` and ::class:`Nexus` objects, including
        all the inter-object relationships.  These are collected in dictionary data structure keyed by the ``id``
        property of each object.  Once that is created, the backing attribute is set to this dictionary for subsequent
        reuse, and the dictionary is returned.

        Returns
        -------
        Dict[str, Union[Catchment, Nexus]]
            A dictionary of the nodes of the graph keyed by each's string id value.
        """
        if self._hydrofabric_graph is None:
            # Keys of nexus id to lists of catchment ids for the catchments receiving water from this nexus
            nexus_receiving_cats = dict()
            # Keys of nexus id to lists of catchment ids for the catchments contributing water to this nexus
            nexus_contrib_cats = dict()
            known_catchment_ids = set()
            known_nexus_ids = set()
            cat_to = dict()
            cat_from = dict()

            for cat_id in self.catchment_geodataframe.index:
                known_catchment_ids.add(cat_id)
                # TODO: do we need to account for more than one downstream?
                to_nex_id = self.catchment_geodataframe.loc[cat_id]['toid'].strip()
                known_nexus_ids.add(to_nex_id)
                cat_to[cat_id] = to_nex_id
                if to_nex_id in nexus_contrib_cats:
                    nexus_contrib_cats[to_nex_id].add(cat_id)
                else:
                    nexus_contrib_cats[to_nex_id] = {cat_id}
                # TODO: do we need to account for contained/containing/conjoined?
            for nex_id in self.nexus_geodataframe.index:
                known_nexus_ids.add(nex_id)
                to_cats = self.nexus_geodataframe.loc[nex_id]['toid']
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
            self._hydrofabric_graph = hf
        return self._hydrofabric_graph


class MappedGraphHydrofabric(Hydrofabric):
    """
    Subtype of ::class:`Hydrofabric` created from an object graph stored as a dictionary.
    """

    def __init__(self, hydrofabric_object_graph: Dict[str, Union[Catchment, Nexus]],
                 graph_creator: Optional[Any] = None):
        """
        Initialize the instance.

        Parameters
        ----------
        hydrofabric_object_graph : Dict[str, Union[Catchment, Nexus]]
            The hydrofabric object graph, as a dictionary of inflated catchment and nexus objects keyed by ``id``.
        graph_creator : Optional[Any]
            An optional reference to a utility object that was used to construct the hydrofabric object graph.
        """
        self._hydrofabric_graph = hydrofabric_object_graph
        self._graph_creator = graph_creator
        self._catchment_ids = set()
        self._nexus_ids = set()
        for obj_id, obj in self._hydrofabric_graph.items():
            if isinstance(obj, Catchment):
                self._catchment_ids.add(obj_id)
            else:
                self._nexus_ids.add(obj_id)

    def get_all_catchment_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained catchments.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained catchments.
        """
        return tuple(sorted(self._catchment_ids))

    def get_all_nexus_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained nexuses.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained nexuses.
        """
        return tuple(sorted(self._nexus_ids))

    def get_catchment_by_id(self, catchment_id: str) -> Optional[Catchment]:
        """
        Get the catchment object for the given id.

        Parameters
        ----------
        catchment_id : str
            The catchment id.

        Returns
        -------
        Optional[Catchment]
            The appropriate catchment object, or ``None`` if this hydrofabric does not contain a catchment with this id.
        """
        return self._hydrofabric_graph[catchment_id] if catchment_id in self._hydrofabric_graph else None

    def get_nexus_by_id(self, nexus_id: str) -> Optional[Nexus]:
        """
        Get the nexus object for the given id.

        Parameters
        ----------
        nexus_id : str
            The nexus id.

        Returns
        -------
        Optional[Nexus]
            The appropriate nexus object, or ``None`` if this hydrofabric does not contain a nexus with this id.
        """
        return self._hydrofabric_graph[nexus_id] if nexus_id in self._hydrofabric_graph else None

    def is_catchment_recognized(self, catchment_id: str) -> bool:
        """
        Test whether a catchment is recognized.

        Parameters
        ----------
        catchment_id : str
            The id of the catchment.

        Returns
        -------
        bool
            Whether the catchment is recognized.
        """
        return catchment_id in self._hydrofabric_graph

    def is_nexus_recognized(self, nexus_id: str) -> bool:
        """
        Test whether a nexus is recognized.

        Parameters
        ----------
        nexus_id : str
            The id of the nexus.

        Returns
        -------
        bool
            Whether the nexus is recognized.
        """
        return nexus_id in self._hydrofabric_graph

