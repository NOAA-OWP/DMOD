import asyncio
from dmod.communication import AbstractInitRequest
import json
import os
from time import sleep as time_sleep
from docker.types import Healthcheck, RestartPolicy, SecretReference, ServiceMode
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, \
    ManagementAction, WebSocketInterface
from dmod.communication.dataset_management_message import DatasetQuery, QueryType
from dmod.communication.data_transmit_message import DataTransmitMessage, DataTransmitResponse
from dmod.core.meta_data import DataCategory, DataDomain, DataRequirement, DiscreteRestriction
from dmod.core.serializable import ResultIndicator, BasicResultIndicator
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_dataset import Dataset, DatasetManager, ObjectStoreDataset, \
    ObjectStoreDatasetManager
from dmod.scheduler import SimpleDockerUtil
from dmod.scheduler.job import Job, JobExecStep, JobUtil
from typing import Dict, List, Optional, Tuple, Type, TypeVar, Union
from uuid import UUID, uuid4
from websockets import WebSocketServerProtocol

import logging


DATASET_MGR = TypeVar('DATASET_MGR', bound=DatasetManager)
DATASET_TYPE = TypeVar('DATASET_TYPE', bound=Dataset)


class DockerS3FSPluginHelper(SimpleDockerUtil):

    DOCKER_SERVICE_NAME = 's3fs-volumes-initializer'

    def __init__(self, service_manager: 'ServiceManager', obj_store_access: str, obj_store_secret: str, *args,
                 **kwargs):
        super(DockerS3FSPluginHelper, self).__init__(*args, **kwargs)
        image_name = os.getenv('S3FS_VOL_IMAGE_NAME', '127.0.0.1:5000/s3fs-volume-helper')
        image_tag = os.getenv('S3FS_VOL_IMAGE_TAG', 'latest')
        self.image = '{}:{}'.format(image_name, image_tag)
        self.networks = ['host']
        self._service_manager = service_manager
        self._obj_store_access = obj_store_access
        self._obj_store_secret = obj_store_secret

    def init_volumes(self, job: Job):
        # Get the names of all the needed datasets for all workers
        worker_required_datasets = set()
        all_dataset = self._service_manager.get_known_datasets()
        obj_store_dataset_names = [n for n in all_dataset if isinstance(all_dataset[n], ObjectStoreDataset)]
        for worker_reqs in job.worker_data_requirements:
            for fulfilled_by in [r.fulfilled_by for r in worker_reqs if r.fulfilled_by in obj_store_dataset_names]:
                worker_required_datasets.add(fulfilled_by)

        if len(worker_required_datasets) == 0:
            return

        secrets_objects = [self.docker_client.secrets.get('object_store_exec_user_name'),
                           self.docker_client.secrets.get('object_store_exec_user_passwd')]
        secrets = [SecretReference(secret_id=s.id, secret_name=s.name) for s in secrets_objects]

        sentinel_basename = 's3fs_init_sentinel'
        # Script written to have the sentinel have provided basename and be in /tmp directory
        sentinel_file_name = '/tmp/{}'.format(sentinel_basename)

        docker_cmd_args = ['--sentinel', sentinel_basename, '--service-mode']
        docker_cmd_args.extend(worker_required_datasets)

        service_name = '{}-{}'.format(self.DOCKER_SERVICE_NAME, job.job_id)

        restart_policy = RestartPolicy(condition='none')

        env_vars = ['S3FS_URL=http://localhost:9002/', 'PLUGIN_ALIAS=s3fs']
        env_vars.append('S3FS_ACCESS_KEY={}'.format(self._obj_store_access))
        env_vars.append('S3FS_SECRET_KEY={}'.format(self._obj_store_secret))

        # Make sure to re-mount the Docker socket inside the helper service container that gets started
        mounts = ['/var/run/docker.sock:/var/run/docker.sock:rw']

        def to_nanoseconds(seconds: int):
            return 1000000000 * seconds

        # Remember that the time values are in nanoseconds, so multiply
        healthcheck = Healthcheck(test=["CMD-SHELL", 'test -e {}'.format(sentinel_file_name)],
                                  interval=to_nanoseconds(seconds=2),
                                  timeout=to_nanoseconds(seconds=2),
                                  retries=5,
                                  start_period=to_nanoseconds(seconds=5))

        try:
            service = self.docker_client.services.create(image=self.image,
                                                         mode=ServiceMode(mode='global'),
                                                         args=docker_cmd_args,
                                                         cap_add=['SYS_ADMIN'],
                                                         env=env_vars,
                                                         name=service_name,
                                                         mounts=mounts,
                                                         networks=self.networks,
                                                         restart_policy=restart_policy,
                                                         healthcheck=healthcheck,
                                                         secrets=secrets)
            time_sleep(5)
            for tries in range(5):
                service.reload()
                if all([task['Status']['State'] == task['DesiredState'] for task in service.tasks()]):
                    break
                time_sleep(3)
            service.remove()
        except KeyError as e:
            logging.error('Failure checking service status: {}'.format(str(e)))
            service.remove()
        except Exception as e:
            logging.error(e)
            raise e


