from __future__ import annotations

import json
import pandas as pd
import geopandas as gpd
import io
import tempfile
from dmod.communication import AbstractNgenRequest, NgenCalibrationRequest
from dmod.communication.maas_request.ngen.partial_realization_config import PartialRealizationConfig
from dmod.core.dataset import Dataset, DatasetManager, InitialDataAdder
from dmod.core.exception import DmodRuntimeError
from dmod.core.meta_data import DataCategory, DataFormat, DataRequirement, StandardDatasetIndex
from dmod.modeldata.data import BmiInitConfigAutoGenerator
from dmod.scheduler.job import Job
from ngen.init_config.serializer import (IniSerializer, JsonSerializer, NamelistSerializer, TomlSerializer,
                                         YamlSerializer)
from ngen.config.configurations import Forcing, Time
from ngen.config.realization import NgenRealization, Realization
from ngen.config_gen.file_writer import _get_file_extension
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, List, Optional, Set, Union

from .dataset_manager_collection import DatasetManagerCollection


class FromFilesInitialDataAdder(InitialDataAdder):
    """
    Implementation that sources data from a file or directory path received during initialization.

    A simple implementation that adds data directly sourced from either a single file or all files directly within a
    supplied directory.
    """

    def __init__(self, source_path: Union[str, Path], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source_path: Path = source_path if isinstance(source_path, Path) else Path(source_path)
        if not self._source_path.exists():
            msg = f"Can't initialize {self.__class__.__name__}: given source path '{str(source_path)}' doesn't exist"
            raise DmodRuntimeError(msg)

    def add_initial_data(self):
        """
        Assemble and add the initial data.

        If adding data from a file, the data item will be named after the basename of the file.

        If adding data from a directory, this top directory will be treated as an "add root."  The directory will then
        be traversed, adding all non-directory files to the dataset as data items, and recursively descending into
        subdirectories. Each added data item will be named based on the path of its source file relative to the original
        "add root."

        Raises
        -------
        DmodRuntimeError
            Raised when initial data could not be assembled and/or added successfully to the dataset.
        """
        original_domain = self._dataset_manager.datasets[self._dataset_name].data_domain

        # TODO: later, look at options for threading
        def _add(path: Path, dest: Optional[str] = None, add_root: Optional[Path] = None):
            if path.is_dir():
                for file_name in path.iterdir():
                    _add(path=file_name, add_root=path if add_root is None else add_root)
                return

            if not dest and not add_root:
                dest = path.name
            elif not dest:
                dest = path.relative_to(add_root)

            if not self._dataset_manager.add_data(dataset_name=self._dataset_name, dest=dest, data=path.read_bytes(),
                                                  domain=original_domain):
                msg = f"{self.__class__.__name__} failed to add item {dest} under {str(self._source_path)}"
                raise DmodRuntimeError(msg)

        try:
            _add(path=self._source_path)
        except DmodRuntimeError as e:
            raise e
        except Exception as e:
            raise DmodRuntimeError(f"{self.__class__.__name__} failed due to {e.__class__.__name__}: {str(e)}")


class FromRawInitialDataAdder(InitialDataAdder):
    """
    Very simple implementation that receives raw data at initialization that it needs to add.

    A near trivial subtype that simply receives a dictionary object whose values are the raw ``bytes`` that should be
    added to individual data items.  The ``str`` keys are the names of these data items.
    """

    def __init__(self, data_items: Dict[str, bytes], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_items: Dict[str, bytes] = data_items

    def add_initial_data(self):
        """
        Assemble and add the initial data.

        Initial data is provided in the form of a dictionary, keyed by item name, with values that are raw ``bytes`` to
        add.  Function simply iterates through the dictionary, adding items one by one, but stopping immediately and
        raising a ::class:`DmodRuntimeError` if any item fails.

        Raises
        -------
        DmodRuntimeError
            Raised when initial data could not be assembled and/or added successfully to the dataset.
        """
        original_domain = self._dataset_manager.datasets[self._dataset_name].data_domain
        try:
            for item, data in self._data_items.items():
                if not self._dataset_manager.add_data(dataset_name=self._dataset_name, dest=item, data=data,
                                                      domain=original_domain):
                    raise DmodRuntimeError(f"{self.__class__.__name__} failed to add initial data item {item}")
        except DmodRuntimeError as e:
            raise e
        except Exception as e:
            msg = f"{self.__class__.__name__} failed due to {e.__class__.__name__}: {str(e)}"
            raise DmodRuntimeError(msg)


class FromPartialRealizationConfigAdder(InitialDataAdder):
    """
    Subtype that adds a realization config derived from a ::class:`PartialRealizationConfig` to a newly created dataset.
    """

    # TODO: centrally define this somewhere else
    _REAL_CONFIG_FILE_NAME = 'realization_config.json'

    def __init__(self, job: Job, dataset_manager_collection: DatasetManagerCollection, *args, **kwargs):
        """

        Parameters
        ----------
        job : Job
            The job requiring a realization config dataset, which must be an ngen-related job.
        dataset_manager_collection: DatasetManagerCollection
            Collection of DatasetManager objects and their associated DatasetType.
        args
        kwargs
        """
        super().__init__(*args, **kwargs)
        self._job: Job = job
        request = self._job.model_request
        if isinstance(request, AbstractNgenRequest):
            self._job_request: AbstractNgenRequest = request
        else:
            raise ValueError("Can't do {} for job with {}".format(self.__class__.__name__, request.__class__.__name__))
        self._managers: DatasetManagerCollection = dataset_manager_collection

    def _build_forcing_config_for_realization(self) -> Forcing:
        """
        Build a ::class:`Forcing` config object from to satisfy requirements of this request.

        Function builds a ::class:`Forcing` config object as a part of the steps to create a ngen realization config
        for the given request.  It is typically expected that the provided request will include a partial realization
        config object that includes certain details.

        Returns
        -------
        Forcing
            Forcing config object to be used in building a ngen realization config to satisfy this request.
        """
        forcing_cfg_params = dict()

        # Get the correct forcing dataset from associated requirement
        # TODO: double check that this is being added when we do data checks
        forcing_req = [r for r in self._job_request.data_requirements if r.category == DataCategory.FORCING][0]
        forcing_dataset_name = forcing_req.fulfilled_by
        manager = [m for _, m in self._managers.managers() if forcing_dataset_name in m.datasets][0]
        forcing_dataset = manager.datasets[forcing_dataset_name]

        # Figure out the correct provider type from the dataset format
        # TODO: this may not be the right way to do this to instantiate the object directly (i.e., not through JSON)
        if forcing_dataset.data_format == DataFormat.NETCDF_FORCING_CANONICAL:
            forcing_cfg_params['provider'] = 'NetCDF'
        elif forcing_dataset.data_format == DataFormat.AORC_CSV:
            forcing_cfg_params['provider'] = 'CsvPerFeature'

        # TODO: (#needs_issue) introduce logic to examine forcing dataset and intelligently assess what the file
        #  name(s)/pattern(s) should be if they aren't explicitly provided

        if self.partial_realization_config is not None and self.partial_realization_config.forcing_file_pattern:
            forcing_cfg_params['file_pattern'] = self.partial_realization_config.forcing_file_pattern

        # Finally, produce the right path
        # TODO: these come from scheduler.py; may need to centralize somehow
        forcing_cfg_params['path'] = '/dmod/datasets/'
        if self.partial_realization_config is not None and self.partial_realization_config.is_env_workaround:
            forcing_cfg_params['path'] += 'from_env'
        else:
            forcing_cfg_params['path'] += '{}/{}/'.format(DataCategory.FORCING.name.lower(), forcing_dataset_name)

        if self.partial_realization_config is not None and self.partial_realization_config.forcing_file_name:
            forcing_cfg_params['path'] += self.partial_realization_config.forcing_file_name

        return Forcing(**forcing_cfg_params)

    def build_realization_config_from_partial(self) -> NgenRealization:
        """
        Build a ngen realization config object from current service state and partial config within the job request.

        Returns
        -------
        NgenRealization
            The built realization config.
        """
        params = dict()

        if self.partial_realization_config.global_formulations is not None:
            params['global_config'] = Realization(formulations=self.partial_realization_config.global_formulations,
                                                  forcing=self._build_forcing_config_for_realization())

        params['time'] = Time(start_time=self._job_request.time_range.begin, end_time=self._job_request.time_range.end)

        if self.partial_realization_config.routing_config is not None:
            params['routing'] = self.partial_realization_config.routing_config

        if self.partial_realization_config.catchment_formulations is not None:
            params['catchments'] = self.partial_realization_config.catchment_formulations

        return NgenRealization(**params)

    def add_initial_data(self):
        """
        Assemble and add the initial data.

        Raises
        -------
        DmodRuntimeError
            Raised when initial data could not be assembled and/or added successfully to the dataset.
        """
        original_domain = self._dataset_manager.datasets[self._dataset_name].data_domain

        if self.partial_realization_config is not None:
            raise DmodRuntimeError(f"{self.__class__.__name__} can't have 'None' for partial realization property")

        try:
            real_config: NgenRealization = self.build_realization_config_from_partial()
            if not self._dataset_manager.add_data(dataset_name=self._dataset_name, dest=self._REAL_CONFIG_FILE_NAME,
                                                  data=real_config.json().encode(), domain=original_domain):
                raise DmodRuntimeError(f"{self.__class__.__name__} failed to add realization config item")
        except DmodRuntimeError as e:
            raise e
        except Exception as e:
            msg = f"{self.__class__.__name__} failed due to {e.__class__.__name__}: {str(e)}"
            raise DmodRuntimeError(msg)

    @property
    def partial_realization_config(self) -> Optional[PartialRealizationConfig]:
        """
        The ::class:`PartialRealizationConfig` included with the original job request, if present.

        Returns
        -------
        Optional[PartialRealizationConfig]
            The ::class:`PartialRealizationConfig` included with the original job request, if present.
        """
        return self._job_request.formulation_configs


class CompositeConfigDataAdder(FromPartialRealizationConfigAdder):
    """
    An ::class:`InitialDataAdder` subtype for a dataset of the ``NGEN_JOB_COMPOSITE_CONFIG`` ::class:`DataFormat`.

    An instance expects the received ::class:`DataRequirement` passed during initialization to have a domain that
    includes `data_id` values of any/all datasets from which initial data is obtained or derived, per the composite
    config data format.  However, data can be supplied via other means; e.g., a ::class:`PartialRealizationConfig`
    embedded within the originating job request.
    """

    def __init__(self, requirement: DataRequirement, hydrofabric_id: str, *args, **kwargs):
        """

        Parameters
        ----------
        requirement : DataRequirement
            The requirement needing (i.e. to be fulfilled by) a composite config dataset to be created
        hydrofabric_id : str
            The hydrofabric id of the hydrofabric used by this job.
        args
        kwargs
        """
        super().__init__(*args, **kwargs)
        self._requirement: DataRequirement = requirement
        self._hydrofabric_id: str = hydrofabric_id

        self._source_datasets = None

    def _add_bmi_init_config_data(self):
        """
        Acquired and add initial BMI init config data to be added to dataset.

        Raises
        -------
        DmodRuntimeError
            Raised if not all BMI init config data items could be added successfully.
        """
        # Determine if we have a BMI init config dataset already or must generate configs using tools and the hydrofabric
        bmi_src_ds_list = [d for n, d in self.source_datasets.items() if d.data_format == DataFormat.BMI_CONFIG]
        # If there were source BMI config datasets, copy things from them
        if len(bmi_src_ds_list) > 0:
            # TODO: add threading support
            for ds in bmi_src_ds_list:
                if not self.copy_items(item_names=ds.manager.list_files(dataset_name=ds.name), other_dataset=ds):
                    raise DmodRuntimeError(f"{self.__class__.__name__} could not copy BMI configs from {ds.name}")

        # TODO: implement a proper check, based on request, of whether any config generation is appropriate
        should_generate_bmi_configs = len(bmi_src_ds_list) == 0

        if should_generate_bmi_configs:
            # TODO: support for this needs to be added later
            raise NotImplementedError(f"{self.__class__.__name__} doesn't yet support BMI init config auto generation")

    def _add_ngen_cal_config_data(self):
        """
        Acquired and add initial ngen-cal config data to be added to dataset.

        Raises
        -------
        DmodRuntimeError
            Raised if ngen-cal config data could not be added successfully.
        """
        src_ds_list = [d for n, d in self.source_datasets.items() if d.data_format == DataFormat.NGEN_CAL_CONFIG]
        if len(src_ds_list) == 1:
            src_ds = src_ds_list[0]
            if not self.copy_items(item_names=src_ds.manager.list_files(src_ds.name), other_dataset=src_ds):
                raise DmodRuntimeError(f"{self.__class__.__name__} could not copy ngen-cal config from {src_ds.name}")
        elif len(src_ds_list) > 1:
            raise DmodRuntimeError(f"{self.__class__.__name__} can't copy initial ngen-cal data from multiple sources")
        else:
            # TODO: implement properly once we can actually generate t-route configs
            raise NotImplementedError(f"{self.__class__.__name__} doesn't yet support ngen-cal config auto generation")

    def _add_realization_config_data(self):
        """
        Acquire initial realization config data and add to the dataset.

        Function branches depending on whether the originating request for the involved job contained a partial config
        containing base formulation configs.  If that is not the case, then we expect ::attribute:`_requirement` to
        have a domain that includes `data_id` values of all source datasets, per the composite config data format.

        Raises
        -------
        DmodRuntimeError
            Raised if realization config data could not be added successfully.
        """
        # TODO: add optimizations (perhaps in subtype)
        # TODO: add threading support

        original_domain = self._dataset_manager.datasets[self._dataset_name].data_domain

        # TODO: centrally define this, and probably somewhere else
        real_cfg_file_name = 'realization_config.json'

        # Branch based on if we have realization config dataset already or are building from formulations
        if self.partial_realization_config is not None:
            # In this case, we need to derive a dataset from formulations
            real_config: NgenRealization = self.build_realization_config_from_partial()
            if not self._dataset_manager.add_data(dataset_name=self._dataset_name, dest=real_cfg_file_name,
                                                  data=json.dumps(real_config.json()).encode(), domain=original_domain):
                raise DmodRuntimeError(f"{self.__class__.__name__} could not add built realization config")
        else:
            # In this case, we need to find the right existing realization config dataset and get data from it
            names = [n for n, d in self.source_datasets.items() if d.data_format == DataFormat.NGEN_REALIZATION_CONFIG]
            real_ds_name = names[0] if len(names) > 0 else None
            # Sanity check that we found an actual name
            if real_ds_name is None:
                raise DmodRuntimeError("Couldn't find source realization config in {}".format(self.__class__.__name__))
            # If we did, copy the realization config file to the new dataset
            if not self.copy_item(item_name=real_cfg_file_name, other_dataset=self.source_datasets[real_ds_name]):
                raise DmodRuntimeError(f"{self.__class__.__name__} failed copy realization config from {real_ds_name}")

    def _add_troute_config_data(self):
        """
        Acquired and add initial t-route routing config data to be added to dataset.

        Raises
        -------
        DmodRuntimeError
            Raised if t-route config data could not be added successfully.
        """
        src_ds_list = [d for n, d in self.source_datasets.items() if d.data_format == DataFormat.T_ROUTE_CONFIG]
        if len(src_ds_list) == 1:
            src_ds = src_ds_list[0]
            if not self.copy_items(item_names=src_ds.manager.list_files(src_ds.name), other_dataset=src_ds):
                raise DmodRuntimeError(f"{self.__class__.__name__} could not copy t-route config from {src_ds.name}")
        elif len(src_ds_list) > 1:
            raise DmodRuntimeError(f"{self.__class__.__name__} can't copy initial t-route data from multiple sources")
        else:
            # TODO: implement properly once we can actually generate t-route configs
            raise NotImplementedError(f"{self.__class__.__name__} doesn't yet support t-route config auto generation")

    def add_initial_data(self):
        """
        Assemble and add the initial data.

        Raises
        -------
        DmodRuntimeError
            Raised when initial data could not be assembled and/or added successfully to the dataset.
        """
        # TODO: add threading support

        # A composite config will always need these items, so we can immediately add them
        self._add_realization_config_data()
        self._add_bmi_init_config_data()

        # However, these two things may not be necessary, depending on the job
        if self._job_request.request_body.t_route_config_data_id is not None:
            self._add_troute_config_data()

        if isinstance(self._job_request, NgenCalibrationRequest):
            self._add_ngen_cal_config_data()

    def copy_item(self, item_name: str, other_dataset: Dataset, dest_path: Optional[str] = None) -> bool:
        """
        Copy a data item that already exists in some other dataset.

        Parameters
        ----------
        item_name : str
            The data item name.
        other_dataset : Dataset
            The source dataset containing the item already.
        dest_path : Optional[str]
            An optional item name when adding to the new dataset, if something other than `item_name`.

        Returns
        -------
        bool
            Whether the copy was successful.

        See Also
        -------
        copy_items
        """
        # TODO: when optimizations are added, might look at really keeping this with its own implementation
        return self.copy_items(item_names=[item_name], other_dataset=other_dataset,
                               dest_names=None if dest_path is None else {item_name: dest_path})

    def copy_items(self, item_names: List[str], other_dataset: Dataset, dest_names: Optional[Dict[str, str]] = None):
        """
        Copy data items that already exists in some other dataset.

        Parameters
        ----------
        item_names : List[str]
            The data item names.
        other_dataset : Dataset
            The source dataset containing the items already.
        dest_names : Optional[Dict[str, str]]
            An optional mapping of exiting item name to new, destination item name within the new dataset, if not simply
            the name of the existing item (even if not ``None``, not required to map all items from ``item_names``).

        Returns
        -------
        bool
            Whether the copy was successful.
        """
        original_domain = self._dataset_manager.datasets[self._dataset_name].data_domain

        if dest_names is None:
            dest_names = dict()

        # TODO: add optimizations later for this in cases when other_dataset uses the same data manager
        for item_name in item_names:
            # Immediately stop and return False if anything doesn't work properly
            if not self._dataset_manager.add_data(dataset_name=self._dataset_name,
                                                  dest=dest_names.get(item_name, item_name),
                                                  data=other_dataset.manager.get_data(dataset_name=other_dataset.name,
                                                                                      item_name=item_name),
                                                  domain=original_domain):
                return False
        # If we complete the loop, everything must have been successful
        return True

    @property
    def source_datasets(self) -> Dict[str, Dataset]:
        """
        Datasets that are sources of data that make up the initial data this instance will add, keyed by name.

        An instance expects the received ::class:`DataRequirement` passed during initialization to have a domain that
        includes `data_id` values of any/all datasets from which initial data is obtained or derived, per the composite
        config data format. The corresponding source datasets are made accessible via this property.

        Property lazily initializes and must communicate with **all** dataset managers to search for ::class:`Dataset`
        objects for the collection.

        Returns
        -------
        Dict[str, Dataset]
            Datasets that are sources of data that make up the initial data this instance will add, keyed by name.
        """
        if self._source_datasets is None:
            self._source_datasets: Dict[str, Dataset] = {}
            try:
                for ds_id in self._requirement.domain.discrete_restrictions[StandardDatasetIndex.COMPOSITE_SOURCE_ID].values:
                    manager = [m for _, m in self._managers.managers() if ds_id in m.datasets][0]
                    self._source_datasets[ds_id] = manager.datasets[ds_id]
            except Exception as e:
                msg = "Failed to find source datasets and managers initializing {} ({}: {})"
                raise DmodRuntimeError(msg.format(self.__class__.__name__, e.__class__.__name__, str(e)))
        return self._source_datasets


class DataServiceBmiInitConfigGenerator(BmiInitConfigAutoGenerator):
    """
    Convenience extension of :class:`BmiInitConfigAutoGenerator` that can accept base data as :class:`Dataset` objects.
    """

    def __init__(self,
                 hydrofabric_dataset: Dataset,
                 hydrofabric_geopackage_file_name: str,
                 hydrofabric_model_attributes_file_name: str,
                 realization_config_dataset: Dataset,
                 realization_cfg_file_name: str,
                 noah_owp_params_dir: Optional[Union[str, Path]] = None,
                 catchment_subset: Optional[Set[str]] = None):
        """
        Initialize an instance using datasets (and certain specific metadata) for hydrofabric and realization config.

        Parameters
        ----------
        hydrofabric_dataset
            The dataset for the hydrofabric used for generation.
        hydrofabric_geopackage_file_name
            The name of the primary hydrofabric geopackage file within the hydrofabric dataset.
        hydrofabric_model_attributes_file_name
            The name of the primary hydrofabric model attributes file within the hydrofabric dataset.
        realization_config_dataset
            The dataset for the ngen realization config use for generation.
        realization_cfg_file_name
            The name of the main realization config file within its dataset.
        noah_owp_params_dir
            An optional path to a directory containing Noah-OWP-modular parameter data, if Noah-OWP-modular configs are
            to be generated.
        catchment_subset
            An optional subset of catchments for which to generate BMI init configs, instead of all those having
            formulations implicitly (i.e., via the global formulation) or explicitly within the realization config.
        """
        def load_from_dataset(ds: Dataset, item_name: str) -> bytes:
            return ds.manager.get_data(dataset_name=ds.name, item_name=item_name)

        realization: NgenRealization = NgenRealization.parse_raw(
            load_from_dataset(ds=realization_config_dataset, item_name=realization_cfg_file_name))

        hf: gpd.GeoDataFrame = gpd.read_file(
            io.BytesIO(load_from_dataset(ds=hydrofabric_dataset, item_name=hydrofabric_geopackage_file_name)),
            layer="divides")

        attrs_data: pd.DataFrame = pd.read_parquet(
            io.BytesIO(load_from_dataset(ds=hydrofabric_dataset, item_name=hydrofabric_model_attributes_file_name)))

        super().__init__(ngen_realization=realization,
                         hydrofabric_data=hf,
                         hydrofabric_model_attributes=attrs_data,
                         noah_owp_params_dir=noah_owp_params_dir,
                         catchment_subset=catchment_subset)


class BmiAutoGenerationAdder(InitialDataAdder):

    def __init__(self, dataset_name: str, dataset_manager: DatasetManager, bmi_generator: BmiInitConfigAutoGenerator,
                 **kwargs):
        super().__init__(dataset_name=dataset_name, dataset_manager=dataset_manager, **kwargs)
        self._bmi_generator: BmiInitConfigAutoGenerator = bmi_generator

    @classmethod
    def _serialize(cls, config_model: BaseModel) -> bytes:
        if isinstance(config_model, IniSerializer):
            return config_model.to_ini_str().encode()
        elif isinstance(config_model, JsonSerializer):
            return config_model.to_json_str().encode()
        elif isinstance(config_model, NamelistSerializer):
            return config_model.to_namelist_str().encode()
        elif isinstance(config_model, TomlSerializer):
            return config_model.to_toml_str().encode()
        elif isinstance(config_model, YamlSerializer):
            return config_model.to_yaml_str().encode()
        elif isinstance(config_model, BaseModel):
            return config_model.json().encode()

        raise RuntimeError(f"{cls.__name__} can't serialize config model of type '{config_model.__class__.__name__}'")

    def add_initial_data(self):
        """
        Generate the BMI init configs and add to the dataset as the initial data.

        Raises
        -------
        DmodRuntimeError
            Raised when initial data could not be assembled and/or added successfully to the dataset.
        """
        dataset: Dataset = self._dataset_manager.datasets[self._dataset_name]

        # We should be able to get away with just maintaining the same domain at this stage for this type of data
        # Supplying this to add_data() eventually gets to the merge stage, where equal domains just do nothing
        initial_domain = dataset.data_domain

        # Write all files, then send all at once to add_data to potentially take advantage of optimizations
        # Get temp directory to write to
        with tempfile.TemporaryDirectory() as temp_dir_name:
            self._bmi_generator.write_configs(output_dir=temp_dir_name)
            # Pass everything to add_data() at once and hope for implementation-specific optimizations
            if not self._dataset_manager.add_data(dataset_name=self._dataset_name, dest='', source=temp_dir_name,
                                                  domain=initial_domain):
                raise DmodRuntimeError(f"{self.__class__.__name__} failed to add generated BMI init configs")
