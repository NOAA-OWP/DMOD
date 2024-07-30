import geopandas as gpd
import json
from dmod.modeldata import SubsetHandler
from pathlib import Path
from typing import List, Optional, Union


class Cli:
    """
    Class for managing CLI operations for this module.
    """

    def __init__(self,
                 catchment_geojson: Union[str, Path],
                 nexus_geojson: Union[str, Path],
                 crosswalk_json: Union[str, Path, None] = None,
                 partition_file_str: Optional[str] = None,
                 subset_handler: Optional[SubsetHandler] = None):
        self.catchment_geojson = catchment_geojson if isinstance(catchment_geojson, Path) else Path(catchment_geojson)
        self.nexus_geojson = nexus_geojson if isinstance(nexus_geojson, Path) else Path(nexus_geojson)
        self.files_dir = self.catchment_geojson.parent

        if crosswalk_json is None:
            self.crosswalk = self.files_dir / 'crosswalk.json'
        elif isinstance(crosswalk_json, Path):
            self.crosswalk = crosswalk_json
        else:
            self.crosswalk = Path(crosswalk_json)

        self._partitions_file_str = partition_file_str
        self._partitions_file = None
        if subset_handler is None:
            self.handler = SubsetHandler.factory_create_from_geojson(catchment_data=catchment_geojson,
                                                                     nexus_data=nexus_geojson,
                                                                     cross_walk=crosswalk_json)
        else:
            self.handler = subset_handler

    @property
    def partitions_file(self) -> Path:
        if self._partitions_file is None and self._partitions_file_str is not None:
            # Look for partition file either relative to working directory or files directory
            partitions_file = Path.cwd() / self._partitions_file_str
            if not partitions_file.exists():
                partitions_file = self.files_dir / self._partitions_file_str
            if partitions_file.exists():
                self._partitions_file = partitions_file
        return self._partitions_file

    # TODO: incorporate a little more tightly with the modeldata package and the Hydrofabric and SubsetDefinition types
    def divide_hydrofabric(self, partition_index: Optional[int] = None) -> bool:
        """
        Subdivide a GeoJSON hydrofabric according to a supplied partitions config, writing to new files.

        Function reads partition config from the supplied file location relative to either ::attribute:`files_dir` or
        the current working directory (it returns ``False`` immediately if there it fails to find a file there). Next it
        reads in the full hydrofabric files into catchment and nexus ::class:`GeoDataFrame` objects.  It then iterates
        through each partition, extracting the subsets of catchments and nexuses of the each partition from the full
        hydrofabric and writing those subsets to files.

        The partition-specific output files are written in to same directory as the analogous full hydrofabric file.
        Their names are based on partition index and the name of the full hydrofabric file, with a dot (``.``) and the
        index being added as a suffix to the latter to form the name.  E.g. for a ``catchment_data.geojson`` file,
        output files will have names like ``catchment_data.geojson.0``, ``catchment_data.geojson.1``, etc., with these
        being created in the same directory as the original ``catchment_data.geojson``.

        Finally, it is possible to limit the writing of the output files to just a single partition, if that partition
        index is provided.

        Parameters
        ----------
        partition_index: Optional[int]
            An optional index for a single partition, if only the subdivided hydrofabric files for that partition should
            be created.

        Returns
        -------
        bool
            Whether the operation completed successfully.
        """
        if self.partitions_file is None:
            print("Error: cannot find partition file {} from either working directory or given files directory {}".format(
                self._partitions_file_str, self.files_dir))
            return False

        with self.partitions_file.open() as f:
            partition_config_json = json.load(f)

        hydrofabric_catchments = gpd.read_file(str(self.catchment_geojson))
        hydrofabric_catchments.set_index('id', inplace=True)

        hydrofabric_nexuses = gpd.read_file(str(self.nexus_geojson))
        hydrofabric_nexuses.set_index('id', inplace=True)

        # This may be just the single give partition; otherwise it will be the indices of all in the range
        if partition_index and partition_index in partition_config_json['partitions']:
            partition_indices = [partition_index]
        else:
            partition_indices = range(len(partition_config_json['partitions']))

        for i in partition_indices:
            partition_cat_ids = partition_config_json['partitions'][i]['cat-ids']
            partition_catchments: gpd.GeoDataFrame = hydrofabric_catchments.loc[partition_cat_ids]
            partition_catchment_file = self.catchment_geojson.parent / '{}.{}'.format(self.catchment_geojson.name, i)
            partition_catchments.to_file(str(partition_catchment_file), driver='GeoJSON')

            partition_nexus_ids = partition_config_json['partitions'][i]['nex-ids']
            partition_nexuses = hydrofabric_nexuses.loc[partition_nexus_ids]
            partition_nexuses_file = self.nexus_geojson.parent / '{}.{}'.format(self.nexus_geojson.name, i)
            partition_nexuses.to_file(str(partition_nexuses_file), driver='GeoJSON')
        return True

    def output_subset(self, cat_ids: List[str], is_simple: bool, format_json: bool,
                      output_file_name: Optional[Path] = None) -> bool:
        """
        Perform CLI operations to output a subset, either to standard out or a file.

        Parameters
        ----------
        cat_ids: List[str]
            A list of string catchment ids from which the subset will be created.
        is_simple: bool
            Whether a simple subset is created (when ``False``, and upstream type subset will be created).
        format_json: bool
            Whether the output should have pretty JSON formatting.
        output_file_name: Optional[str]
            Optional file in which to write the output; when ``None``, output is printed.

        Returns
        -------
        bool
            Whether the CLI operation was completed successfully.
        """
        if not cat_ids:
            print("Cannot run CLI operation without specifying at least one catchment id (see --help for details).")
            return False
        subset = self.handler.get_subset_for(cat_ids) if is_simple else self.handler.get_upstream_subset(cat_ids)
        json_output_str = subset.to_json()
        if format_json:
            json_output_str = json.dumps(json.loads(json_output_str), indent=4, sort_keys=True)
        if output_file_name:
            output_file_name.write_text(json_output_str)
        else:
            print(json_output_str)
        return True