class ServiceManager(WebSocketInterface):
    """
    Primary service management class.
    """

    _PARSEABLE_REQUEST_TYPES = [DatasetManagementMessage]
    """ Parseable request types, which are all authenticated ::class:`MaaSRequest` subtypes for this implementation. """

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

    def __init__(self, job_util: JobUtil, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._job_util = job_util
        self._all_data_managers: Dict[Type[DATASET_TYPE], DATASET_MGR] = {}
        """ Map of dataset class type (key), to service's dataset manager (value) for handling that dataset type. """
        self._managers_by_uuid: Dict[UUID, DatasetManager] = {}
        """ Map of dataset managers keyed by the UUID of each. """
        self._obj_store_data_mgr = None
        self._obj_store_access_key = None
        self._obj_store_secret_key = None
        self._docker_s3fs_helper = DockerS3FSPluginHelper(service_manager=self,
                                                          obj_store_access=self._obj_store_access_key,
                                                          obj_store_secret=self._obj_store_secret_key, *args, **kwargs)

    def _add_manager(self, manager: DatasetManager):
        """
        Add this manager and its managed datasets to this service's internal collections and mappings.

        Method first ensures that this manager does not have any datasets conflicting with names of dataset of any
        previously added manager.  It then ensures there is no previously-add manager for managing any of the dataset
        types the given manager handles.  A ::class:`DmodRuntimeError` is thrown if there are any conflicts in either
        case.

        As long as there are no above-described conflicts, the method adds datasets of this manager to the service's
        known datasets collection (mapping the name of each dataset to its type) and the dataset-type-to-manager-object
        mapping.

        Parameters
        ----------
        manager : DatasetManager
            The new dataset manager to add/incorporate and use within this service.
        """
        # In this case, just return, as the manager is already added
        if manager.uuid in self._managers_by_uuid:
            return

        known_dataset_names = set(self.get_known_datasets().keys())
        if not known_dataset_names.isdisjoint(manager.datasets.keys()):
            duplicates = known_dataset_names.intersection(manager.datasets.keys())
            msg = "Can't add {} to service with already known dataset names {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        if not manager.supported_dataset_types.isdisjoint(self._all_data_managers.keys()):
            duplicates = manager.supported_dataset_types.intersection(self._all_data_managers.keys())
            msg = "Can't add new {} to service for managing already managed dataset types {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        # We've already done sanity checking for duplicates, so just add things.
        self._managers_by_uuid[manager.uuid] = manager

        for dataset_type in manager.supported_dataset_types:
            self._all_data_managers[dataset_type] = manager

    async def _async_can_dataset_be_derived(self, requirements: List[DataRequirement]) -> bool:
        """
        Asynchronously determine if a dataset can be derived from existing datasets to fulfill all these requirements.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirements : List[DataRequirement]
            The requirements that needs to be fulfilled.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill these requirement.

        See Also
        -------
        ::method:`can_dataset_be_derived`
        """
        return self.can_dataset_be_derived(requirements)

    async def _async_can_provide_data(self, dataset_name: str, data_item: str) -> ResultIndicator:
        """
        Check if the requested data can be provided by the service.

        Check if the requested data can be provided by the service.  If so, return a ::class:`BasicResultIndicator`
        that indicates success is ``True``.  If not, return a ::class:`DatasetManagementResponse` instance that includes
        ``reason`` and ``message`` properties that provide inforamtion on why the requested data cannot be provided.

        Parameters
        ----------
        message : DatasetManagementMessage
            A ``REQUEST_DATA`` action management message.

        Returns
        -------
        ResultIndicator
            A ::class:`BasicResultIndicator` if possible, or a ::class:`DatasetManagementResponse` if not.
        """
        action = ManagementAction.REQUEST_DATA
        if dataset_name not in self.get_known_datasets():
            msg = "Data service does not recognized a dataset with name '{}'".format(dataset_name)
            return DatasetManagementResponse(success=False, action=action, reason="Unknown Dataset", message=msg)
        elif data_item not in self.get_known_datasets()[dataset_name].manager.list_files(dataset_name):
            msg = "No file/item named '{}' exist within the '{}' dataset".format(data_item, dataset_name)
            return DatasetManagementResponse(success=False, action=action, reason='Unknown Data Item', message=msg)
        else:
            return BasicResultIndicator(success=True, reason='Valid Dataset and Item')

    async def _async_dataset_search(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Search for a dataset that fulfills the requirements of this ::class:`ManagementAction` ``SEARCH`` message.

        Parameters
        ----------
        message : DatasetManagementMessage
            A data management message with the ``SEARCH`` :class:`ManagementAction` set.

        Returns
        -------
        DatasetManagementResponse
            A response indicating the success of the search and, if successful, the name of the dataset.
        """
        requirements = [DataRequirement(domain=message.data_domain, is_input=True, category=message.data_category)]
        dataset = await self._async_find_dataset_for_requirements(requirements)
        if isinstance(dataset, Dataset):
            return DatasetManagementResponse(action=message.management_action, dataset_name=dataset.name, success=True,
                                             reason='Qualifying Dataset Found', data_id=str(dataset.uuid))
        else:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason='No Qualifying Dataset Found')

    async def _async_find_dataset_for_requirements(self, requirements: List[DataRequirement]) -> Optional[Dataset]:
        """
        Asynchronously search for an existing dataset that will fulfill all the given requirements.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirements : List[DataRequirement]
            The data requirements that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling the given requirements, if one is found; otherwise ``None``.

        See Also
        -------
        ::method:`find_dataset_for_requirements`
        """
        return self.find_dataset_for_requirements(requirements)

    async def _async_process_add_data(self, message: DatasetManagementMessage, mngr: DatasetManager) -> DatasetManagementResponse:
        """
        Async wrapper function for ::method:`_process_add_data`.

        Parameters
        ----------
        message : DatasetManagementMessage
            The incoming message, expected to include data to be added to a dataset.
        mngr : DatasetManager
            The manager instance for the relevant dataset.

        Returns
        -------
        DatasetManagementResponse
            Generated response to the manager message for adding data.

        See Also
        -------
        ::method:`_process_add_data`
        """
        return self._process_add_data(message, mngr)

    async def _async_process_dataset_create(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Async wrapper function for ::method:`_process_dataset_create`.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of creating a new dataset

        Returns
        -------
        DatasetManagementResponse
            A generated response object to the incoming creation message, indicating whether creation was successful.

        See Also
        -------
        ::method:`_process_dataset_create`
        """
        return self._process_dataset_create(message)

    async def _async_process_dataset_delete(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Async wrapper function for ::method:`_process_dataset_delete`.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of deleting a dataset

        Returns
        -------
        DatasetManagementResponse
            A generated response object to the incoming delete message, indicating whether deletion was successful.

        See Also
        -------
        ::method:`_process_dataset_delete`
        """
        return self._process_dataset_delete(message)

    async def _async_process_query(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Async wrapper function for ::method:`_process_query`.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of querying a dataset

        Returns
        -------
        DatasetManagementResponse
            A generated response object to the incoming query message, which includes the query response.

        See Also
        -------
        ::method:`_process_query`
        """
        return self._process_query(message)

    def _create_output_datasets(self, job: Job):
        """
        Create output datasets and associated requirements for this job, based on its ::method:`Job.output_formats`.

        Create empty output datasets and the associated ::class:`DataRequirement` instances for this job, corresponding
        to the output dataset formats listed in the job's ::method:`Job.output_formats` property.  The values in this
        property are iterated through by list index to be able to reuse the index value for dataset name, as noted
        below.

        Datasets will be named as ``job-<job_uuid>-output-<output_index>``, where ``<output_index>`` is the index of the
        corresponding value in ::method:`Job.output_formats`.

        Parameters
        ----------
        job : Job
            The job for which to create output datasets.
        """
        for i in range(len(job.model_request.output_formats)):

            id_restrict = DiscreteRestriction(variable='id', values=[])

            time_range = None
            for data_domain in [req.domain for req in job.data_requirements if req.category == DataCategory.FORCING]:
                time_restrictions = [r for k, r in data_domain.continuous_restrictions.items() if r.variable == 'Time']
                if len(time_restrictions) > 0:
                    time_range = time_restrictions[0]
                    break

            # TODO: (later) more intelligently determine type
            mgr = self._all_data_managers[ObjectStoreDataset]
            dataset = mgr.create(name='job-{}-output-{}'.format(job.job_id, i),
                                 is_read_only=False,
                                 category=DataCategory.OUTPUT,
                                 domain=DataDomain(data_format=job.model_request.output_formats[i],
                                                   continuous_restrictions=None if time_range is None else [time_range],
                                                   discrete_restrictions=[id_restrict]))
            # Create a data requirement for the job, fulfilled by the new dataset
            requirement = DataRequirement(domain=dataset.data_domain, is_input=False,
                                          category=DataCategory.OUTPUT, fulfilled_by=dataset.name)
            job.data_requirements.append(requirement)

    def _determine_dataset_type(self, message: DatasetManagementMessage) -> Type[DATASET_TYPE]:
        """
        Determine the right kind of dataset for this situation.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message initiating some kind of action for which the dataset type is needed.

        Returns
        -------
        Type[DATASET_TYPE]
            The class for the right kind of dataset for this situation.
        """
        # TODO: (later) implement this correctly
        return ObjectStoreDataset

    def _process_add_data(self, message: DatasetManagementMessage, mngr: DatasetManager) -> DatasetManagementResponse:
        """
        Process a management message for adding data to a dataset, adding the data using the provided manager.

        Parameters
        ----------
        message : DatasetManagementMessage
            The incoming message, expected to include data to be added to a dataset.
        mngr : DatasetManager
            The manager instance for the relevant dataset.

        Returns
        -------
        DatasetManagementResponse
            Generated response to the manager message for adding data.

        See Also
        -------
        ::method:`_async_process_add_data`
        """
        if not isinstance(message, DatasetManagementMessage):
            return DatasetManagementResponse(action=ManagementAction.UNKNOWN, success=False,
                                             reason="Unparseable Message Received")
        elif message.management_action != ManagementAction.ADD_DATA:
            msg_txt = "Expected {} action but received {}".format(ManagementAction.ADD_DATA, message.management_action)
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="Unexpected Management Action", message=msg_txt)
        elif message.data is None:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="No Data In ADD_DATA Message")
        elif mngr.add_data(message.dataset_name, dest=message.data_location, data=message.data):
            return DatasetManagementResponse(action=message.management_action, success=True, reason='Data Added',
                                             is_awaiting=message.is_pending_data, dataset_name=message.dataset_name)
        else:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             dataset_name=message.dataset_name, reason="Failure Adding Data To Dataset")

    def _process_dataset_create(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        As part of the communication protocol for the service, handle incoming messages that request dataset creation.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of creating a new dataset

        Returns
        ----------
        DatasetManagementResponse
            A generated response object to the incoming creation message, indicating whether creation was successful.
        """
        # Make sure there is no conflict/existing dataset already
        if message.dataset_name in self.get_known_datasets():
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="Dataset Already Exists", dataset_name=message.dataset_name)
        # Handle when message to create fails to include a dataset domain
        elif message.data_domain is None:
            msg = "Invalid {} for dataset creation: no dataset domain provided.".format(message.__class__.__name__)
            return DatasetManagementResponse(action=message.management_action, success=False, message=msg,
                                             reason="No Dataset Domain", dataset_name=message.dataset_name)

        # Create the dataset
        dataset_type = self._determine_dataset_type(message)
        dataset = self._all_data_managers[dataset_type].create(name=message.dataset_name, category=message.data_category,
                                                               domain=message.data_domain, is_read_only=False)
        # TODO: determine if there is an expectation to find data
        # TODO:     if so, attempt to find data, setting pending response based on result
        return DatasetManagementResponse(action=message.management_action, success=True, reason="Dataset Created",
                                         data_id=str(dataset.uuid), dataset_name=dataset.name,
                                         is_awaiting=message.is_pending_data)

    def _process_dataset_delete(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        As part of the communication protocol for the service, handle incoming messages that request dataset deletion.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of deleting an existing dataset

        Returns
        ----------
        DatasetManagementResponse
            A generated response object to the incoming delete message, indicating whether deletion was successful.
        """
        known_datasets = self.get_known_datasets()
        if message.dataset_name not in known_datasets:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="Dataset Does Not Exists", dataset_name=message.dataset_name)
        dataset: Dataset = known_datasets[message.dataset_name]

        # TODO: later look at doing something more related to if there are things using a dataset
        #dataset_users = dataset.manager.get_dataset_users(dataset.name)

        result = dataset.manager.delete(dataset=dataset)
        reason = 'Dataset Deleted' if result else 'Dataset Delete Failed'
        return DatasetManagementResponse(action=message.management_action, success=result, reason=reason,
                                         dataset_name=dataset.name)

    def _process_query(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        As part of the communication protocol for the service, handle incoming dataset query messages.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of querying a dataset

        Returns
        -------
        DatasetManagementResponse
            A generated response object to the incoming query message, which includes the query response.

        See Also
        -------
        ::method:`_async_process_query`
        """
        query_type = message.query.query_type
        if query_type == QueryType.LIST_FILES:
            dataset_name = message.dataset_name
            list_of_files = self.get_known_datasets()[dataset_name].manager.list_files(dataset_name)
            return DatasetManagementResponse(action=message.management_action, success=True, dataset_name=dataset_name,
                                             reason='Obtained {} Items List',
                                             data={DatasetManagementResponse._DATA_KEY_QUERY_RESULTS: list_of_files})
            # TODO: (later) add support for messages with other query types also
        else:
            reason = 'Unsupported {} Query Type - {}'.format(DatasetQuery.__class__.__name__, query_type.name)
            return DatasetManagementResponse(action=message.management_action, success=False, reason=reason)

    async def can_be_fulfilled(self, requirements: List[DataRequirement]) -> Tuple[bool, Optional[str]]:
        """
        Determine whether all the given requirements can be fulfilled, either directly or by deriving a new dataset.

        The returned tuple will return two items.  The first is whether the data requirements can be fulfilled given the
        currently existing datasets.  The second is the name of the fulfilling dataset, if a fulfilling dataset already
        exists.  If data among known datasets is sufficient to fulfill the requirements, but deriving a new dataset is
        necessary (e.g., in a different format, or by combining data from multiple datasets), then the second value will
        be ``None``.

        Parameters
        ----------
        requirements : List[DataRequirement]
            The data requirements in question that need to be fulfilled.

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple of whether the requirements can be fulfilled and, if one exists, the name of the fulfilling dataset.
        """
        fulfilling_dataset = await self._async_find_dataset_for_requirements(requirements)
        if isinstance(fulfilling_dataset, Dataset):
            return True, fulfilling_dataset.name
        else:
            return await self._async_can_dataset_be_derived(requirements), None

    def can_dataset_be_derived(self, requirements: List[DataRequirement]) -> bool:
        """
        Determine if it is possible for a dataset to be derived from existing datasets to fulfill these requirements.

        Parameters
        ----------
        requirements : List[DataRequirement]
            The requirement that needs to be fulfilled.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill these requirements.
        """
        return False

    def find_dataset_for_requirements(self, requirements: List[DataRequirement]) -> Optional[Dataset]:
        """
        Search for an existing dataset that will fulfill all the given requirements.

        Parameters
        ----------
        requirements : List[DataRequirement]
            The data requirements that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling all the given requirement, if one is found; otherwise ``None``.
        """
        for name, dataset in self.get_known_datasets().items():
            for requirement in requirements:
                if dataset.category != requirement.category or not dataset.data_domain.contains(requirement.domain):
                    break
            return dataset
        return None

    def get_known_datasets(self) -> Dict[str, Dataset]:
        """
        Get real-time mapping of all datasets known to this instance via its managers, in a map keyed by dataset name.

        This is implemented as a function, and not a property, since it is mutable and could change without this service
        instance being directly notified.  As such, a new collection object is created and returned on every call.

        Returns
        -------
        Dict[str, Dataset]
            All datasets known to the service via its manager objects, in a map keyed by dataset name.
        """
        datasets = {}
        for uuid, manager in self._managers_by_uuid.items():
            datasets.update(manager.datasets)
        return datasets

    def init_object_store_dataset_manager(self, obj_store_host: str, access_key: str, secret_key: str, port: int = 9000):
        mgr = ObjectStoreDatasetManager(obj_store_host_str='{}:{}'.format(obj_store_host, port), access_key=access_key,
                                        secret_key=secret_key)
        self._add_manager(mgr)
        self._obj_store_data_mgr = mgr

        self._obj_store_access_key = access_key
        self._obj_store_secret_key = secret_key

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Process incoming messages over the websocket and respond appropriately.
        """
        try:

            async for raw_message in websocket:
                data = json.loads(raw_message)
                inbound_message: DatasetManagementMessage = DatasetManagementMessage.factory_init_from_deserialized_json(data)

                # If we were not able to otherwise process the message into a response, then it is unsupported
                if inbound_message is None:
                    response = DatasetManagementResponse(action=ManagementAction.UNKNOWN, success=False,
                                                         reason="Unparseable Message Received")

                elif inbound_message.management_action == ManagementAction.CREATE:
                    response = await self._async_process_dataset_create(message=inbound_message)

                elif inbound_message.management_action == ManagementAction.QUERY:
                    response = await self._async_process_query(message=inbound_message)
                elif inbound_message.management_action == ManagementAction.DELETE:
                    response = await self._async_process_dataset_delete(message=inbound_message)
                elif inbound_message.management_action == ManagementAction.LIST_ALL:
                    dataset_names = list(self.get_known_datasets().keys())
                    dataset_names.sort()
                    response = DatasetManagementResponse(action=ManagementAction.LIST_ALL, success=True,
                                                         reason='List Assembled', data={'datasets': dataset_names})
                elif inbound_message.management_action == ManagementAction.SEARCH:
                    response = await self._async_dataset_search(message=inbound_message)
                # TODO: (later) properly handle additional incoming messages
                else:
                    msg = "Unsupported data management message action {}".format(inbound_message.management_action)
                    response = DatasetManagementResponse(action=inbound_message.management_action, success=False,
                                                         reason="Unsupported Action", message=msg)
                await websocket.send(str(response))

        # TODO: handle logging
        # TODO: handle exceptions appropriately
        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        #except websockets.exceptions.ConnectionClosed:
        #    logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.error("Cancelling listener task")
        except Exception as e:
            logging.error("Encountered error: {}".format(str(e)))

    async def manage_required_data_checks(self):
        """
        Task method to periodically examine whether required data for jobs is available.

        Method is expected to be a long-running async task.  In its main routine, it iterates through the job-level
        ::class:`DataRequirement`, in each active job in the ``AWAITING_DATA_CHECK`` ::class:`JobExecStep`.  It checks
        whether each individual requirement can be fulfilled for a job.  If so, the job is moved to the
        ``AWAITING_PARTITIONING`` step and any needed output datasets are created.  If not, the job is moved to the
        ``DATA_UNPROVIDEABLE`` step.
        """
        while True:
            for job in self._job_util.get_all_active_jobs():
                if job.status_step != JobExecStep.AWAITING_DATA_CHECK:
                    continue
                # Check if all requirements for this job can be fulfilled, updating the job's status based on result
                if await self.perform_checks_for_job(job):
                    # Before moving to next successful step, also create output datasets and requirement entries
                    self._create_output_datasets(job)
                    job.status_step = JobExecStep.AWAITING_PARTITIONING
                else:
                    job.status_step = JobExecStep.DATA_UNPROVIDEABLE
                # Regardless, save the updated job state
                try:
                    self._job_util.save_job(job)
                except:
                    # TODO: logging would be good, and perhaps maybe retries
                    pass
            await asyncio.sleep(5)

    async def manage_data_provision(self):
        """
        Task method to periodically associate and (when needed) generate required datasets with/for jobs.
        """
        logging.debug("Starting task loop for performing data provisioning for requested jobs.")
        while True:
            lock_id = str(uuid4())
            while not self._job_util.lock_active_jobs(lock_id):
                await asyncio.sleep(2)

            for job in [j for j in self._job_util.get_all_active_jobs() if j.status_step == JobExecStep.AWAITING_DATA]:
                logging.debug("Managing provisioning for job {} that is awaiting data.".format(job.job_id))

                # Initialize dataset Docker volumes required for a job
                try:
                    logging.debug('Initializing any required S3FS dataset volumes for {}'.format(job.job_id))
                    self._docker_s3fs_helper.init_volumes(job=job)
                except Exception as e:
                    job.status_step = JobExecStep.DATA_FAILURE
                    self._job_util.save_job(job)
                    continue

                job.status_step = JobExecStep.AWAITING_SCHEDULING
                self._job_util.save_job(job)

            self._job_util.unlock_active_jobs(lock_id)
            await asyncio.sleep(5)

    async def perform_checks_for_job(self, job: Job) -> bool:
        """
        Check whether all requirements for this job can be fulfilled, setting the fulfillment associations.

        Check whether all the requirements for the provided job can be fulfilled, such that the job can move on to the
        next successful step in the execution workflow.  As part of the check, also update the ::class:`DataRequirement`
        objects with the name of the fulfilling dataset.

        Parameters
        ----------
        job : Job
            The job of interest.

        Returns
        -------
        bool
            Whether all requirements can be fulfilled.

        See Also
        -------
        ::method:`can_be_fulfilled`
        """
        # TODO: (later) should we check whether any 'fulfilled_by' datasets exist, or handle this differently?
        for requirement in [req for req in job.data_requirements if req.fulfilled_by is None]:
            can_fulfill, dataset_name = await self.can_be_fulfilled([requirement])
            if not can_fulfill:
                return False
            elif dataset_name is not None:
                requirement.fulfilled_by = dataset_name
        return True

