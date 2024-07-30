import asyncio
import json
import logging

import websockets
from pathlib import Path
from typing import List, Optional, Tuple, Union, Type
from websockets import WebSocketServerProtocol
from docker.errors import ContainerError
from dmod.communication import AbstractInitRequest, DatasetManagementMessage, DatasetManagementResponse, \
    InvalidMessageResponse, PartitionRequest, PartitionResponse, ManagementAction, WebSocketInterface
from dmod.communication.dataset_management_message import DatasetQuery, QueryType
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction, \
    StandardDatasetIndex
from dmod.core.exception import DmodRuntimeError
from dmod.core.dataset import Dataset
from dmod.externalrequests.maas_request_handlers import DataServiceClient
from dmod.modeldata.hydrofabric import HydrofabricFilesManager
from dmod.scheduler import SimpleDockerUtil
from dmod.scheduler.job import Job, JobExecStep, JobUtil
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class ServiceManager(HydrofabricFilesManager, WebSocketInterface):
    """
    Main service and communication manager class, implemented with WebSocketInterface.

    To perform partitioning, an instance will run a Docker container with the partitioning executable.  Because the
    executable expects to read input files and write to an output file, a Docker volume is mounted inside the
    container.

    It is supported for an instance to itself be run inside a container.  However, it must also be able to access the
    contents of the aforementioned Docker data volume, to create the partitioner input files and extract and return the
    partitioner's output to requesters.  As such, it is assumed that management of the volume is handled externally.
    An instance only requires the name of an already-existing volume and the volume's storage directory path.  This will
    be the volume mount target of the instance's container in cases when one exists, since the volume will need to have
    been mounted by that container also in order to provide access.
    """

    _PARSEABLE_REQUEST_TYPES = [PartitionRequest]
    """ Parseable request types, which are all authenticated ::class:`ExternalRequest` subtypes for this implementation. """

    @classmethod
    def get_parseable_request_types(cls) -> List[Type[AbstractInitRequest]]:
        """
        Get the ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.

        Returns
        -------
        List[Type[AbstractInitRequest]]
            The ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.
        """
        return cls._PARSEABLE_REQUEST_TYPES

    def __init__(self, image_name: str, hydrofabrics_dir: Union[str, Path], job_util: JobUtil,
                 data_client: DataServiceClient, *args, **kwargs):
        """
        Initialize with type-specific params and any user defined custom server config.

        Parameters
        ----------
        port
        image_name
        hydrofabrics_dir
        job_util
        data_client
        args
        kwargs

        Raises
        ----------
        docker.errors.NotFound
            Raised if the expected data volume does not exist.
        """
        self._job_util = job_util
        self._data_client = data_client
        self._image_name = image_name
        # TODO: probably need to check that image exists or can be pulled (and then actually pull)
        self._docker_util = SimpleDockerUtil()
        self._hydrofabrics_root_dir = hydrofabrics_dir if isinstance(hydrofabrics_dir, Path) else Path(hydrofabrics_dir)

        # TODO: reassess later if we really need to be a HydrofabricFilesManager
        super().__init__(*args, **kwargs)

        # Go ahead and lazy load the first one of these so it is cached
        #self.get_hydrofabric_uid(0)

    async def _async_create_new_partitioning_dataset(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Submit a request to the data service for creating a new, empty partitioning config dataset.

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            The new dataset's name and 'data_id' respectively, with ``None`` for both if creation failed.
        """
        # TODO: probably won't work ... needs domain
        dataset_name = 'partition-config-{}'.format(str(uuid4()))
        request = DatasetManagementMessage(action=ManagementAction.CREATE, dataset_name=dataset_name,
                                           category=DataCategory.CONFIG)
        response: DatasetManagementResponse = await self._data_client.async_make_request(request)
        return (dataset_name, response.data_id) if response.success else (None, None)

    async def _async_find_hydrofabric_dataset_name(self, data_id: str, uid: str) -> Tuple[Optional[str], Optional[DataFormat], Optional[str]]:
        """
        Query the data service for the name of the required hydrofabric dataset that fulfill the implied restrictions.

        The hydrofabric dataset must have the given 'data_id' and unique id, defined as constraints on its domain.

        Parameters
        ----------
        data_id : str
            The 'data_id' index value of the hydrofabric to find.
        uid : str
            The unique id of the hydrofabric to find.

        Returns
        -------
        Tuple[Optional[str], Optional[DataFormat], Optional[str]]
            Tuple containing:
                - name of hydrofabric dataset satisfying these restrictions, or ``None`` if one could not be found
                - the data format of hydrofabric dataset, or ``None`` if a dataset could not be found
                - the name of the geopackage file, if a ``NGEN_GEOPACKAGE_HYDROFABRIC_V2`` dataset, or ``None`` if
                  either a dataset could not be found **OR** the dataset is ``NGEN_GEOJSON_HYDROFABRIC``
        """
        # TODO: (later) need a way to select (or prioritize) data format from the partitioning request
        restrictions = [DiscreteRestriction(variable=StandardDatasetIndex.DATA_ID, values=[data_id]),
                        DiscreteRestriction(variable=StandardDatasetIndex.HYDROFABRIC_ID, values=[uid])]

        domain = DataDomain(data_format=DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2, discrete_restrictions=restrictions)
        data_request = DatasetManagementMessage(action=ManagementAction.SEARCH, category=DataCategory.HYDROFABRIC,
                                                domain=domain)
        response: DatasetManagementResponse = await self._data_client.async_make_request(data_request)

        if response.success:
            list_request = DatasetManagementMessage(action=ManagementAction.QUERY, dataset_name=response.dataset_name,
                                               query=DatasetQuery(query_type=QueryType.LIST_FILES))
            list_response = await self._data_client.async_make_request(list_request)
            gpkg_name = None
            for item in list_response.query_results.get('files', []) if response.success else []:
                if item[-5:].lower() == ".gpkg":
                    gpkg_name = item
                    break
            return response.dataset_name, DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2, gpkg_name

        # Otherwise, try geojson too, just to be safe
        domain = DataDomain(data_format=DataFormat.NGEN_GEOJSON_HYDROFABRIC, discrete_restrictions=restrictions)
        data_request = DatasetManagementMessage(action=ManagementAction.SEARCH, category=DataCategory.HYDROFABRIC,
                                                domain=domain)
        response: DatasetManagementResponse = await self._data_client.async_make_request(data_request)

        if response.success:
            return response.dataset_name, DataFormat.NGEN_GEOJSON_HYDROFABRIC, None
        else:
            return None, None, None

    async def _async_process_request(self, request: PartitionRequest) -> PartitionResponse:
        """
        Process a received request and return a response.

        Process a received request by attempting to run the partitioner via a Docker container.  Write partitioner input
        data from the request to the data volume first, then run the partitioner.  When successful, read the output and
        use in the created response object.

        When unsuccessful, include details on the error in the ``reason`` and ``message`` of the response.

        Parameters
        ----------
        request : PartitionRequest
            The incoming request for partitioning.

        Returns
        -------
        PartitionResponse
            The generated response based on success or failure.
        """
        try:

            hydrofabric_dataset_name, hf_data_format, file_name = await self._async_find_hydrofabric_dataset_name(
                request.hydrofabric_data_id, request.hydrofabric_uid)
            if not isinstance(hydrofabric_dataset_name, str):
                return PartitionResponse(success=False, reason='Could Not Find Hydrofabric Dataset')

            # TODO: (later) perhaps look at examining these and adapting to what's in the dataset (or request); for now,
            #  just use whatever the defaults are used when "None" is passed in
            if hf_data_format == DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2 and file_name:
                catchment_file_name = file_name
                nexus_file_name = file_name
            else:
                catchment_file_name = None
                nexus_file_name = None

            # Create a new dataset that is empty for the partitioning config
            partition_dataset_name, partition_dataset_data_id = await self._async_create_new_partitioning_dataset()
            if partition_dataset_name is None:
                return PartitionResponse(success=False, reason='Dataset Create Failed')

            # Run the partitioning execution container
            result, logs = self._execute_partitioner_container(num_partitions=request.num_partitions,
                                                               hydrofabric_dataset_name=hydrofabric_dataset_name,
                                                               partition_dataset_name=partition_dataset_name,
                                                               catchment_file_name=catchment_file_name,
                                                               nexus_file_name=nexus_file_name)

            # TODO: (later) get perhaps a more reflective response from the container run
            return PartitionResponse.factory_create(dataset_name=partition_dataset_name,
                                                    dataset_data_id=partition_dataset_data_id,
                                                    reason='Partitioning Complete')
        except RuntimeError as e:
            return PartitionResponse(success=False, reason=e.__cause__.__class__.__name__, message=str(e))

    def _execute_partitioner_container(self, num_partitions: int, hydrofabric_dataset_name: str,
                                       partition_dataset_name: str, catchment_file_name: Optional[str] = None,
                                       nexus_file_name: Optional[str] = None, nexus_id_subset_str: str = '',
                                       catchment_id_subset_str: str = '') -> Tuple[bool, Optional[bytes]]:
        """
        Execute the partitioner Docker container and executable.

        Execute the partitioner Docker container and executable.  This includes mounting the necessary datasets via
        s3fs prior to running the partitioning, where input and output data is accessed.  The container is run in a
        way so that this function does not return until the container does.

        The image selected is based on an init parameter and stored in a "private" attribute.

        Parameters
        ----------
        num_partitions : int
            The number of partitions to request of the partitioner.
        hydrofabric_dataset_name : str
            The name of the dataset containing the hydrofabric.
        partition_dataset_name : str
            The name of the dataset in which to save the partitioning config output.
        catchment_file_name : Optional[str]
            Basename of hydrofabric's catchment data file; note that a value of``None`` (which is the default) is
            replaced with 'catchment_data.geojson'.
        nexus_file_name : Optional[str]
            Basename of hydrofabric's nexus data file; note that a value of``None`` (which is the default) is
            replaced with 'nexus_data.geojson'.
        nexus_id_subset_str : str
            The comma separated string of the subset of nexuses to include in partitions, or empty string by default.
        catchment_id_subset_str : str
            The comma separated string of the subset of catchments to include in partitions, or empty string by default.

        Returns
        -------
        Tuple[bool, Optional[bytes]]
            Whether the run was successful and, if so, container logs.

        Raises
        -------
        RuntimeError
            Raised if execution fails, containing as a nested ``cause`` the encountered, more specific error/exception.
        """
        # If these two default settings are ever altered, make sure to reflect in the docstring also
        if catchment_file_name is None:
            catchment_file_name = 'catchment_data.geojson'
        if nexus_file_name is None:
            nexus_file_name = 'nexus_data.geojson'

        try:
            command = list()
            # Add the hydrofabric dataset
            command.append('--hydrofabric-dataset')
            command.append(hydrofabric_dataset_name)
            # Add the partition config output dataset
            command.append('--partition-dataset')
            command.append(partition_dataset_name)
            # Add the number of partitions
            command.append('--num-partitions')
            command.append(str(num_partitions))
            # Specify a catchment data file name
            command.append('--catchment-data-file')
            command.append(catchment_file_name)
            # Specify a custom nexus data file name
            command.append('--nexus-data-file')
            command.append(nexus_file_name)
            # Finally, specify catchment and/or nexus subsets
            command.append('--nexus-subset')
            command.append(nexus_id_subset_str)
            command.append('--catchment-subset')
            command.append(catchment_id_subset_str)

            return True, self._docker_util.run_container(image=self._image_name, command=command, remove=True)
        # This particular exception indicates container exits with a non-zero exit code
        except ContainerError as e:
            return False, None
        except Exception as e:
            msg = 'Could not successfully execute partitioner Docker container: {}'.format(str(e))
            raise RuntimeError(msg) from e

    async def _find_partition_dataset(self, job: Job) -> DatasetManagementResponse:
        """
        Attempt to find an existing, expected partitioning dataset based on the job's data requirements.

        When found, also update the applicable data requirements of the job, setting the ``fulfilled_by`` property to
        the found dataset's name.

        Parameters
        ----------
        job : Job
            The job in question.

        Returns
        -------
        DatasetManagementResponse
            Response to search for existing, expected partition config dataset.
        """
        reqs = [r for r in job.data_requirements if r.domain.data_format == DataFormat.NGEN_PARTITION_CONFIG]
        c_rests = [req.domain.continuous_restrictions[r] for req in reqs for r in req.domain.continuous_restrictions]
        d_rests = [req.domain.discrete_restrictions[r] for req in reqs for r in req.domain.discrete_restrictions]
        if len(reqs) == 0:
            reason = 'No Data Requirements For DataFormat'
            logging.info("Cannot query for satisfactory, existing partition dataset: {}".format(reason))
            return DatasetManagementResponse(action=ManagementAction.SEARCH, success=False, reason=reason)

        domain = DataDomain(data_format=DataFormat.NGEN_PARTITION_CONFIG, continuous_restrictions=c_rests,
                            discrete_restrictions=d_rests)
        request = DatasetManagementMessage(action=ManagementAction.SEARCH, category=DataCategory.CONFIG, domain=domain)
        logging.info("Querying for existing, satisfactory partition dataset for job {}".format(job.job_id))
        response: DatasetManagementResponse = await self._data_client.async_make_request(request)
        if response.success:
            logging.info("Existing partition dataset for {} found: {}".format(job.job_id, response.dataset_name))
            for r in reqs:
                r.fulfilled_by = response.dataset_name
        else:
            logging.info("No existing partition dataset for {} was found: ".format(job.job_id))
        return response

    def _find_required_hydrofabric_details(self, job: Job) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the given job's required hydrofabric's 'data_id' and unique id.

        Parameters
        ----------
        job : Job
            The job requiring a hydrofabric dataset, for which the details are needed.

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            Required hydrofabric dataset's 'data_id' and unique id respectively, or ``None`` for either if not found.
        """
        data_id = None
        uid = None

        # TODO: this suggests that domains may need to do something to prevent conflicting restrictions
        for requirement in [r for r in job.data_requirements if r.category == DataCategory.HYDROFABRIC]:
            for variable, restriction in requirement.domain.discrete_restrictions.items():
                if len(restriction.values) != 1:
                    continue
                elif variable == StandardDatasetIndex.DATA_ID:
                    data_id = restriction.values[0]
                    if uid is not None:
                        return data_id, uid
                elif variable == StandardDatasetIndex.HYDROFABRIC_ID:
                    uid = restriction.values[0]
                    if data_id is not None:
                        return data_id, uid
        return data_id, uid

    async def _generate_partition_config_dataset(self, job: Job) -> bool:
        """
        Generate a new partition config dataset for the given job, returning whether this was done successfully.

        Before actually creating a dataset, the function must obtain details on the dataset containing the hydrofabric
        to be partitioned.  If it cannot, a ::class:`DmodRuntimeError` is raised.

        After creating an empty dataset, a nested call is made to execute the container that runs the ngen partitioning
        executable to create and save a partitioning config in the dataset.  If this is successful, a new
        ::class:`DataRequirement` object is added to the parameter ::class:`Job` object to represent the job's need to
        use this new dataset.

        Parameters
        ----------
        job : Job
            A job requiring a partition config dataset.

        Returns
        -------
        bool
            Whether the generation process was successful.
        """
        logging.info("Attempting to generate partition config dataset for {}".format(job.job_id))

        err_msg = ' '.join(['{}', '{}'.format('for job {} awaiting partitioning.'.format(job.job_id))])

        # Find the hydrofabric dataset required for partitioning
        hy_data_id, hy_uid = self._find_required_hydrofabric_details(job)
        if hy_data_id is None or hy_uid is None:
            raise DmodRuntimeError(err_msg.format("Cannot get hydrofabric dataset details"))
        hydrofabric_ds_name, hf_format, gpkg_file = await self._async_find_hydrofabric_dataset_name(hy_data_id, hy_uid)
        if hydrofabric_ds_name is None:
            raise DmodRuntimeError(err_msg.format("Cannot find hydrofabric dataset name"))

        # Create a new partitioning dataset, and get back the name and data_id
        part_dataset_name, part_dataset_data_id = await self._async_create_new_partitioning_dataset()
        if part_dataset_name is None or part_dataset_data_id is None:
            raise DmodRuntimeError(err_msg.format("Cannot create new partition config dataset"))

        # Run the partitioning execution container
        # TODO: (later) doesn't account for whether we are dealing with gpkg or geojson
        result, logs = self._execute_partitioner_container(num_partitions=job.cpu_count,
                                                           hydrofabric_dataset_name=hydrofabric_ds_name,
                                                           partition_dataset_name=part_dataset_name,
                                                           catchment_file_name=gpkg_file,
                                                           nexus_file_name=gpkg_file)
        if result:
            logging.info("Partition config dataset generation for {} was successful".format(job.job_id))
            # If good, save the partition dataset data_id as a data requirement for the job.
            data_id_restrict = DiscreteRestriction(variable=StandardDatasetIndex.DATA_ID, values=[part_dataset_data_id])
            domain = DataDomain(data_format=DataFormat.NGEN_PARTITION_CONFIG, discrete_restrictions=[data_id_restrict])
            requirement = DataRequirement(domain=domain, is_input=True, category=DataCategory.CONFIG,
                                          fulfilled_by=part_dataset_name)
            job.data_requirements.append(requirement)
        else:
            logging.error("Partition config dataset generation for {} failed".format(job.job_id))

        return result

    # def _read_and_serialize_partitioner_output(self, output_file: Path) -> dict:
    #     try:
    #         with output_file.open() as output_data_file:
    #             return json.load(output_data_file)
    #     except Exception as e:
    #         msg = 'Could not read partitioner Docker container output file: {}'.format(str(e))
    #         raise RuntimeError(msg) from e

    @property
    def hydrofabric_data_root_dir(self) -> Path:
        """
        Get the ancestor data directory under which files for managed hydrofabrics are located.

        Returns
        -------
        Path
            The ancestor data directory under which files for managed hydrofabrics are located.
        """
        return self._hydrofabrics_root_dir

    async def listener(self, websocket: WebSocketServerProtocol):
        """
        Listen for and process partitioning requests.

        Parameters
        ----------
        websocket : WebSocketServerProtocol
            Websocket over which the request was sent and response should be sent.

        Returns
        -------

        """
        try:
            message = await websocket.recv()
            request: PartitionRequest = PartitionRequest.factory_init_from_deserialized_json(json.loads(message))
            if request is None:
                err_msg = "Unrecognized message format received over {} websocket (message: `{}`)".format(
                    self.__class__.__name__, message)
                response = InvalidMessageResponse(data={'message_content': message})
                await websocket.send(str(response))
                raise TypeError(err_msg)
            else:
                response = await self._async_process_request(request)
                await websocket.send(str(response))

        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listener task")

    async def manage_job_partitioning(self):
        """
        Task method to periodically generate partition configs for jobs that require them.
        """
        logging.info("Starting partitioner service management loop for job partition generation.")
        while True:
            lock_id = str(uuid4())
            while not self._job_util.lock_active_jobs(lock_id):
                await asyncio.sleep(2)

            for job in (j for j in self._job_util.get_all_active_jobs() if
                        j.status_step == JobExecStep.AWAITING_PARTITIONING):
                partition_requirements = [r for r in job.data_requirements if
                                          r.domain.data_format == DataFormat.NGEN_PARTITION_CONFIG]
                assert len(partition_requirements) <= 1

                if job.cpu_count == 1:
                    logging.info("No need to partition job {} with only 1 CPU allocated".format(job.job_id))
                    job.set_status_step(JobExecStep.AWAITING_ALLOCATION)
                elif len(partition_requirements) == 1 and partition_requirements[0].fulfilled_by:
                    logging.info(f"No need to partition job {job.job_id} with partition config already fulfilled by "
                                 f"dataset {partition_requirements[0].fulfilled_by}")
                    job.set_status_step(JobExecStep.AWAITING_ALLOCATION)
                else:
                    logging.info("Processing partitioning for active job {}".format(job.job_id))
                    try:
                        # TODO: test the actual partitioning process also
                        if await self._generate_partition_config_dataset(job):
                            job.set_status_step(JobExecStep.AWAITING_ALLOCATION)
                        else:
                            job.set_status_step(JobExecStep.PARTITIONING_FAILED)
                    except Exception as e:
                        logging.error(f"Partition generation for {job.job_id} failed ({e.__class__.__name__}) - {e!s}")
                        job.set_status_step(JobExecStep.PARTITIONING_FAILED)

                # Protect service task against problems with an individual save attempt
                try:
                    self._job_util.save_job(job)
                except Exception as e:
                    logging.error(f"Partition service actions were successful for job {job.job_id}, but service could "
                                  f"not save updated job state due to {e.__class__.__name__}: {e!s}")
            self._job_util.unlock_active_jobs(lock_id)
            await asyncio.sleep(5)



