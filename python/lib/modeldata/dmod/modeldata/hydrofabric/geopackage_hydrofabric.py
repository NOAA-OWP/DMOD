import fiona
import geopandas as gpd
import hashlib
from pandas.util import hash_pandas_object
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Tuple, Union
from hypy import Catchment, Nexus, Realization
from .hydrofabric import Hydrofabric
from ..subset import SubsetDefinition


class GeoPackageCatchment(Catchment):
    """
    Customized subtype of ::class:`Catchment` backed by dataframes from a parent ::class:`GeoPackageHydrofabric`.

    Type overrides most properties of superclass so that those can be evaluated on-demand. This supports creating an
    instance based on data and a parent, and defers the association (or really, associates indirectly and gets the
    linked object on-demand) to things like a connected nexus for which the nexus object may or may not yet exist.
    """

    __slots__ = ["_cat_id", "_hydrofabric", "_catchments_df", "_nexuses_df", "_realization", "_col_cat_id",
                 "_col_nex_id", "_col_to_cat", "_col_to_nex"]

    def __init__(self, cat_id: str, hydrofabric: 'GeoPackageHydrofabric', catchments_df: gpd.GeoDataFrame,
                 nexuses_df: gpd.GeoDataFrame, col_cat_id: str, col_nex_id: str, col_to_cat: str, col_to_nex: str):
        """
        Initialize this instance.

        Parameters
        ----------
        cat_id : str
            The id of the represented catchment.
        hydrofabric : GeoPackageHydrofabric
            The backing package hydrofabric.
        catchments_df : gpd.GeoDataFrame
            The geodataframe from parent hydrofabric specifically containing catchment data (for hydrologic modeling).
        nexuses_df : gpd.GeoDataFrame
            The geodataframe from parent hydrofabric specifically containing nexus data.
        col_cat_id : str
            The name of the column within ``catchments_df`` that holds catchment ids.
        col_nex_id : str
            The name of the column within ``nexuses_df`` that holds nexus ids.
        col_to_cat : str
            The name of the column within ``nexuses_df`` that holds reference to downstream catchment (by id).
        col_to_nex : str
            The name of the column within ``catchments_df`` that holds reference to downstream catchment (by id).
        """
        self._cat_id: str = cat_id
        self._hydrofabric: GeoPackageHydrofabric = hydrofabric
        self._catchments_df: gpd.GeoDataFrame = catchments_df
        self._nexuses_df: gpd.GeoDataFrame = nexuses_df
        self._col_cat_id = col_cat_id
        self._col_nex_id = col_nex_id
        self._col_to_cat = col_to_cat
        self._col_to_nex = col_to_nex

        self._realization = None

    def _get_conjoined_ids(self) -> List[str]:
        """
        Process and return the list of ids of those catchments in a conjoined relationship with this instance.

        Returns
        -------
        List[str]
            The list of ids of catchments in a conjoined relationship with this instance.
        """
        # TODO: implement properly
        raise NotImplementedError

    def _get_contained_ids(self) -> List[str]:
        """
        Process and return the list of ids of those catchments having an "is-in" relationship with this instance.

        Returns
        -------
        List[str]
            The list of ids of those catchments having an "is-in" relationship with this instance.
        """
        # TODO: implement properly
        raise NotImplementedError

    def _get_catchment_record(self) -> gpd.GeoDataFrame:
        """
        Get the (1-line) sub-dataframe from the catchments layer dataframe for this particular catchment.

        Returns
        -------
        gpd.GeoDataFrame
            The (1-line) sub-dataframe from the catchments layer dataframe for this particular catchment.
        """
        df = self._catchments_df.loc[self._catchments_df[self._col_cat_id] == self._cat_id]
        if df.shape[0] == 0:
            msg = 'No backing records in {} data for {} {}'
            raise RuntimeError(msg.format(self._hydrofabric.__class__.__name__, self.__class__.__name__, self._cat_id))
        elif df.shape[0] > 1:
            msg = 'Multiple ({}) backing records in {} data for catchment with id {}'
            raise RuntimeError(msg.format(df.shape[0], self._hydrofabric.__class__.__name__, self._cat_id))
        else:
            return df

    @property
    def conjoined_catchments(self) -> Tuple['GeoPackageCatchment', ...]:
        """

        Returns
        -------
        Tuple['GeoPackageCatchment']
            Tuple of catchment objects in a conjoined relationship with this object.
        """
        return tuple([c for c in [self._hydrofabric.get_catchment_by_id(cid) for cid in self._get_conjoined_ids()] if
                      c is not None])

    @property
    def contained_catchments(self) -> Tuple['GeoPackageCatchment', ...]:
        """
        Tuple of catchment object having an "is-in" relationship with this catchment object.

        Returns
        -------
        Tuple[GeoPackageCatchment]
            Tuple of catchment object having an "is-in" relationship with this catchment object.
        """
        return tuple([c for c in [self._hydrofabric.get_catchment_by_id(cid) for cid in self._get_contained_ids()] if
                      c is not None])

    @property
    def containing_catchment(self) -> Optional['GeoPackageCatchment']:
        """
        The (optional) catchment with which this catchment has an "is-in" relationship.

        Returns
        -------
        Optional[GeoPackageCatchment]
            The catchment with which this catchment has an "is-in" relationship, or ``None`` if there is not one.
        """
        # TODO: implement properly
        raise NotImplementedError

    @property
    def id(self) -> str:
        """
        The catchment identifier.

        Returns
        -------
        str
            The catchment identifier.
        """
        return self._cat_id

    @property
    def inflow(self) -> Optional['GeoPackageNexus']:
        """
        In-flowing connected Nexus.

        Returns
        -------
        Optional[GeoPackageNexus]
            In-flowing connected Nexus.
        """
        matches_df = self._nexuses_df.loc[self._nexuses_df[self._col_to_cat] == self._cat_id]
        if matches_df.shape[0] > 1:
            raise RuntimeError("Invalid catchment {} with multiple inflow nexuses".format(self._cat_id))
        elif matches_df.shape[0] == 0:
            return None
        else:
            return self._hydrofabric.get_nexus_by_id(matches_df[self._col_nex_id].values[0])

    @property
    def outflow(self) -> Optional['GeoPackageNexus']:
        """
        Out-flowing connected ::class:`GeoPackageNexus`.

        Returns
        -------
        Optional[GeoPackageNexus]
            Out-flowing connected nexus.
        """
        nex_id = self._get_catchment_record()[self._col_to_nex].values[0]
        return self._hydrofabric.get_nexus_by_id(nex_id)

    @property
    def realization(self) -> Optional[Realization]:
        """
        The optional ::class:`Realization` for this catchment.

        Returns
        -------
        Optional[Realization]
            The ::class:`Realization` for this catchment, or ``None`` if it has not been set.
        """
        return self._realization

    @realization.setter
    def realization(self, realization: Realization):
        self._realization = realization


