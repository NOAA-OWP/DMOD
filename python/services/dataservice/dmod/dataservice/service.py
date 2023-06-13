import asyncio
from dmod.communication import AbstractInitRequest
import json
import os
from time import sleep as time_sleep
from docker.types import Healthcheck, RestartPolicy, ServiceMode
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, WebSocketInterface
from dmod.communication.dataset_management_message import DatasetQuery, QueryType
from dmod.communication.data_transmit_message import DataTransmitMessage, DataTransmitResponse
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction, \
    StandardDatasetIndex
from dmod.core.serializable import ResultIndicator, BasicResultIndicator
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_manager import Dataset, DatasetManager, DatasetType, ObjectStoreDatasetManager
from dmod.modeldata.data.filesystem_manager import FilesystemDatasetManager
from dmod.scheduler import SimpleDockerUtil
from dmod.scheduler.job import Job, JobExecStep, JobUtil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar, Union
from uuid import UUID, uuid4
from websockets import WebSocketServerProtocol
from .data_derive_util import DataDeriveUtil

import logging


DATASET_MGR = TypeVar('DATASET_MGR', bound=DatasetManager)


class DockerS3FSPluginHelper(SimpleDockerUtil):
    """
    A utility to assist with creating Docker volumes for object store datasets.

    The primary function for this type is ::method:`init_volumes`.  It creates a ``global`` Docker service that runs on
    all Swarm nodes and creates any necessary object store dataset volumes on each node.
    """

    DOCKER_SERVICE_NAME = 's3fs-volumes-initializer'

    def __init__(self, service_manager: 'ServiceManager', obj_store_access: str, obj_store_secret: str,
                 docker_image_name: str, docker_image_tag: str, docker_networks: List[str], obj_store_url: Optional[str],
                 docker_plugin_alias: str = 's3fs', access_docker_secret_name: str = 'object_store_exec_user_name',
                 secret_docker_secret_name: str = 'object_store_exec_user_passwd', *args, **kwargs):
        super(DockerS3FSPluginHelper, self).__init__(*args, **kwargs)
        self._image_name = docker_image_name
        self._image_tag = docker_image_tag
        self.image = '{}:{}'.format(self._image_name, self._image_tag)
        self.networks = docker_networks
        self._docker_plugin_alias = docker_plugin_alias
        self._service_manager = service_manager
        self._obj_store_url = obj_store_url
        self._obj_store_access = obj_store_access
        self._obj_store_secret = obj_store_secret

        self._obj_store_docker_secret_names = [access_docker_secret_name, secret_docker_secret_name]

        self._sentinel_file = None
        self._service_heathcheck = None

    def _get_worker_required_datasets(self, job: Job) -> Set[str]:
        """
        Get the names of all required datasets for all workers of this job.

        Parameters
        ----------
        job : Job
            A job object with allocated workers, for which the required datasets are needed.

        Returns
        -------
        Set[str]
            Set of the names of required datasets for all the given job's workers.
        """
        worker_required_datasets = set()
        all_dataset = self._service_manager.get_known_datasets()
        obj_store_dataset_names = [n for n in all_dataset if all_dataset[n].dataset_type == DatasetType.OBJECT_STORE]
        for worker_reqs in job.worker_data_requirements:
            for fulfilled_by in [r.fulfilled_by for r in worker_reqs if r.fulfilled_by in obj_store_dataset_names]:
                worker_required_datasets.add(fulfilled_by)
        return worker_required_datasets

    def init_volumes(self, job: Job):
        """
        Primary function for this type, creating needed dataset volumes on all hosts through a global Swarm service.

        Function creates a ``global`` Docker service using the appropriate image, where the image name and tag was
        provided to the instance when it was created.  It is expected that this image contains a script that can expect
        standardized args and environment variables, and initialize the appropriate Docker volumes for the needed
        datasets on each host.

        Parameters
        ----------
        job : Job
            The job for which volumes should be created, where each such volume correspond to an object store dataset
            required by one of the job's workers.
        """
        worker_required_datasets = self._get_worker_required_datasets(job)
        if len(worker_required_datasets) == 0:
            return

        secrets = [self.get_secret_reference(sn) for sn in self._obj_store_docker_secret_names]

        docker_cmd_args = ['--sentinel', self.sentinel_file, '--service-mode']
        docker_cmd_args.extend(worker_required_datasets)

        env_vars = ['PLUGIN_ALIAS={}'.format(self._docker_plugin_alias)]
        if self._obj_store_url is not None:
            env_vars.append('S3FS_URL={}'.format(self._obj_store_url))
        env_vars.append('S3FS_ACCESS_KEY={}'.format(self._obj_store_access))
        env_vars.append('S3FS_SECRET_KEY={}'.format(self._obj_store_secret))

        try:
            service = self.docker_client.services.create(image=self.image,
                                                         mode=ServiceMode(mode='global'),
                                                         args=docker_cmd_args,
                                                         cap_add=['SYS_ADMIN'],
                                                         env=env_vars,
                                                         name='{}-{}'.format(self.DOCKER_SERVICE_NAME, job.job_id),
                                                         # Make sure to re-mount the Docker socket inside the helper
                                                         # service container that gets started
                                                         mounts=['/var/run/docker.sock:/var/run/docker.sock:rw'],
                                                         networks=self.networks,
                                                         restart_policy=RestartPolicy(condition='none'),
                                                         healthcheck=self.service_healthcheck,
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

    @property
    def sentinel_file(self) -> str:
        """
        String form of file path to sentinel file used by entrypoint script.

        Sentinel file is passed as an argument to entrypoint script.  It is also then used in the Docker healthcheck for
        started service(s) created by ::method:`service_healthcheck`, expecting the script to have created the file to
        indicate it is working.

        At present the entrypoint is written to have the sentinel file be of a standard, fixed basename within the
        ``/tmp/`` directory.

        Returns
        -------
        str
            String form of file path to sentinel file used by entrypoint script.

        See Also
        -------
        service_healthcheck
        """
        if self._sentinel_file is None:
            self._sentinel_file = '/tmp/{}'.format('s3fs_init_sentinel')
        return self._sentinel_file

    @property
    def service_healthcheck(self):
        """
        The Docker healthcheck to use when creating services.

        Returns
        -------
        Healthcheck
            The Docker healthcheck to use when creating services.

        See Also
        -------
        sentinel_file
        """
        # Remember that the time values are expected in nanoseconds, so ...
        def to_nanoseconds(seconds: int):
            return 1000000000 * seconds

        return Healthcheck(test=["CMD-SHELL", 'test -e {}'.format(self.sentinel_file)],
                           interval=to_nanoseconds(seconds=2),
                           timeout=to_nanoseconds(seconds=2),
                           retries=5,
                           start_period=to_nanoseconds(seconds=5))


class ServiceManager(WebSocketInterface):
    """
    Primary service management class.
    """

    _PARSEABLE_REQUEST_TYPES = [DatasetManagementMessage]
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

    def __init__(self, job_util: JobUtil, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._job_util = job_util
        self._all_data_managers: Dict[DatasetType, DatasetManager] = {}
        """ Map of dataset class type (key), to service's dataset manager (value) for handling that dataset type. """
        self._managers_by_uuid: Dict[UUID, DatasetManager] = {}
        """ Map of dataset managers keyed by the UUID of each. """
        self._obj_store_data_mgr = None
        self._obj_store_access_key = None
        self._obj_store_secret_key = None
        self._docker_s3fs_helper = None
        self._filesystem_data_mgr = None
        self._data_derive_util: DataDeriveUtil = DataDeriveUtil(data_mgrs_by_ds_type=self._all_data_managers)

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
        requirement = DataRequirement(domain=message.data_domain, is_input=True, category=message.data_category)
        dataset = await self._async_find_dataset_for_requirement(requirement)
        if isinstance(dataset, Dataset):
            return DatasetManagementResponse(action=message.management_action, dataset_name=dataset.name, success=True,
                                             reason='Qualifying Dataset Found', data_id=str(dataset.uuid))
        else:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason='No Qualifying Dataset Found')

    async def _async_find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Asynchronously search for an existing dataset that will fulfill the given requirement.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling the given requirement, if one is found; otherwise ``None``.

        See Also
        -------
        ::method:`find_dataset_for_requirement`
        """
        return self.find_dataset_for_requirement(requirement)

    async def _async_process_add_data(self, dataset_name: str, dest_item_name: str, message: DataTransmitMessage,
                                      manager: DatasetManager, is_temp: bool = False) -> Union[DataTransmitResponse,
                                                                                               DatasetManagementResponse]:
        """
        Process a data transmit message for adding data to a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset to which data should be added.
        dest_item_name : str
            The name of the item/object/file within the dataset to which data should be added.
        message : DataTransmitMessage
            The incoming data message.
        manager : DatasetManager
            The manager instance for the relevant dataset.
        is_temp : bool
            Value to pass through to the dataset manager, which is an indication of whether the destination item should
            be treated as temporary.

        Returns
        -------
        Union[DataTransmitResponse, DatasetManagementResponse]
            Generated response to the manager message for adding data.
        """
        if not isinstance(message, DataTransmitMessage):
            return DatasetManagementResponse(action=ManagementAction.ADD_DATA, success=False, dataset_name=dataset_name,
                                             reason="Unexpected Message Type Received")
        elif message.data is None:
            return DatasetManagementResponse(action=ManagementAction.ADD_DATA, success=False, dataset_name=dataset_name,
                                             reason="No Data In Transmit Message")
        elif manager.add_data(dataset_name=dataset_name, dest=dest_item_name, data=message.data.encode(), is_temp=is_temp):
            if message.is_last:
                return DatasetManagementResponse(action=ManagementAction.ADD_DATA, success=True,
                                                 dataset_name=dataset_name, reason="All Data Added Successfully")
            else:
                return DataTransmitResponse(series_uuid=message.series_uuid, success=True, reason='Data Added')
        else:
            return DatasetManagementResponse(action=ManagementAction.ADD_DATA, success=False,
                                             dataset_name=dataset_name, reason="Failure Adding Data To Dataset")

    async def _async_process_data_request(self, message: DatasetManagementMessage, websocket) -> DatasetManagementResponse:
        # Check if the data request can actually be fulfilled
        dataset_name = message.dataset_name
        item_name = message.data_location
        check_possible_result = await self._async_can_provide_data(dataset_name=dataset_name, data_item=item_name)
        if not check_possible_result.success:
            # This should mean this is specifically a response instance than we can directly return
            return check_possible_result

        chunk_size = 1024
        manager = self.get_known_datasets()[dataset_name].manager
        chunking_keys = manager.data_chunking_params
        if chunking_keys is None:
            raw_data = manager.get_data(dataset_name=dataset_name, item_name=item_name)
            transmit = DataTransmitMessage(data=raw_data, series_uuid=uuid4(), is_last=True)
            await websocket.send(str(transmit))
            response = DataTransmitResponse.factory_init_from_deserialized_json(json.loads(await websocket.recv()))
        else:
            offset = 0
            actual_length = chunk_size
            while actual_length == chunk_size:
                chunk_params = {chunking_keys[0]: offset, chunking_keys[1]: chunk_size}
                raw_data = manager.get_data(dataset_name, item_name, **chunk_params)
                offset += chunk_size
                actual_length = len(raw_data)
                transmit = DataTransmitMessage(data=raw_data, series_uuid=uuid4(), is_last=True)
                await websocket.send(str(transmit))
                raw_response = await websocket.recv()
                json_response = json.loads(raw_response)
                response = DataTransmitResponse.factory_init_from_deserialized_json(json_response)
                if not response.success:
                    break
        return DatasetManagementResponse(success=response.success, message='' if response.success else response.message,
                                         reason='All Data Transferred' if response.success else response.reason)

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

            id_restrict = DiscreteRestriction(variable=StandardDatasetIndex.ELEMENT_ID, values=[])

            time_range = None
            for data_domain in [req.domain for req in job.data_requirements if req.category == DataCategory.FORCING]:
                time_restrictions = [r for k, r in data_domain.continuous_restrictions.items() if r.variable == 'Time']
                if len(time_restrictions) > 0:
                    time_range = time_restrictions[0]
                    break

            # TODO: (later) more intelligently determine type
            mgr = self._all_data_managers[DatasetType.OBJECT_STORE]
            dataset = mgr.create(name='job-{}-output-{}'.format(job.job_id, i),
                                 is_read_only=False,
                                 category=DataCategory.OUTPUT,
                                 domain=DataDomain(data_format=job.model_request.output_formats[i],
                                                   continuous_restrictions=None if time_range is None else [time_range],
                                                   discrete_restrictions=[id_restrict]))
            # TODO: (later) in the future, whether the job is running via Docker needs to be checked
            # TODO: also, whatever is done here needs to align with what is done within perform_checks_for_job, when
            #  setting the fulfilled_access_at for the DataRequirement
            is_job_run_in_docker = True
            if is_job_run_in_docker:
                output_access_at = dataset.docker_mount
            else:
                msg = "Could not determine proper access location for new output dataset of type {} by non-Docker job {}."
                raise DmodRuntimeError(msg.format(dataset.__class__.__name__, job.job_id))
            # Create a data requirement for the job, fulfilled by the new dataset
            requirement = DataRequirement(domain=dataset.data_domain, is_input=False, category=DataCategory.OUTPUT,
                                          fulfilled_by=dataset.name, fulfilled_access_at=output_access_at)
            job.data_requirements.append(requirement)

    def _determine_dataset_type(self, message: DatasetManagementMessage) -> DatasetType:
        """
        Determine the right type of dataset for this situation.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message initiating some kind of action for which the dataset type is needed.

        Returns
        -------
        DatasetType
            The appopriate ::class:`DatasetType` value for this situation.
        """
        # TODO: figure out if this is actually still needed, and fix for filesystem type if so ...
        # TODO: (later) implement this correctly
        return DatasetType.OBJECT_STORE

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

    def _process_initial_add_data(self, message: DatasetManagementMessage) -> Tuple[str, DatasetManager, str, UUID, DataTransmitResponse]:
        """
        Process initial ``ADD_DATA`` message, preparing things needed for the subsequent transfer routine.

        Process the initial ``ADD_DATA`` management message, which involves preparing things needed for the subsequent
        transfer routine.  These are then returned as a tuple, typically to be used by the ::method:`listener` method
        in the ``for`` loop of messages coming through the current thread's websocket.

        The function prepares and returns the following:

        - the name of the dataset to which data is to be added
        - the ::class:`DatasetManager` object managing the aforementioned dataset
        - the name/identifier of the item/file/object/etc. within the dataset into which the added data is to be placed
        - the "series" ::class:`UUID` to identify multiple transmit messages of the same ``ADD_DATA`` process
        - the initial ::class:`DataTransmitResponse` that indicates the service is ready to receive transmitted data

        Parameters
        ----------
        message : DatasetManagementMessage
            The message initiating the ``ADD_DATA`` process.

        Returns
        -------
        Tuple[str, DatasetManager, str, UUID, DataTransmitResponse]
            Tuple of ``dataset_name``, ``dataset_manager``, ``dest_item_name``, ``series_uuid``, ``transmit_response``.

        See Also
        -------
        listener
        """
        if message.management_action != ManagementAction.ADD_DATA:
            msg = "Data service function to process initial '{}' {} instead received one with action '{}'"
            raise ValueError(msg.format(ManagementAction.ADD_DATA.name, DatasetManagementMessage.__name__,
                                        message.management_action.name))
        dataset_name = message.dataset_name
        manager = self.get_known_datasets()[dataset_name].manager
        series_uuid = uuid4()
        dest_item_name = message.data_location
        # TODO: (later) probably need some logic to check the manager to make sure this is actually ready
        response = DataTransmitResponse(series_uuid=series_uuid, success=True, reason='Ready')
        return message.dataset_name, manager, dest_item_name, series_uuid, response

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

    async def can_be_fulfilled(self, requirement: DataRequirement, job: Optional[Job] = None) -> Tuple[bool, Optional[Dataset]]:
        """
        Determine details of whether a data requirement can be fulfilled, either directly or by deriving a new dataset.

        The function will process and return a tuple of two items.  The first is whether the data requirement can be
        fulfilled, given the currently existing datasets.  The second is either the fulfilling ::class:`Dataset`, if a
        dataset already exists that completely fulfills the requirement, or ``None``.

        Even if a single fulfilling dataset for the requirement does not already exist, it may still be possible for the
        service to derive a new dataset that does fulfill the requirement.  In such cases, ``True, None`` is returned.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement in question that needs to be fulfilled.
        job : Optional[Job]
            The job having the given requirement.

        Returns
        -------
        Tuple[bool, Optional[Dataset]]
            A tuple of whether the requirement can be fulfilled and, if one already exists, the fulfilling dataset.
        """
        fulfilling_dataset = await self._async_find_dataset_for_requirement(requirement)
        if isinstance(fulfilling_dataset, Dataset):
            return True, fulfilling_dataset
        else:
            return await self._data_derive_util.async_can_dataset_be_derived(requirement=requirement, job=job), None

    def find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Search for an existing dataset that will fulfill the given requirement.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The (first) dataset fulfilling the given requirement, if one is found; otherwise ``None``.
        """
        # Keep track of a few things for logging purposes
        datasets_count_match_category = 0
        datasets_count_match_format = 0
        # Keep those of the right category but wrong format, in case one is needed and satisfactory
        potentially_compatible_alternates: List[Dataset] = []

        for name, dataset in self.get_known_datasets().items():
            # Skip anything with the wrong category
            if dataset.category != requirement.category:
                continue

            # Keep track of how many of the right category there were for error purposes
            datasets_count_match_category += 1

            # Skip (for now at least) anything with a different format (though set aside if potentially compatible)
            if dataset.data_format != requirement.domain.data_format:
                # Check if this format could fulfill
                if DataFormat.can_format_fulfill(needed=requirement.domain.data_format, alternate=dataset.data_format):
                    # We will return to examine these if no dataset qualifies that has the exact format in requirement
                    potentially_compatible_alternates.append(dataset)
                continue

            # When a dataset matches, keep track for error counts, and then test to see if it qualifies
            datasets_count_match_format += 1
            # TODO: need additional test of some kind for cases when the requirement specifies "any" (e.g., "any"
            #  catchment (from hydrofabric) in realization config, for finding a forcing dataset)
            if dataset.data_domain.contains(requirement.domain):
                return dataset

        # At this point, no datasets qualify against the exact domain (including format) of the requirement
        # However, before failing, check if any have different, but compatible format, and otherwise qualify
        for dataset in potentially_compatible_alternates:
            if dataset.data_domain.contains(requirement.domain):
                return dataset

        # Before failing, treat the count of alternates as being of the same format, for error messaging purposes
        datasets_count_match_format += len(potentially_compatible_alternates)

        if datasets_count_match_category == 0:
            msg = "Could not fill requirement for '{}': no datasets for this category"
            logging.error(msg.format(requirement.category.name))
        elif datasets_count_match_format == 0:
            msg = "Could not fill requirement with '{}' format domain: no datasets found this (or compatible) format"
            logging.error(msg.format(requirement.domain.data_format.name))
        else:
            msg = "Could not find dataset meeting all restrictions of requirement: {}"
            logging.error(msg.format(requirement.to_json()))
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

    def init_filesystem_dataset_manager(self, file_dataset_config_dir: Path):
        logging.info("Initializing manager for {} type datasets".format(DatasetType.FILESYSTEM.name))
        mgr = FilesystemDatasetManager(serialized_files_directory=file_dataset_config_dir)
        logging.info("{} initialized with {} existing datasets".format(mgr.__class__.__name__, len(mgr.datasets)))
        self._add_manager(mgr)
        self._filesystem_data_mgr = mgr

    def init_object_store_dataset_manager(self, obj_store_host: str, access_key: str, secret_key: str, port: int = 9000,
                                          *args, **kwargs):
        host_str = '{}:{}'.format(obj_store_host, port)
        logging.info("Initializing object store dataset manager at {}".format(host_str))
        mgr = ObjectStoreDatasetManager(obj_store_host_str=host_str, access_key=access_key, secret_key=secret_key)
        logging.info("Object store dataset manager initialized with {} existing datasets".format(len(mgr.datasets)))
        self._add_manager(mgr)
        self._obj_store_data_mgr = mgr

        self._obj_store_access_key = access_key
        self._obj_store_secret_key = secret_key

        s3fs_helper_networks = ['host']

        s3fs_url_proto = os.getenv('S3FS_URL_PROTOCOL', 'http')
        s3fs_url_host = os.getenv('S3FS_URL_HOST')
        s3fs_url_port = os.getenv('S3FS_URL_PORT', '9000')
        if s3fs_url_host is not None:
            s3fs_helper_url = '{}://{}:{}/'.format(s3fs_url_proto, s3fs_url_host, s3fs_url_port)
        else:
            s3fs_helper_url = None

        self._docker_s3fs_helper = DockerS3FSPluginHelper(service_manager=self,
                                                          obj_store_access=self._obj_store_access_key,
                                                          obj_store_secret=self._obj_store_secret_key,
                                                          docker_image_name=os.getenv('S3FS_VOL_IMAGE_NAME', '127.0.0.1:5000/s3fs-volume-helper'),
                                                          docker_image_tag=os.getenv('S3FS_VOL_IMAGE_TAG', 'latest'),
                                                          docker_networks=s3fs_helper_networks,
                                                          docker_plugin_alias=os.getenv('S3FS_PLUGIN_ALIAS', 's3fs'),
                                                          obj_store_url=s3fs_helper_url,
                                                          *args, **kwargs)

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Process incoming messages over the websocket and respond appropriately.
        """
        try:
            # We may need to lazily load a dataset manager
            dataset_manager = None
            dest_dataset_name = None
            dest_item_name = None
            transmit_series_uuid = None
            partial_indx = 0
            async for raw_message in websocket:
                data = json.loads(raw_message)
                if transmit_series_uuid is None:
                    inbound_message: DatasetManagementMessage = DatasetManagementMessage.factory_init_from_deserialized_json(data)
                else:
                    inbound_message: DataTransmitMessage = DataTransmitMessage.factory_init_from_deserialized_json(data)
                # If we were not able to otherwise process the message into a response, then it is unsupported
                if inbound_message is None:
                    response = DatasetManagementResponse(action=ManagementAction.UNKNOWN, success=False,
                                                         reason="Unparseable Message Received")
                elif transmit_series_uuid:
                    # TODO: need to refactor this to be cleaner
                    # Write data to temporary, partial item name, then after the last one, combine all the temps in this
                    # transmit series into a single file
                    partial_item_name = '{}.{}.{}'.format(transmit_series_uuid, dest_item_name, partial_indx)
                    response = await self._async_process_add_data(dataset_name=dest_dataset_name,
                                                                  dest_item_name=partial_item_name,
                                                                  message=inbound_message,
                                                                  is_temp=True,
                                                                  manager=dataset_manager)
                    partial_indx += 1
                    if inbound_message.is_last and response.success:
                        partial_items = ['{}.{}.{}'.format(transmit_series_uuid, dest_item_name, i) for i in range(partial_indx)]
                        # Combine partial files into a composite
                        dataset_manager.combine_partials_into_composite(dataset_name=dest_dataset_name,
                                                                        item_name=dest_item_name,
                                                                        combined_list=partial_items)
                        # Clean up the partial items
                        dataset_manager.delete_data(dataset_name=dest_dataset_name, item_names=partial_items)
                    # Clear the series UUID if we just processed the last transmit message (response will have the UUID
                    # by this point), or if we got back an unsuccessful response (whether management or transfer type)
                    elif inbound_message.is_last or not response.success:
                        transmit_series_uuid = None
                        # Clean up the partial items
                        partial_items = ['{}.{}.{}'.format(transmit_series_uuid, dest_item_name, i) for i in range(partial_indx)]
                        result = dataset_manager.delete_data(dataset_name=dest_dataset_name, item_names=partial_items)
                        # If this didn't work, retry without the very last partial item name, since it may have failed
                        if not result:
                            dataset_manager.delete_data(dataset_name=dest_dataset_name, item_names=[
                                '{}.{}.{}'.format(transmit_series_uuid, dest_item_name, i) for i in
                                range(partial_indx - 1)])
                        partial_indx = 0
                elif inbound_message.management_action == ManagementAction.CREATE:
                    response = await self._async_process_dataset_create(message=inbound_message)
                elif inbound_message.management_action == ManagementAction.REQUEST_DATA:
                    response = await self._async_process_data_request(message=inbound_message, websocket=websocket)
                elif inbound_message.management_action == ManagementAction.ADD_DATA:
                    # When seeing ADD_DATA, this is the beginning of several messages, so init/cache certain things
                    # Note that transmit_series_uuid should be 'None' before this, as this is its initial value and it
                    #   will be reset to 'None' after the last
                    dest_dataset_name, dataset_manager, dest_item_name, transmit_series_uuid, response = \
                        self._process_initial_add_data(inbound_message)
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
        logging.debug("Starting task loop for performing checks for required data for jobs.")
        while True:
            lock_id = str(uuid4())
            while not self._job_util.lock_active_jobs(lock_id):
                await asyncio.sleep(2)

            for job in self._job_util.get_all_active_jobs():
                if job.status_step != JobExecStep.AWAITING_DATA_CHECK:
                    continue

                logging.debug("Checking if required data is available for job {}.".format(job.job_id))
                # Check if all requirements for this job can be fulfilled, updating the job's status based on result
                if await self.perform_checks_for_job(job):
                    logging.info("All required data for {} is available.".format(job.job_id))
                    # Before moving to next successful step, also create output datasets and requirement entries
                    self._create_output_datasets(job)
                    job.status_step = JobExecStep.AWAITING_PARTITIONING if job.cpu_count > 1 else JobExecStep.AWAITING_ALLOCATION
                else:
                    logging.error("Some or all required data for {} is unprovideable.".format(job.job_id))
                    job.status_step = JobExecStep.DATA_UNPROVIDEABLE
                # Regardless, save the updated job state
                try:
                    self._job_util.save_job(job)
                except:
                    # TODO: logging would be good, and perhaps maybe retries
                    pass
            self._job_util.unlock_active_jobs(lock_id)
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
                try:
                    # Derive any datasets as required
                    reqs_w_derived_datasets = await self._data_derive_util.derive_datasets(job)
                    logging.info('Job {} had {} datasets derived.'.format(job.job_id, len(reqs_w_derived_datasets)))

                    # Initialize dataset Docker volumes required for a job
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
        objects with the name of the fulfilling dataset and the location at which the dataset will be accessible to the
        job.

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
        try:
            for requirement in [req for req in job.data_requirements if req.fulfilled_by is None]:
                can_fulfill, dataset = await self.can_be_fulfilled(requirement=requirement, job=job)

                if not can_fulfill:
                    logging.error("Cannot fulfill '{}' category data requirement".format(requirement.category.name))
                    return False
                elif dataset is not None:
                    # TODO: (later) in the future, whether the job is running via Docker needs to be checked
                    # TODO: also, whatever is done here needs to align with what is done within _create_output_dataset,
                    #  when creating the output data DataRequirement
                    is_job_run_in_docker = True
                    if is_job_run_in_docker:
                        requirement.fulfilled_access_at = dataset.docker_mount
                    else:
                        msg = "Could not determine proper access location for dataset of type {} by non-Docker job {}."
                        raise DmodRuntimeError(msg.format(dataset.__class__.__name__, job.job_id))
                    requirement.fulfilled_by = dataset.name
            return True
        except Exception as e:
            msg = "Encountered {} checking if job {} data requirements could be fulfilled - {}"
            logging.error(msg.format(e.__class__.__name__, job.job_id, str(e)))
            return False

