import logging
import re

from .dataset_manager_collection import DatasetManagerCollection
from .initial_data_adder_impl import (BmiAutoGenerationAdder, CompositeConfigDataAdder,
                                      DataServiceBmiInitConfigGenerator, FromPartialRealizationConfigAdder)
from dmod.communication import AbstractNgenRequest
from dmod.communication.maas_request.ngen.partial_realization_config import PartialRealizationConfig
from dmod.core.meta_data import (DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction,
                                 StandardDatasetIndex)
from dmod.core.exception import DmodRuntimeError
from dmod.core.dataset import Dataset, DatasetType
from dmod.scheduler.job import Job, JobExecStep
from typing import List, Optional, Tuple


class DataDeriveUtil:
    """
    Utility class used by main ``dataservice`` manager for deriving new datasets and data.

    A package-internal utility class, intended for use with the main service manager class for this package.  It
    encapsulates behavior relating to deriving new, non-empty ::class:`Dataset` instances from existing data.  Data can
    potentially be either from existing ::class:`Dataset` or other data sources, such as a UI-generated partial
    realization config.

    The type provides functions for both actually deriving a new ::class:`Dataset` and for testing whether it is
    possible to derive a new ::class:`Dataset` to satisfy a supplied ::class:`DataRequirement`.
    """

    @staticmethod
    def find_hydrofabric_files(dataset: Dataset) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the hydrofabric geopackage and model attributes data files for a geopackage hydrofabric datasets.

        The main hydrofabric geopackage file should be the only file with a ".gpkg" extension.

        The model attribute file will be named `<region/vpu>_model_attributes.parquet`, `model_attributes.parquet`, or
        `<region/vpu>.parquet`, where `<region/vpu>` is something like `conus` or `nextgen_01`.

        Parameters
        ----------
        dataset: Dataset
            The hydrofabric dataset.

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            The name of the geopackage file and the attributes file, if each can be found.

        See Also
        --------
        _can_derive_bmi_configs
        _derive_bmi_init_config_dataset
        """
        if dataset.data_format != DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2:
            return None, None
        if dataset.manager is None:
            return None, None

        # Survey for the geopackage file and any parquet files (the attributes file will be one of the latter)
        parquet_files = []
        gpkg_file = None
        for item in dataset.manager.list_files(dataset.name):
            if item[-5:].lower() == ".gpkg":
                assert gpkg_file is None
                gpkg_file = item
            # If we have a parquet file ...
            elif item[-8:].lower() == ".parquet":
                parquet_files.append(item)

        # If we didn't find the geopackage file, something is up here, so don't proceed further
        if gpkg_file is None:
            logging.warning(f"Failed to find geopackage file searching for attributes file in dataset {dataset.name}")
            return None, None

        # Figure out the region, which we'll need to determine what the model attributes file name is
        vpu_match = re.match(".*(nextgen_\d+).gpkg", gpkg_file.lower())
        if vpu_match:
            region = vpu_match.groups()[0]
        elif "conus" in gpkg_file.lower():
            region = "conus"
        else:
            logging.warning(f"Failed to parse region from hydrofabric file {gpkg_file} of dataset {dataset.name}")
            return gpkg_file, None

        for item in parquet_files:
            if region == "conus" and (item == "conus_model_attributes.parquet" or item == "model_attributes.parquet"):
                return gpkg_file, item
            elif item == f"{region}.parquet":
                return gpkg_file, item
        return gpkg_file, None

    @staticmethod
    def get_fulfilling_dataset_name(job: Job, data_format: DataFormat) -> Optional[str]:
        """
        Get the name of the dataset fulfilling the requirement for this job with the given format.

        Get the name of the dataset fulfilling this job's data requirement that is associated with the supplied data
        format, if the job has exactly one such requirement.

        This function is useful for getting hydrofabric or realization config datasets, which are sometimes needed when
        deriving datasets of other types.

        Parameters
        ----------
        job: Job
            The job of interest.
        data_format: DataFormat
            The data format of the dataset of interest.

        Returns
        -------
        Optional[str]
            The name of the hydrofabric dataset fulfilling the related data requirement for this job, or ``None``.
        """
        hf_req = [r for r in job.data_requirements if r.domain.data_format == data_format]
        assert len(hf_req) != 0, f"Can't extract dataset name from job {job.job_id!s} with no {data_format.name} requirements"
        assert len(hf_req) == 1, f"Can't extract dataset name from job {job.job_id!s} with multiple {data_format.name} requirements"
        return hf_req[0].fulfilled_by if len(hf_req) == 1 else None

    def __init__(self, dataset_manager_collection: DatasetManagerCollection, noah_owp_params_dir: Optional[str] = None):
        self._managers: DatasetManagerCollection = dataset_manager_collection
        # TODO: (later) this might eventually need to be in a specialized dataset
        self._noah_owp_params_dir: Optional[str] = noah_owp_params_dir

    def _apply_dataset_to_requirement(self, dataset: Dataset, requirement: DataRequirement, job: Job):
        """
        Set ::attribute:`DataRequirement.fulfilled_access_at` and ::attribute:`DataRequirement.fulfilled_by`.

        Update the provided requirement's ::attribute:`DataRequirement.fulfilled_access_at` and
        ::attribute:`DataRequirement.fulfilled_by` attributes to associate the requirement with the provided dataset.
        The dataset is assume to have already been determined as satisfactory to fulfill the given requirement.

        Parameters
        ----------
        dataset : Dataset
            The dataset that fulfills the given requirement.
        requirement : DataRequirement
            The requirement fulfilled by the given dataset.
        job : Job
            The job owning the given requirement, which is needed for determining the appropriate value to use for
            :attribute:`DataRequirement.fulfilled_access_at`

        See Also
        -------
        _determine_access_location
        """
        #################################################################################
        # It is important that `fulfilled_access_at` is set first (or at least that the #
        # _determine_access_location function is called first) to ensure `fulfilled_by  #
        # isn't set if something with `fulfilled_access_at` goes wrong.                 #
        #################################################################################
        requirement.fulfilled_access_at = self._determine_access_location(dataset, job)
        #################################################################################
        requirement.fulfilled_by = dataset.name

    def _can_derive_bmi_configs(self, requirement: DataRequirement, job: Job) -> bool:
        """
        Determine whether a ``BMI_CONFIG`` :class:`DataFormat` dataset can be derived to fulfill this job requirement.

        Parameters
        ----------
        requirement: DataRequirement
            The requirement in question, for which a generated BMI init config dataset is needed.
        job: Job
            The job to which ``requirement`` belongs, which also is associated with other requirements and datasets that
            must be available for BMI init config generation.

        Notes
        -----
        See the :class:`DataServiceBmiInitConfigGenerator` and :class:`BmiInitConfigAutoGenerator` classes for what is
        necessary to derive/generate BMI init configs.

        Returns
        -------
        bool
            Whether a ``BMI_CONFIG`` :class:`DataFormat` dataset can be derived to fulfill the job requirement.
        """
        if requirement.category != DataCategory.CONFIG:
            return False
        elif requirement.domain.data_format != DataFormat.BMI_CONFIG:
            return False
        # Make sure we have a hydrofabric dataset, and that it is geopackage format
        hf_ds = self._managers.known_datasets().get(
            self.get_fulfilling_dataset_name(job=job, data_format=DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2))
        if not isinstance(hf_ds, Dataset) or hf_ds.data_format != DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2:
            return False
        # Also ensure there are a valid hydrofabric data and attributes file in the dataset for use with generation
        hf_gpkg_file, attributes_file = self.find_hydrofabric_files(dataset=hf_ds)
        if hf_gpkg_file is None or attributes_file is None:
            return False
        # Finally, make sure we have a realization config dataset
        real_cfg_ds = self._managers.known_datasets().get(
            self.get_fulfilling_dataset_name(job=job, data_format=DataFormat.NGEN_REALIZATION_CONFIG))
        if not isinstance(real_cfg_ds, Dataset) or real_cfg_ds.data_format != DataFormat.NGEN_REALIZATION_CONFIG:
            return False
        # TODO: (later) expand domain of realization dataset to include the set of used BMI module names to compare with
        #  what is currently supported for auto-generation
        # TODO: (later) also check to make sure that there aren't explicitly declared catchments in the realization
        #  config not covered by the hydrofabric (though this is a problem that perhaps should be caught elsewhere)
        # If we weren't missing anything required ...
        return True

    def _derive_bmi_init_config_dataset(self, requirement: DataRequirement, job: Job):
        """
        Derive and apply a new BMI init config dataset for this requirement.

        Parameters
        ----------
        requirement: DataRequirement
            The requirement needing the new dataset in order to be fulfilled.
        job: Job
            The job possessing the requirement.
        """
        # Also construct a name for the dataset we are generating, based on the job
        ds_name = "job-{}-bmi-init-config".format(job.job_id)

        # TODO: (later) more intelligently determine type
        ds_type = DatasetType.OBJECT_STORE
        ds_mgr = self._managers.manager(ds_type)

        hf_ds_name = self.get_fulfilling_dataset_name(job=job, data_format=DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2)
        hydrofabric_ds = self._managers.known_datasets()[hf_ds_name]
        real_cfg_ds_name = self.get_fulfilling_dataset_name(job=job, data_format=DataFormat.NGEN_REALIZATION_CONFIG)
        realization_cfg_ds = self._managers.known_datasets()[real_cfg_ds_name]

        hf_gpkg_file, attributes_file = self.find_hydrofabric_files(dataset=hydrofabric_ds)

        generator = DataServiceBmiInitConfigGenerator(hydrofabric_dataset=hydrofabric_ds,
                                                      hydrofabric_geopackage_file_name=hf_gpkg_file,
                                                      hydrofabric_model_attributes_file_name=attributes_file,
                                                      realization_config_dataset=realization_cfg_ds,
                                                      realization_cfg_file_name="realization_config.json",
                                                      noah_owp_params_dir=self._noah_owp_params_dir)

        data_adder = BmiAutoGenerationAdder(dataset_name=ds_name, dataset_manager=ds_mgr, bmi_generator=generator)

        domain = DataDomain(data_format=DataFormat.BMI_CONFIG,
                            discrete_restrictions=[DiscreteRestriction(variable=StandardDatasetIndex.DATA_ID,
                                                                       values=[ds_name])])

        dataset: Dataset = ds_mgr.create_temporary(name=ds_name, category=DataCategory.CONFIG, domain=domain,
                                                   is_read_only=False, initial_data=data_adder)
        self._apply_dataset_to_requirement(dataset=dataset, requirement=requirement, job=job)

    async def _derive_composite_job_config(self, requirement: DataRequirement, job: Job):
        """
        Derive and link a ``DataFormat.NGEN_JOB_COMPOSITE_CONFIG`` dataset to fulfill the given job's given requirement.

        Derive a new composite config format dataset in order to fulfill the given requirement.  Then, update the
        requirement to note that it is fulfilled by the new dataset.

        Parameters
        ----------
        requirement : DataRequirement
            The requirement needing a dataset to be created in order to be fulfilled.
        job : Job
            The job "owning" the relevant requirement.
        """
        # First, determine appropriate hydrofabric
        restricts = [r for i, r in requirement.domain.discrete_restrictions if i == StandardDatasetIndex.HYDROFABRIC_ID]
        if len(restricts) != 1:
            msg = "Cannot derive composite config for job {} requirement that has no Hydrofabric id defined"
            raise DmodRuntimeError(msg.format(job.job_id))
        # TODO: (later) consider if we need to account (as error or otherwise) for multiple hydrofabric ids here
        hydrofabric_id = restricts[0].values[0]

        # Also construct a name for the dataset we are generating, based on the job
        ds_name = "job-{}-composite-config".format(job.job_id)

        # Build a modified domain, based on the requirement, but with any name/data_id restriction removed
        req_domain = requirement.domain
        continuous_restricts = [r for idx, r in req_domain.continuous_restrictions.items()]
        # Leave out dataset's name/data_id restriction, as it's unnecessary here, and just use None if nothing else
        discrete_restricts = [r for idx, r in req_domain.discrete_restrictions if idx != StandardDatasetIndex.DATA_ID]
        if len(discrete_restricts) == 0:
            discrete_restricts = None
        domain = DataDomain(data_format=req_domain.data_format, continuous_restrictions=continuous_restricts,
                            discrete_restrictions=discrete_restricts)

        # TODO: (later) more intelligently determine type
        ds_type = DatasetType.OBJECT_STORE
        manager = self._managers.manager(ds_type)
        data_adder = CompositeConfigDataAdder(requirement=requirement, job=job, hydrofabric_id=hydrofabric_id,
                                              dataset_manager_collection=self._managers, dataset_name=ds_name,
                                              dataset_manager=manager)
        dataset: Dataset = manager.create_temporary(name=ds_name, category=DataCategory.CONFIG, domain=domain,
                                                    is_read_only=False, initial_data=data_adder)

        self._apply_dataset_to_requirement(dataset=dataset, requirement=requirement, job=job)

    def _derive_realization_config_from_formulations(self, requirement: DataRequirement, job: Job):
        """
        Derive a new realization config dataset for this requirement from the formulations within the job.

        Parameters
        ----------
        requirement
        job
        """
        # TODO: (later) more intelligently determine type
        ds_type = DatasetType.OBJECT_STORE
        ds_name = requirement.domain.discrete_restrictions[StandardDatasetIndex.DATA_ID].values[0]
        ds_mgr = self._managers.manager(ds_type)

        initial_data = FromPartialRealizationConfigAdder(job=job, dataset_manager_collection=self._managers,
                                                         dataset_name=ds_name, dataset_manager=ds_mgr)

        # Build a modified domain, based on the requirement, but with any name/data_id restriction removed
        req_domain = requirement.domain
        continuous_restricts = [r for idx, r in req_domain.continuous_restrictions.items()]
        # Leave out dataset's name/data_id restriction, as it's unnecessary here, and just use None if nothing else
        discrete_restricts = [r for idx, r in req_domain.discrete_restrictions if idx != StandardDatasetIndex.DATA_ID]
        if len(discrete_restricts) == 0:
            discrete_restricts = None
        domain = DataDomain(data_format=req_domain.data_format, continuous_restrictions=continuous_restricts,
                            discrete_restrictions=discrete_restricts)

        dataset: Dataset = self._managers.manager(ds_type).create_temporary(name=ds_name,
                                                                             category=DataCategory.CONFIG,
                                                                             domain=domain,
                                                                             is_read_only=False,
                                                                             initial_data=initial_data)

        self._apply_dataset_to_requirement(dataset=dataset, requirement=requirement, job=job)

    def _determine_access_location(self, dataset: Dataset, job: Job) -> str:
        """
        Get the correct access location string for a given dataset, in the context of the provided job.

        Get the correct access location string for a given dataset and job.  This is a string value suitable for use to
        set the ::attribute:`DataRequirement.fulfilled_access_at` for a ::class:`DataRequirement` for this ::class:`Job`
        that is satisfied by ``dataset``.

        Note that the access location value is returned, but no requirement for the provided job is modified by this
        function.


        Parameters
        ----------
        dataset : Dataset
            A dataset that fulfills one of the requirements of the provide job.
        job : Job
            A job that needs the appropriate value for the ::attribute:`DataRequirement.fulfilled_access_at` property of
            one of said job's :class:`DataRequirement`s, where this requirement is fulfilled by ``dataset``.

        Returns
        -------
        str
            The appropriate ``fulfilled_access_at`` value.
        """
        # TODO: (later) in the future, whether the job is running via Docker needs to be checked
        # TODO: (later) also, whatever is done here needs to align with what is done within perform_checks_for_job,
        #  when setting the fulfilled_access_at for the DataRequirement
        is_job_run_in_docker = True

        if is_job_run_in_docker:
            return dataset.docker_mount
        else:
            msg = "Could not determine proper access location for new dataset of type {} by non-Docker job {}."
            raise DmodRuntimeError(msg.format(dataset.__class__.__name__, job.job_id))

    async def async_can_dataset_be_derived(self, requirement: DataRequirement, job: Optional[Job] = None) -> bool:
        """
        Asynchronously determine if a dataset can be derived from existing datasets to fulfill this requirement.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirement : DataRequirement
            The requirement that needs to be fulfilled.
        job : Optional[Job]
            The job having the given requirement.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill these requirement.

        See Also
        -------
        ::method:`can_dataset_be_derived`
        """
        return self.can_dataset_be_derived(requirement=requirement, job=job)

    def can_dataset_be_derived(self, requirement: DataRequirement, job: Optional[Job] = None) -> bool:
        """
        Determine if it is possible for a dataset to be derived from existing datasets to fulfill these requirements.

        Parameters
        ----------
        requirement : DataRequirement
            The requirement that needs to be fulfilled.
        job : Optional[Job]
            The job having the given requirement.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill these requirements.
        """
        # Account for partial configs included in request that enable building realization config on the fly
        if job is not None and self.can_derive_realization_from_formulations(requirement=requirement, job=job):
            return True
        else:
            return job is not None and self._can_derive_bmi_configs(requirement=requirement, job=job)

    def can_derive_realization_from_formulations(self, requirement: DataRequirement, job: Job) -> bool:
        """
        Test if possible to derive a satisfactory realization config dataset from the originating request.

        Test whether it is possible to derive a realization config that will satisfy this requirement, using a
        formulation configuration contain within the original request message for this job.

        Because this deals specifically with NextGen realization config datasets, a few conditions will immediately
        result in a return of ``False``:
            - a requirement category value other than ``CONFIG``
            - a requirement domain data format value other than ``NGEN_REALIZATION_CONFIG``
            - an originating request message for the job that is not a ::class:`NGENRequest`

        Parameters
        ----------
        requirement : DataRequirement
            The requirement for which the capability to derive a realization config needs to be determined.
        job : Job
            The job having the given requirement.

        Returns
        -------
        bool
            Whether deriving an appropriate realization configuration is possible.
        """
        if requirement.category != DataCategory.CONFIG:
            return False
        elif requirement.domain.data_format != DataFormat.NGEN_REALIZATION_CONFIG:
            return False

        request = job.model_request
        return (isinstance(request, AbstractNgenRequest) and request.is_intelligent_request
                and isinstance(request.formulation_configs, PartialRealizationConfig))

    async def derive_datasets(self, job: Job) -> List[DataRequirement]:
        """
        Derive any datasets as required for the given job awaiting its data.

        Job is expected to be in the ``AWAITING_DATA`` status step.  If it is not, no datasets are derived, exception
        is thrown.  This implies that the job has proceeded through the service's checks in the ``AWAITING_DATA_CHECK``
        step.  This means that all the job's data requirements hav been determined to be "fulfillable," and thus any
        requirements that are still set to ``None`` must be "derivable" according to :method:`can_dataset_be_derived`.

        If in the right status, but any initially unfulfilled requirements of the job cannot have a dataset successfully
        derived, a ::class:`DmodRuntimeError` is raised.

        Parameters
        ----------
        job : Job
            The job having ::class:`DataRequirement` objects for which fulfilling datasets should be derived.

        Returns
        -------
        List[DataRequirement]
            A list of the given job's data requirements for a which a fulfilling dataset was derived and associated.

        Raises
        -------
        DmodRuntimeError
            Raised if the job has the wrong status, or if the job with the correct status has an initially unfulfilled
            requirement for which a satisfactory dataset can not be derived by this function.

        See Also
        --------
        DatasetInqueryUtil.can_be_fulfilled
        async_can_dataset_be_derived
        can_dataset_be_derived
        """
        # Only do something if the job has the right status
        if job.status_step != JobExecStep.AWAITING_DATA:
            msg = "Cannot attempt to derive datasets with job status step of {}".format(job.status_step.name)
            logging.error(msg)
            raise DmodRuntimeError(msg)

        results = []

        # TODO: #needs_issue Make sure logic is in place to make derived datasets temporary (unless somehow specified to
        #  not be temporary) and have temporary datasets cleaned up by service periodically
        # TODO: #needs_issue Also make sure that temporary datasets have their expire time updated if they are used
        #  again for something
        for req in (r for r in job.data_requirements if r.fulfilled_by is None):
            # **********************************************************************************************************
            # *** TODO: if/when deriving forcing datasets is supported, make sure this is done before config datasets
            # **********************************************************************************************************
            # TODO: figure out reason for previous todo comment, "when generating BMI datasets is supported, make sure
            #  it's done before realization configs," which isn't actually possible since generating BMI configs
            #  REQUIRES a realization config
            # Derive realization config datasets from formulations in message body when necessary
            if req.category == DataCategory.CONFIG and req.domain.data_format == DataFormat.NGEN_REALIZATION_CONFIG:
                self._derive_realization_config_from_formulations(requirement=req, job=job)
                results.append(req)
            # Derive BMI init configs from hydrofabric data and realization config
            elif req.category == DataCategory.CONFIG and req.domain.data_format == DataFormat.BMI_CONFIG:
                self._derive_bmi_init_config_dataset(requirement=req, job=job)
                results.append(req)
            # Derive composite dataset with all config details need for executing job
            elif req.category == DataCategory.CONFIG and req.domain.data_format == DataFormat.NGEN_JOB_COMPOSITE_CONFIG:
                await self._derive_composite_job_config(requirement=req, job=job)
                results.append(req)
            # The above are the only supported derivations, so blow up here if there was something else
            else:
                msg_template = "Unsupported requirement dataset derivation for job {} (requirement: {})"
                raise DmodRuntimeError(msg_template.format(job.job_id, str(req)))
        return results