class GeoPackageNexus(Nexus):
    """
    Customized subtype of ::class:`Nexus` backed by dataframes from a parent ::class:`GeoPackageHydrofabric`.

    Type overrides most properties of superclass so that those can be evaluated on-demand. This supports creating an
    instance based on data and a parent, and defers the association (or really, associates indirectly and gets the
    linked object on-demand) to things like a connected catchment for which the catchment object may or may not yet
    exist.
    """

    __slots__ = ["_nex_id", "_hydrofabric", "_catchments_df", "_nexuses_df", "_col_cat_id", "_col_nex_id",
                 "_col_to_cat", "_col_to_nex"]

    def __init__(self, nex_id: str, hydrofabric: 'GeoPackageHydrofabric', catchments_df: gpd.GeoDataFrame,
                 nexuses_df: gpd.GeoDataFrame, col_cat_id: str, col_nex_id: str, col_to_cat: str, col_to_nex: str):
        """
        Initialize this instance.

        Parameters
        ----------
        nex_id : str
            The id of the represented nexus.
        hydrofabric : GeoPackageHydrofabric
            The backing package hydrofabric.
        catchments_df : gpd.GeoDataFrame
            The geodataframe from parent hydrofabric specifically containing catchment data (for hydrologic modeling).
        nexuses_df : gpd.GeoDataFrame
            The geodataframe from parent hydrofabric specifically containing nexus data.
        col_cat_id : str
            The name of the column within ``catchments_df`` that holds catchment ids.
        col_nex_id : str
            The name of the column within ``nexuses_df`` that holds nexus ids.
        col_to_cat : str
            The name of the column within ``nexuses_df`` that holds reference to downstream catchment (by id).
        col_to_nex : str
            The name of the column within ``catchments_df`` that holds reference to downstream catchment (by id).
        """
        self._nex_id: str = nex_id
        self._hydrofabric: GeoPackageHydrofabric = hydrofabric
        self._catchments_df: gpd.GeoDataFrame = catchments_df
        self._nexuses_df: gpd.GeoDataFrame = nexuses_df
        self._col_cat_id = col_cat_id
        self._col_nex_id = col_nex_id
        self._col_to_cat = col_to_cat
        self._col_to_nex = col_to_nex

    def _get_nexus_record(self) -> gpd.GeoDataFrame:
        """
        Get the (1-line) sub-dataframe from the ``nexus`` layer dataframe for this particular nexus.

        Returns
        -------
        gpd.GeoDataFrame
            The (1-line) ssub-dataframe from the ``nexus`` layer dataframe for this particular nexus.
        """
        df = self._nexuses_df.loc[self._nexuses_df[self._col_nex_id] == self._nex_id]
        if df.shape[0] == 0:
            msg = 'No backing records in {} data for {} {}'
            raise RuntimeError(msg.format(self._hydrofabric.__class__.__name__, self.__class__.__name__, self._nex_id))
        elif df.shape[0] > 1:
            msg = 'Multiple ({}) backing records in {} data for nexus with id {}'
            raise RuntimeError(msg.format(df.shape[0], self._hydrofabric.__class__.__name__, self._nex_id))
        else:
            return df

    @property
    def id(self) -> str:
        """
        The nexus identifier.

        Returns
        -------
        str
            The nexus identifier.
        """
        return self._nex_id

    @property
    def receiving_catchments(self) -> Tuple['GeoPackageCatchment', ...]:
        """
        Tuple of GeoPackageCatchment object(s) receiving water from nexus

        Returns
        -------
        Tuple['GeoPackageCatchment']
            Tuple of GeoPackageCatchment object(s) receiving water from nexus
        """
        catchments = [self._hydrofabric.get_catchment_by_id(cid) for cid in
                      self._get_nexus_record()[self._col_to_cat].values]
        return tuple([c for c in catchments if c is not None])

    @property
    def contributing_catchments(self) -> Tuple['GeoPackageCatchment', ...]:
        """
        Tuple of GeoPackageCatchment object(s) contributing water to nexus

        Returns
        -------
        Tuple['GeoPackageCatchment']
            Tuple of GeoPackageCatchment object(s) contributing water to nexus
        """
        cat_rows = self._catchments_df.loc[self._catchments_df[self._col_to_nex] == self._nex_id]
        cat_lookups = [self._hydrofabric.get_catchment_by_id(cid) for cid in
                       cat_rows[self._col_cat_id].values]
        return tuple([c for c in cat_lookups if c is not None])


