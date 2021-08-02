import geopandas as gpd
import pandas as pd
from abc import ABC, abstractmethod
from collections import defaultdict
from hypy import Catchment, HydroLocation, Nexus
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union
from ..subset import SubsetDefinition


class Hydrofabric(ABC):

    @classmethod
    def connect_features(cls, catchment: Catchment, nexus: Nexus, is_catchment_upstream: bool):
        """
        Make the connections on both sides between this catchment and nexus.

        Set the connections for this catchment and nexus pair.  How the upstream/downstream relationship exists is
        indicated by another parameter.  E.g., if ``is_catchment_upstream`` is ``True``, then the catchment's
        ::attribute:`Catchment.outflow` property is set to this nexus, and the catchment is added to the nexus's
        ::attribute:`Nexus.contributing_catchments` tuple (or the tuple is created with the catchment placed in it).

        Other properties, in particular those on the other "side" of each entity from where the two are connected, are
        not altered.

        Note that, for ::class:`Nexus` properties, duplication is avoided, but otherwise the catchment will be added to
        a collection property (potentially with the collection object being created).  However, for ::class`Catchment`
        properties, which are each an individual reference, the reference will be always be set.  No check is performed
        as to whether the property currently references ``None``.

        Parameters
        ----------
        catchment : Catchment
            The upstream/downstream catchment in the connected pair.
        nexus : Nexus
            The upstream/downstream (with this being opposite the state of ``catchment``) nexus in the connected pair.
        is_catchment_upstream : bool
            Whether ``catchment`` is connected upstream of ``nexus``.
        """
        if is_catchment_upstream:
            # Add catchment to nexus's collection of contributing, accounting for it being in there or the collection
            # needing to be created
            if nexus.contributing_catchments is None:
                nexus._contributing_catchments = (catchment,)
            elif catchment.id not in [cat.id for cat in nexus.contributing_catchments]:
                nexus._contributing_catchments = nexus.contributing_catchments + (catchment,)
            # Add nexus as catchment's outflow
            catchment._outflow = nexus
        else:
            # Add catchment to nexus's collection of receiving, accounting for it being in there or the collection
            # needing to be created
            if nexus.receiving_catchments is None:
                nexus._receiving_catchments = (catchment,)
            elif catchment.id not in [cat.id for cat in nexus.receiving_catchments]:
                nexus._receiving_catchments = nexus.receiving_catchments + (catchment,)
            # Add nexus as catchment's inflow
            catchment._inflow = nexus

    @classmethod
    def get_ids_of_connected(cls, feature: Union[Catchment, Nexus], upstream: bool, downstream: bool) -> Set[str]:
        """
        Get the ids of the features connected to the given feature.

        Gets the ids of features connected a given "base" feature, with connected features being nexuses if the base is
        a catchment, or catchments if the base is a nexus.  Whether upstream and/or downstream connected features are
        included is controlled by the other parameters.

        Parameters
        ----------
        feature : Union[Catchment, Nexus]
            The base catchment or nexus.
        upstream : bool
            Whether the base's upstream feature(s) should have their ids included.
        downstream : bool
            Whether the base's downstream feature(s) should have their ids included.

        Returns
        -------
        Set[str]
            The set of ids of the upstream and/or downstream features directly connected to the given base feature.
        """
        output = set()
        if isinstance(feature, Catchment):
            if upstream and feature.inflow is not None:
                output.add(feature.inflow.id)
            if downstream and feature.outflow is not None:
                output.add(feature.outflow.id)
        else:
            # Assumed to be Nexus
            if upstream and feature.contributing_catchments is not None:
                output.update([cat.id for cat in feature.contributing_catchments])
            if downstream and feature.receiving_catchments is not None:
                output.update([cat.id for cat in feature.receiving_catchments])
        return output

    def __eq__(self, other):
        """
        Get whether another object is an ::class:`Hydrofabric` instance equal to this one.

        To be equal, two hydrofabrics must have equivalent lists (when sorted) of catchments, nexuses, and links between
        features.  Links are handled using the encoded form from ::method:`_get_link_representations`, which is used to
        get the list of links.

        Parameters
        ----------
        other
            The item to compare to this one.

        Returns
        -------
        bool
            ``True`` when the other item is equal, or ``False`` otherwise.
        """
        if not isinstance(other, Hydrofabric):
            return False

        sorted_cat_ids = list(self.get_all_catchment_ids())
        sorted_cat_ids.sort()
        other_cat_ids = list(other.get_all_catchment_ids())
        other_cat_ids.sort()
        if sorted_cat_ids != other_cat_ids:
            return False

        sorted_nex_ids = list(self.get_all_nexus_ids())
        sorted_nex_ids.sort()
        other_nex_ids = list(other.get_all_nexus_ids())
        other_nex_ids.sort()
        if sorted_nex_ids != other_nex_ids:
            return False

        # Finally, compare these, which should already be sorted
        return self._get_link_representations == other._get_link_representations

    def __hash__(self):
        """
        Get the hash value for this instance.

        The hash is determined from the ordered lists of catchment ids, nexus ids, and link representations.  Link
        representations are obtained from the ::method:`_get_link_representations` function.

        These three lists are individually joined into comma-separated strings.  These three strings are then formatted
         into a single string with ``;`` as a separator.  It is the hash value of this last string that is returned.

        Returns
        -------
        int
            The hash value of this instance.

        See Also
        -------
        _get_link_representations
        """
        sorted_cat_ids = list(self.get_all_catchment_ids())
        sorted_cat_ids.sort()

        sorted_nex_ids = list(self.get_all_nexus_ids())
        sorted_nex_ids.sort()

        final_str = "{};{};{}".format(",".join(sorted_cat_ids),
                                      ",".join(sorted_nex_ids),
                                      ",".join(self._get_link_representations()))
        return hash(final_str)

    def _get_link_representations(self) -> List[str]:
        """
        Get sorted list containing string encodings of all links between features of the hydrofabric.

        A link between features is encoded as a string by joining the ids of the upstream and downstream features, using
        underscore (``_``) as a separator.  For example, if cat-81 is upstream of and linked to nex-92, this would be
        represented with ``cat-81_nex-92``.

        The returned list will be sorted according to the standard rules for list sorting.

        Returns
        -------
        List[str]
            A sorted list of the string encodings for all features links of the hydrofabric.

        See Also
        -------
        __hash__
        """
        links_reps = []
        for cat_id in self.get_all_catchment_ids():
            catchment: Catchment = self.get_catchment_by_id(cat_id)
            # A catchment has, at most, one outflow/downstream nexus, so ...
            if catchment.outflow is not None:
                links_reps.append("{}_{}".format(cat_id, catchment.outflow.id))

        for nex_id in self.get_all_nexus_ids():
            nexus: Nexus = self.get_nexus_by_id(nex_id)
            downstream_ids = []
            for catchment in nexus.receiving_catchments:
                downstream_ids.append(catchment.id)
            # Need to sort these also
            downstream_ids.sort()
            for cat_id in downstream_ids:
                links_reps.append("{}_{}".format(nex_id, cat_id))

        links_reps.sort()
        return links_reps

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
    def get_subset_hydrofabric(self, subset: SubsetDefinition) -> 'Hydrofabric':
        """
        Derive a hydrofabric object from this one with only entities included in a given subset.

        Parameters
        ----------
        subset : SubsetDefinition
            Subset describing which catchments/nexuses from this instance may be included in the produced hydrofabric.

        Returns
        -------
        Hydrofabric
            A hydrofabric object that is a subset of this instance as defined by the given param.
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

    @property
    @abstractmethod
    def roots(self) -> FrozenSet[str]:
        """
        Get the ids of the root features of this graph.

        Returns
        -------
        FrozenSet[str]
            The set of ids of the root nodes for the hydrofabric, from which further upstream traversal is not possible.
        """
        pass


class GeoJsonHydrofabricReader:
    """
    Util type for managing hydrofabric GeoJSON data.

    Type maintains (geo-)dataframe objects with the backing data.  It can receive these directly at initialization or
    be passed paths to files, read them, and create the data structures directly.

    From the backing dataframes, the type constructs and provides a hydrofabric graph as a dictionary of the included
    catchments and nexus, keyed by each's string id, as well as a set of ids of the root nodes of the graph.  These
    are accessible via the ::attribute:`hydrofabric_graph` and ::attribute:`roots` properties respectively, and are
    lazily instantiated.

    """

    @classmethod
    def _standardize(cls, geo_df: gpd.GeoDataFrame, source: Union[str, Path, gpd.GeoDataFrame], feature_type_str: str):
        """
        Standardize the format of a given catchment/nexus geodataframe.

        Method first makes all column names lower case.  Then, the unless initial index already has a name of ``id`` (or
        some case-insensitive equivalent), the ``id`` column is set as the index.  An error is raised this cannot be
        done because there is no ``id`` column.

        In the case of the index name already being a case-insensitive equivalent of ``id``, but not ``id`` precisely
        (e.g., ``ID``), the index's name is also standardized to ``id``.

        Parameters
        ----------
        geo_df : gpd.GeoDataFrame
            The geodataframe in question.
        source : Union[str, Path, gpd.GeoDataFrame]
            Either the source file for the data or a passed "base" geodataframe (when file, included in error messages).
        feature_type_str : str
            A string describing the type of feature for this data.
        """
        geo_df.columns = geo_df.columns.astype(str).str.lower()
        # Standardize capitalization if it looks like this is already set properly
        if geo_df.index.name != 'id' and str(geo_df.index.name).lower() == 'id':
            geo_df.index.name = 'id'
        # Otherwise, set the index as the 'id' column
        elif geo_df.index.name != 'id':
            # This requires 'id' column to be present of course
            if 'id' not in geo_df.columns:
                # Adjust error message depending on whether the source was an existing dataframe or a data file
                if not isinstance(source, gpd.GeoDataFrame):
                    msg = 'Bad format of {} file {}: no \'id\' or \'ID\' column'.format(feature_type_str, source)
                else:
                    msg = 'Bad format of {} dataframe: no \'id\' or \'ID\' column'.format(feature_type_str)
                raise RuntimeError(msg.format(msg))
            geo_df.set_index('id', inplace=True)

    def __init__(self, catchment_data: Union[str, Path, gpd.GeoDataFrame],
                 nexus_data: Union[str, Path, gpd.GeoDataFrame], cross_walk: Union[str, Path, pd.DataFrame]):
        if isinstance(catchment_data, gpd.GeoDataFrame):
            self.catchment_geodataframe = catchment_data
        else:
            self.catchment_geodataframe = gpd.read_file(catchment_data)
        self._standardize(self.catchment_geodataframe, catchment_data, 'catchment hydrofabric')

        if isinstance(nexus_data, gpd.GeoDataFrame):
            self.nexus_geodataframe = nexus_data
        else:
            self.nexus_geodataframe = gpd.read_file(nexus_data)
        self._standardize(self.nexus_geodataframe, nexus_data, 'nexus hydrofabric')

        if isinstance(cross_walk, pd.DataFrame):
            self.crosswalk_dataframe = cross_walk
        else:
            self.crosswalk_dataframe = pd.read_json(cross_walk, dtype=str)

        self._hydrofabric_graph = None
        self._roots = None

    @property
    def hydrofabric_graph(self) -> Dict[str, Union[Catchment, Nexus]]:
        """
        Lazily get the hydrofabric object graph as a dictionary of the elements by their ids.

        Using data in ::attribute:`catchment_geodataframe` and ::attribute:`nexus_geodataframe`, method generates (when
        necessary) a hydrofabric object graph of associated ::class:`Catchment` and ::class:`Nexus` objects, including
        all the inter-object relationships.  These are collected in dictionary data structure keyed by the ``id``
        property of each object.  Once that is created, the backing attribute is set to this dictionary for subsequent
        reuse, and the dictionary is returned.

        As the dictionary is built, the set of root notes is also determined and saved to ::attribute:`roots`.

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
            # Start with all catchments as roots (for now, they are) and then remove later
            # Root nexuses we will add individually below
            roots = set(known_catchment_ids)

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
                # Add ids of nexuses without contributors to set of roots
                if len(contributing) == 0:
                    roots.add(nex_id)
            # Now go back and apply the right to/from relationships for catchments
            for cat_id, nex_id in cat_to.items():
                hf[cat_id]._outflow = hf[nex_id]
            for cat_id, nex_id in cat_from.items():
                hf[cat_id]._inflow = hf[nex_id]
                # Remove any catchment ids from roots that have an upstream/inflow nexus
                if cat_id in roots:
                    roots.remove(cat_id)
            # TODO: again, do we need to worry about contained/containing/conjoined?
            # Finally ...
            self._hydrofabric_graph = hf
            self._roots = frozenset(roots)
        return self._hydrofabric_graph

    @property
    def roots(self) -> FrozenSet[str]:
        """
        Lazily get the ids of the root nodes of the graph.

        Makes a call to the property method for ::attribute:`hydrofabric_graph` when necessary to create, lazily
        initializing both properties.

        Returns
        -------
        FrozenSet[str]
            The set of ids for the roots of the graph.

        See Also
        -------
        ::attribute:`hydrofabric_graph`
        """
        if self._roots is None:
            # Use to lazily instantiate this property also
            graph = self.hydrofabric_graph
        return self._roots


