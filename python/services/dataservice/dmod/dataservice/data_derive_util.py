import json
import logging

from dmod.communication import AbstractNgenRequest, NGENRequest
from dmod.communication.maas_request.ngen.partial_realization_config import PartialRealizationConfig
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, StandardDatasetIndex
from dmod.core.exception import DmodRuntimeError
from dmod.core.dataset import Dataset, DatasetManager, DatasetType
from dmod.scheduler.job import Job, JobExecStep
from ngen.config.configurations import Forcing, Time
from ngen.config.realization import NgenRealization, Realization
from typing import Dict, List, Optional


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

    def __init__(self, data_mgrs_by_ds_type: Dict[DatasetType, DatasetManager]):
        self._all_data_managers: Dict[DatasetType, DatasetManager] = data_mgrs_by_ds_type

    def _build_forcing_config_for_realization(self, request: AbstractNgenRequest) -> Forcing:
        """
        Build a ::class:`Forcing` config object from to satisfy requirements of this request.

        Function builds a ::class:`Forcing` config object as a part of the steps to create a ngen realization config
        for the given request.  It is typically expected that the provided request will include a partial realization
        config object that includes certain details.

        Parameters
        ----------
        request: AbstractNgenRequest
            An AbstractNgenRequest request that needs a realization config generated, and as part of that, a forcing
            config.

        Returns
        -------
        Forcing
            Forcing config object to be used in building a ngen realization config to satisfy this request.
        """
        forcing_cfg_params = dict()

        # Get the correct forcing dataset from associated requirement
        # TODO: double check that this is being added when we do data checks
        forcing_req = [r for r in request.data_requirements if r.category == DataCategory.FORCING][0]
        forcing_dataset_name = forcing_req.fulfilled_by
        forcing_dataset = self._get_known_datasets().get(forcing_dataset_name)

        # Figure out the correct provider type from the dataset format
        # TODO: this may not be the right way to do this to instantiate the object directly (i.e., not through JSON)
        if forcing_dataset.data_format == DataFormat.NETCDF_FORCING_CANONICAL:
            forcing_cfg_params['provider'] = 'NetCDF'
        elif forcing_dataset.data_format == DataFormat.AORC_CSV:
            forcing_cfg_params['provider'] = 'CsvPerFeature'

        # TODO: (#needs_issue) introduce logic to examine forcing dataset and intelligently assess what the file
        #  name(s)/pattern(s) should be if they aren't explicitly provided

        if request.formulation_configs is not None and request.formulation_configs.forcing_file_pattern is not None:
            forcing_cfg_params['file_pattern'] = request.formulation_configs.forcing_file_pattern

        # Finally, produce the right path
        # TODO: these come from scheduler.py; may need to centralize somehow
        forcing_cfg_params['path'] = '/dmod/datasets/'
        if request.formulation_configs is not None and request.formulation_configs.is_env_workaround:
            forcing_cfg_params['path'] += 'from_env'
        else:
            forcing_cfg_params['path'] += '{}/{}/'.format(DataCategory.FORCING.name.lower(), forcing_dataset_name)

        if request.formulation_configs is not None and request.formulation_configs.forcing_file_name is not None:
            forcing_cfg_params['path'] += request.formulation_configs.forcing_file_name

        return Forcing(**forcing_cfg_params)

    def _build_ngen_realization_config_from_request(self, request: AbstractNgenRequest, job: Job) -> NgenRealization:
        """
        Build a ngen realization config object from current service state and partial config within the job request.

        Parameters
        ----------
        request: NGENRequest
            The original request initiating the related NextGen workflow job.
        job: Job
            The NextGen job for which an explicit realization config needs to be built from implied details.

        Returns
        -------
        NgenRealization
            The built realization config.
        """
        params = dict()

        if request.formulation_configs.global_formulations is not None:
            params['global_config'] = Realization(formulations=request.formulation_configs.global_formulations,
                                                  forcing=self._build_forcing_config_for_realization(request))

        params['time'] = Time(start_time=request.time_range.begin, end_time=request.time_range.end)

        if request.formulation_configs.routing_config is not None:
            params['routing'] = request.formulation_configs.routing_config

        if request.formulation_configs.catchment_formulations is not None:
            params['catchments'] = request.formulation_configs.catchment_formulations

        return NgenRealization(**params)

    def _derive_realization_config_from_formulations(self, requirement: DataRequirement, job: Job):
        """
        Derive a new realization config dataset for this requirement from the formulations within the job.

        Parameters
        ----------
        requirement
        job
        """
        request = job.model_request
        if isinstance(request, AbstractNgenRequest):
            # TODO: make sure that, once we are generating BMI init config datasets, the path details get provided as
            #  needed to this function when generating the realization config
            real_config_obj = self._build_ngen_realization_config_from_request(request=request, job=job)

            # Create a new dataset
            req_domain = requirement.domain
            ds_name = req_domain.discrete_restrictions[StandardDatasetIndex.DATA_ID].values[0]

            ds_cont_restricts = [r for idx, r in req_domain.continuous_restrictions.items()]

            # Leave out dataset's name/data_id restriction, as it's unnecessary here, and just use None if nothing else
            ds_d_restricts = [r for idx, r in req_domain.discrete_restrictions if idx != StandardDatasetIndex.DATA_ID]
            if len(ds_d_restricts) == 0:
                ds_d_restricts = None

            ds_domain = DataDomain(data_format=req_domain.data_format, continuous_restrictions=ds_cont_restricts,
                                   discrete_restrictions=ds_d_restricts)
            # TODO: (later) more intelligently determine type
            mgr = self._all_data_managers[DatasetType.OBJECT_STORE]
            dataset: Dataset = mgr.create(name=ds_name, is_read_only=False, category=DataCategory.CONFIG,
                                          domain=ds_domain)

            # TODO: (later) in the future, whether the job is running via Docker needs to be checked
            # TODO: (later) also, whatever is done here needs to align with what is done within perform_checks_for_job,
            #  when setting the fulfilled_access_at for the DataRequirement
            is_job_run_in_docker = True
            if is_job_run_in_docker:
                ds_access_at = dataset.docker_mount
            else:
                msg = "Could not determine proper access location for new dataset of type {} by non-Docker job {}."
                raise DmodRuntimeError(msg.format(dataset.__class__.__name__, job.job_id))

            # Upload the data from the config object to the new dataset
            result = mgr.add_data(dataset_name=ds_name, dest='realization_config.json',
                                  data=json.dumps(real_config_obj.json()).encode())
            if not result:
                msg_tmp = "Could not write data to new {} dataset {} being derived for job {}"
                raise DmodRuntimeError(msg_tmp.format(ds_domain.data_format.name, ds_name, job.job_id))

            # Update the requirement fulfilled_by and fulfilled_at to associate with the new dataset
            requirement.fulfilled_by = dataset.name
            requirement.fulfilled_access_at = ds_access_at
        else:
            msg = 'Bad job request type for {} when deriving realization config from formulations'.format(job.job_id)
            raise DmodRuntimeError(msg)

    def _get_known_datasets(self) -> Dict[str, Dataset]:
        """
        Get real-time mapping of all datasets known to this instance via its managers, in a map keyed by dataset name.

        This is implemented as a function, and not a property, since it is mutable and could change without this
        instance or even the service manager being directly notified.  As such, a new collection object is created and
        returned on every call.

        Returns
        -------
        Dict[str, Dataset]
            All datasets known to the service via its manager objects, in a map keyed by dataset name.
        """
        datasets = {}
        for _, manager in self._all_data_managers.items():
            datasets.update(manager.datasets)
        return datasets

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
            return False

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
        is thrown.

        If in the right status, but initially any unfulfilled requirements of the job cannot have a dataset successfully
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
            # *** TODO: when generating BMI datasets is supported, make sure it's done before realization configs
            # **********************************************************************************************************
            # Derive realization config datasets from formulations in message body when necessary
            if req.category == DataCategory.CONFIG and req.domain.data_format == DataFormat.NGEN_REALIZATION_CONFIG:
                self._derive_realization_config_from_formulations(requirement=req, job=job)
                results.append(req)
            # The above are the only supported derivations, so blow up here if there was something else
            else:
                msg_template = "Unsupported requirement dataset derivation for job {} (requirement: {})"
                raise DmodRuntimeError(msg_template.format(job.job_id, str(req)))
        return results