class GeoPackageHydrofabric(Hydrofabric):
    """
    Hydrofabric implementation sourced from and backed by Nextgen hydrofabric GeoPackage (v1.2) artifacts.

    See https://noaa-owp.github.io/hydrofabric/schema.html.
    """

    #_FLOWPATHS_LAYER_NAME = 'flowpaths'
    #_FLOWPATHS_CAT_ID_COL = 'realized_catchment'
    #_FLOWPATHS_TO_NEX_COL = 'toid'

    _DIVIDES_LAYER_NAME = 'divides'
    _DIVIDES_CAT_ID_COL = 'id'
    _DIVIDES_TO_NEX_COL = 'toid'

    _NEXUS_LAYER_NAME = 'nexus'
    _NEXUS_NEX_ID_COL = 'id'
    _NEXUS_TO_CAT_COL = 'toid'

    @classmethod
    def from_file(cls, geopackage_file: Union[str, Path], vpu: Optional[int] = None, is_conus: bool = False) -> 'GeoPackageHydrofabric':
        """
        Initialize a new instance from a GeoPackage file.

        Parameters
        ----------
        geopackage_file: Union[str, Path]
            The source file for data from which to instantiate.
        vpu: Optional[int]
            The VPU of the hydrofabric to create, if it is known (defaults to ``None``).
        is_conus: bool
            Whether this hydrofabric is for all of CONUS (defaults to ``False``).

        Returns
        -------
        GeoPackageHydrofabric
            A new instance of this type.
        """
        layer_names = fiona.listlayers(geopackage_file)
        return cls(layer_names=layer_names,
                   layer_dataframes={ln: gpd.read_file(geopackage_file, layer=ln, engine="pyogrio") for ln in layer_names},
                   vpu=vpu,
                   is_conus=is_conus)

    def __init__(self, layer_names: List[str], layer_dataframes: Dict[str, gpd.GeoDataFrame], vpu: Optional[int] = None,
                 is_conus: bool = False):
        self._layer_names: List[str] = layer_names
        self._dataframes: Dict[str, gpd.GeoDataFrame] = layer_dataframes
        self._roots = None
        self._vpu = vpu
        self._is_conus = is_conus

        #flowpaths = self._dataframes[self._FLOWPATHS_LAYER_NAME]
        divides = self._dataframes[self._DIVIDES_LAYER_NAME]
        nexuses = self._dataframes[self._NEXUS_LAYER_NAME]

        col_args = {'col_cat_id': self._DIVIDES_CAT_ID_COL, 'col_nex_id': self._NEXUS_NEX_ID_COL,
                    'col_to_cat': self._NEXUS_TO_CAT_COL, 'col_to_nex': self._DIVIDES_TO_NEX_COL}

        self._catchments: Dict[str, GeoPackageCatchment] = dict(
            [(cid, GeoPackageCatchment(cid, self, divides, nexuses, **col_args)) for cid in
             self.get_all_catchment_ids()])

        self._nexuses: Dict[str, GeoPackageNexus] = dict(
            [(nid, GeoPackageNexus(nid, self, divides, nexuses, **col_args)) for nid in self.get_all_nexus_ids()])

    def __eq__(self, other):
        if not isinstance(other, GeoPackageHydrofabric) or self.uid != other.uid:
            return False
        if len(self._layer_names) != len(other._layer_names):
            return False
        for layer_name in self._layer_names:
            if layer_name not in other._dataframes:
                return False
            elif not self._dataframes[layer_name].equals(other._dataframes[layer_name]):
                return False
        return True

    def __hash__(self) -> int:
        return hash(self.uid)

    def get_all_catchment_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained catchments.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained catchments.
        """
        return tuple(self._dataframes[self._DIVIDES_LAYER_NAME][self._DIVIDES_CAT_ID_COL].values)

    def get_all_nexus_ids(self) -> Tuple[str, ...]:
        """
        Get ids for all contained nexuses.

        Returns
        -------
        Tuple[str, ...]
            Ids for all contained nexuses.
        """
        return tuple(self._dataframes[self._NEXUS_LAYER_NAME][self._NEXUS_NEX_ID_COL].values)

    def get_catchment_by_id(self, catchment_id: str) -> Optional[GeoPackageCatchment]:
        return self._catchments.get(catchment_id)

    def get_nexus_by_id(self, nexus_id: str) -> Optional[GeoPackageNexus]:
        return self._nexuses.get(nexus_id)

    def get_subset_hydrofabric(self, subset: SubsetDefinition) -> 'GeoPackageHydrofabric':
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
        # Note that this is somewhat specific to the schema of v1.2, though is probably similar to other versions
        new_dfs = dict()

        # A dictionary to encapsulate how to handle subsetting a particular, known layer type
        # The lambda is to delay evaluation, as in some cases a different layer's subset is needed for deriving a subset
        #
        # Basically, define what we should do for layer we could encounter, since it is possible to not always encounter
        # the same set of layers, even for the same version (e.g., the CONUS v1.2 file doesn't have 'forcing_metadata')
        #
        # Key: layer name
        # Value: Tuple[str, Callable[[], Iterable]]
            # Value[0]: name of column in this known layer that holds ids, which we will examine for subsetting
            # Value[1]: callable no arg function, returning collection of ids for records/rows to include in subset
        subset_query_setups: Dict[str, Tuple[str, Callable[[], Iterable[str]]]] = {
            'flowpaths': ('realized_catchment', lambda: subset.catchment_ids),
            'divides': ('id', lambda: subset.catchment_ids),
            'nexus': ('id', lambda: subset.nexus_ids),
            'flowpath_attributes': ('id', lambda: new_dfs['flowpaths']['id']),
            'flowpath_edge_list': ('id', lambda: new_dfs['flowpaths']['id']),
            'crosswalk': ('id', lambda: new_dfs['flowpaths']['id']),
            'cfe_noahowp_attributes': ('id', lambda: subset.catchment_ids),
            'forcing_metadata': ('id', lambda: subset.catchment_ids)
        }

        # Then, apply this logic to every encountered layer to create subset layer/dataframe to use to init new instance
        def subset_layer(layer_name: str):
            dataframe = self._dataframes[layer_name]
            id_search_col = subset_query_setups[layer_name][0]
            applicable_ids = subset_query_setups[layer_name][1]()
            new_dfs[layer_name] = dataframe.loc[dataframe[id_search_col].isin(applicable_ids)]

        # Subset 'flowpaths' layer first; it's ids may be needed for subsetting other things like 'flowpath_edge_list'
        if 'flowpaths' in self._layer_names:
            subset_layer('flowpaths')

        # Now, generate the rest of the subset layers/dataframes
        for layer in [ln for ln in self._layer_names if ln != 'flowpaths']:
            subset_layer(layer)

        return GeoPackageHydrofabric(layer_names=self._layer_names, layer_dataframes=new_dfs)

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
        return catchment_id in self._dataframes[self._DIVIDES_LAYER_NAME][self._DIVIDES_CAT_ID_COL].values

    @property
    def is_conus(self) -> bool:
        """
        Whether this hydrofabric represents all of CONUS.

        Returns
        -------
        bool
            Whether this hydrofabric represents all of CONUS.
        """
        return self._is_conus

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
        return nexus_id in self._dataframes[self._NEXUS_LAYER_NAME][self._NEXUS_NEX_ID_COL].values

    @property
    def roots(self) -> FrozenSet[str]:
        """
        Get the ids of the root nodes of the hydrofabric graph.

        Returns
        -------
        FrozenSet[str]
            The set of ids for the roots of the hydrofabric graph.

        See Also
        -------
        ::attribute:`hydrofabric_graph`
        """
        if self._roots is None:
            divides_df = self._dataframes[self._DIVIDES_LAYER_NAME]
            nexuses_df = self._dataframes[self._NEXUS_LAYER_NAME]
            self._roots = frozenset(divides_df.loc[~divides_df[self._DIVIDES_CAT_ID_COL].isin(
                nexuses_df[self._NEXUS_TO_CAT_COL].values)][self._DIVIDES_CAT_ID_COL].values)
        return self._roots

    @property
    def uid(self) -> str:
        """
        Get a unique id for this instance.

        Ids are generated from in a deterministic manner from the underlying data.

        Returns
        -------
        int
            A unique id for this instance.
        """
        layer_hashes = [hash_pandas_object(self._dataframes[layer]).values.sum() for layer in sorted(self._layer_names)]
        return hashlib.sha1(','.join([str(h) for h in layer_hashes]).encode('UTF-8')).hexdigest()

    @property
    def vpu(self) -> Optional[int]:
        """
        The VPU of this hydrofabric, if it is known.

        Returns
        -------
        Optional[int]
            The VPU of this hydrofabric, if it is known; otherwise ``None``.
        """
        return self._vpu

    def write_file(self, output_file: Union[str, Path], overwrite_existing: bool = False):
        """
        Write this hydrofabric to a GeoPackage file.

        If a file exists, by default an exception is thrown.  However, a parameter can be passed such that an existing
        file is removed and overwritten.  This only will apply to regular files, though.

        Parameters
        ----------
        output_file: Union[str, Path]
            The file to which to write the data.
        overwrite_existing: bool
            Whether an existing file should be overwritten (``False`` by default).
        """
        output_path = output_file if isinstance(output_file, Path) else Path(output_file)
        if output_path.exists():
            if output_path.is_dir():
                msg = 'Cannot write {} data to path {}: this is an existing directory'
                raise RuntimeError(msg.format(self.__class__.__name__, output_file))
            elif output_path.is_file() and overwrite_existing:
                msg = 'Cannot write {} data to existing file {} when overwrite is set to False'
                raise RuntimeError(msg.format(self.__class__.__name__, output_file))
            elif output_path.is_file():
                output_path.unlink()
            else:
                msg = 'Cannot write {} data to existing, non-regular file {}'
                raise RuntimeError(msg.format(self.__class__.__name__, output_file))

        for layer_name in self._layer_names:
            self._dataframes[layer_name].to_file(output_file, driver="GPKG", layer=layer_name)