class SubsetGeoJsonHydrofabricReader(GeoJsonHydrofabricReader):
    """
    Extension of ::class:`GeoJsonHydrofabricReader` to facilitate handling subsets.

    This type requires an existing "base" ::class:`GeoJsonHydrofabricReader` and a subset definition be provided during
    initialization.  It runs the superclass initialization routine, passing geodataframe data params obtained by
    filtering the analogs of the "base" to just the rows applicable to the given subset.
    """

    def __init__(self, base: GeoJsonHydrofabricReader, subset: SubsetDefinition):
        # Reduce based on subset using Pandas indexing
        # TODO: look later if we need to also address the crosswalk somehow for subsetting
        super(SubsetGeoJsonHydrofabricReader, self).__init__(
            catchment_data=base.catchment_geodataframe.loc[list(subset.catchment_ids)],
            nexus_data=base.nexus_geodataframe.loc[list(subset.nexus_ids)],
            cross_walk=base.crosswalk_dataframe)
        self._base = base
        self._subset = subset


class MappedGraphHydrofabric(Hydrofabric):
    """
    Subtype of ::class:`Hydrofabric` created from an object graph stored as a dictionary.
    """

    def __init__(self, hydrofabric_object_graph: Dict[str, Union[Catchment, Nexus]], roots: FrozenSet[str],
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
        self._roots = roots
        for obj_id, obj in self._hydrofabric_graph.items():
            if isinstance(obj, Catchment):
                self._catchment_ids.add(obj_id)
            else:
                self._nexus_ids.add(obj_id)

    # def _get_new_subset_hydrofabric_roots(self, subset: SubsetDefinition) -> FrozenSet[str]:
    #     """
    #     Get the roots of a subset of this instance's hydrofabric as defined by the given parameter.
    #
    #     Parameters
    #     ----------
    #     subset : SubsetDefinition
    #         A definition for the applicable subset of this instance's hydrofabric for which roots are wanted.
    #
    #     Returns
    #     -------
    #     FrozenSet[str]
    #         The (frozen) set of ids for the roots of a the applicable subset hydrofabric.
    #     """
    #     already_seen = set()
    #     new_roots = set()
    #     possible_roots = set(self.roots)
    #     while len(possible_roots) > 0:
    #         # Pop possible root pr
    #         potential_root = possible_roots.pop()
    #         if potential_root in already_seen:
    #             continue
    #         else:
    #             already_seen.add(potential_root)
    #         if potential_root in subset.catchment_ids or potential_root in subset.nexus_ids:
    #             new_roots.add(potential_root)
    #         else:
    #             # add ids of each child to possible roots
    #             possible_roots.update(
    #                 self.get_ids_of_connected(feature=self._hydrofabric_graph[potential_root],
    #                                           upstream=False,
    #                                           downstream=True))
    #     return frozenset(new_roots)

    def get_subset_hydrofabric(self, subset: SubsetDefinition) -> 'MappedGraphHydrofabric':
        """
        Derive a hydrofabric object from this one with only entities included in a given subset.

        Parameters
        ----------
        subset : SubsetDefinition
            Subset describing which catchments/nexuses from this instance may be included in the produced hydrofabric.

        Returns
        -------
        GeoJsonHydrofabric
            A hydrofabric object that is a subset of this instance as defined by the given param.
        """
        new_graph: Dict[str, Union[Catchment, Nexus]] = dict()
        new_graph_roots = set()
        # TODO: consider changing to implement via Pickle and copy module later
        graph_features_stack = list(self.roots)
        already_seen = set()
        # keep track of new graph entities where we can't immediately link to one (or more) of their parents
        unlinked_to_parent = defaultdict(set)
        # Keep track of catchments with related nested catchments to handle at the end
        have_nested_catchments = set()

        while len(graph_features_stack) > 0:
            feature_id = graph_features_stack.pop()
            if feature_id in already_seen:
                continue
            else:
                already_seen.add(feature_id)
            old_cat = self._hydrofabric_graph[feature_id]
            # add ids for all downstream connected features to graph_features_stack for later processing
            graph_features_stack.extend(self.get_ids_of_connected(old_cat, upstream=False, downstream=True))

            subset_copy_of_feature = None
            # Assume False means feature is a Nexus
            is_catchment = False
            # If feature is in subset, make the start of a deep copy.
            #   Note that the deep copy's upstream refs are handled in next step, and downstream refs are handled during
            #   creation of the subset copy of the downstream object
            if feature_id in subset.catchment_ids:
                is_catchment = True
                subset_copy_of_feature = Catchment(feature_id, params=dict(), realization=old_cat.realization)
                # Must track and handle (later) contained_catchments, containing_catchment, and conjoined_catchments
                if old_cat.containing_catchment is not None:
                    if old_cat.containing_catchment.id in subset.catchment_ids:
                        have_nested_catchments.add(feature_id)
                        graph_features_stack.append(old_cat.containing_catchment.id)
                if old_cat.contained_catchments:
                    contained_ids = [c.id for c in old_cat.contained_catchments if c.id in subset.catchment_ids]
                    have_nested_catchments.update(contained_ids)
                    graph_features_stack.extend(contained_ids)
                if old_cat.conjoined_catchments:
                    conjoined_ids = [c.id for c in old_cat.conjoined_catchments if c.id in subset.catchment_ids]
                    have_nested_catchments.update(conjoined_ids)
                    graph_features_stack.extend(conjoined_ids)

            elif feature_id in subset.nexus_ids:
                subset_copy_of_feature = Nexus(feature_id, hydro_location=old_cat._hydro_location)

            # Will be None when not in subset, so ...
            if subset_copy_of_feature is not None:
                # add to new_graph
                new_graph[feature_id] = subset_copy_of_feature
                # Get the ids of parents in the subset
                parent_ids = self.get_ids_of_connected(old_cat, upstream=True, downstream=False)
                pids_in_subset = [pid for pid in parent_ids if (pid in subset.catchment_ids or pid in subset.nexus_ids)]
                # If old feature does not have any parents that will be in the subset, this is a new root
                if len(pids_in_subset) == 0:
                    new_graph_roots.add(feature_id)
                # For each parent in the subset, set up ref to new copy of parent and its ref down to feature's new copy
                for pid in pids_in_subset:
                    # if parent copy in new graph (i.e., the copy exists)
                    if pid in new_graph:
                        # set upstream connections to parent copy and downstream connection of parent copy to this
                        if is_catchment:
                            self.connect_features(catchment=subset_copy_of_feature, nexus=new_graph[pid],
                                                  is_catchment_upstream=False)
                        else:
                            self.connect_features(catchment=new_graph[pid], nexus=subset_copy_of_feature,
                                                  is_catchment_upstream=True)
                    # If parent copy not in new graph yet (i.e., does not exist), add to collection to deal with later
                    else:
                        unlinked_to_parent[feature_id].add(pid)

        # Now deal with any previously unlinked parents
        for feature_id in unlinked_to_parent:
            new_cat = new_graph[feature_id]
            if isinstance(new_cat, Catchment):
                for pid in unlinked_to_parent[feature_id]:
                    self.connect_features(catchment=new_cat, nexus=new_graph[pid], is_catchment_upstream=False)
            else:
                for pid in unlinked_to_parent[feature_id]:
                    self.connect_features(catchment=new_graph[pid], nexus=new_cat, is_catchment_upstream=True)

        # Also deal with any catchment conjoined, containing, or contained collections
        for cid in subset.catchment_ids:
            old_cat = self._hydrofabric_graph[cid]
            new_cat = new_graph[cid]
            if old_cat.containing_catchment is not None and old_cat.containing_catchment.id in subset.catchment_ids:
                new_cat._containing_catchment = new_graph[old_cat.containing_catchment.id]
            if old_cat.contained_catchments:
                for contained_id in [c.id for c in old_cat.contained_catchments if c.id in subset.catchment_ids]:
                    if contained_id not in [c.id for c in new_cat.contained_catchments]:
                        new_cat.contained_catchments = new_cat.contained_catchments + (new_graph[contained_id],)
            if old_cat.conjoined_catchments:
                for conjoined_id in [c.id for c in old_cat.conjoined_catchments if c.id in subset.catchment_ids]:
                    if conjoined_id not in [c.id for c in new_cat.conjoined_catchments]:
                        new_cat.conjoined_catchments = new_cat.conjoined_catchments + (new_graph[conjoined_id],)

        return MappedGraphHydrofabric(hydrofabric_object_graph=new_graph, roots=frozenset(new_graph_roots),
                                      graph_creator=self)

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

    @property
    def roots(self) -> FrozenSet[str]:
        """
        Get the ids of the root features of this graph.

        Returns
        -------
        FrozenSet[str]
            The set of ids of the root nodes for the hydrofabric, from which further upstream traversal is not possible.
        """
        return self._roots


class GeoJsonHydrofabric(MappedGraphHydrofabric):
    """
    Mapped ::class:`Hydrofabric` subtype created from GeoJSON data.

    Subtype of ::class:`Hydrofabric` (specifically :class:`MappedGraphHydrofabric`) created from GeoJSON data or data
    files. It possesses a ::attribute:`geojson_reader` property for accessing the ::class:`GeoJsonHydrofabricReader`
    object that is directly responsible for managing the backing hydrofabric GeoJSON data.

    A ::class:`GeoJsonHydrofabricReader` parameter must be provided for typical initialization.  However, a factory
    method is available (::method:`factory_create_from_data`) for easily getting a new object from the necessary
    GeoJSON data.
    """

    @classmethod
    def factory_create_from_data(cls, catchment_data: Union[str, Path, gpd.GeoDataFrame],
                                 nexus_data: Union[str, Path, gpd.GeoDataFrame],
                                 cross_walk: Union[str, Path, pd.DataFrame]) -> 'GeoJsonHydrofabric':
        """
        Create an instance by creating and passing the required ::class:`GeoJsonHydrofabricReader`.

        This factory method expects all the parameters required to initialize a new ::class:`GeoJsonHydrofabricReader`.
        It then does so and uses said instance to initialize and return a new ::class:`GeoJsonHydrofabric` object

        Parameters
        ----------
        catchment_data : Union[str, Path, gpd.GeoDataFrame]
            The catchment data or data file needed for creating the required ::class:`GeoJsonHydrofabricReader`.
        nexus_data : Union[str, Path, gpd.GeoDataFrame]
            The nexus data or data file needed for creating the required ::class:`GeoJsonHydrofabricReader`.
        cross_walk : Union[str, Path, gpd.GeoDataFrame]
            The cross walk data or data file needed for creating the required ::class:`GeoJsonHydrofabricReader`.

        Returns
        -------
        GeoJsonHydrofabric
            A new ::class:`GeoJsonHydrofabric` object.
        """
        return cls(GeoJsonHydrofabricReader(catchment_data, nexus_data, cross_walk))

    def __init__(self, geojson_reader: GeoJsonHydrofabricReader):
        """
        Initialize the instance.

        Parameters
        ----------
        geojson_reader : GeoJsonHydrofabricReader
            The reader object which will generate the GeoJSON-based hydrograph.
        """
        super(GeoJsonHydrofabric, self).__init__(geojson_reader.hydrofabric_graph, geojson_reader.roots, geojson_reader)

    def get_subset_hydrofabric(self, subset: SubsetDefinition) -> 'GeoJsonHydrofabric':
        """
        Derive a hydrofabric object from this one with only entities included in a given subset.

        Parameters
        ----------
        subset : SubsetDefinition
            Subset describing which catchments/nexuses from this instance may be included in the produced hydrofabric.

        Returns
        -------
        GeoJsonHydrofabric
            A hydrofabric object that is a subset of this instance as defined by the given param.
        """
        return GeoJsonHydrofabric(geojson_reader=SubsetGeoJsonHydrofabricReader(self.geojson_reader, subset))

    @property
    def geojson_reader(self) -> GeoJsonHydrofabricReader:
        return self._graph_creator

