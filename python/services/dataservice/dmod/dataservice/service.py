import asyncio
from dmod.communication import AbstractInitRequest
import json
from time import sleep as time_sleep
from datetime import datetime, timedelta
from docker.types import Healthcheck, RestartPolicy, ServiceMode
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, WebSocketInterface
from dmod.communication.dataset_management_message import DatasetQuery, QueryType
from dmod.communication.data_transmit_message import DataTransmitMessage, DataTransmitResponse
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction, \
    StandardDatasetIndex
from dmod.core.dataset import Dataset, DatasetManager, DatasetUser, DatasetType
from dmod.core.serializable import BasicResultIndicator
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_manager import ObjectStoreDatasetManager
from dmod.modeldata.data.filesystem_manager import FilesystemDatasetManager
from dmod.scheduler import SimpleDockerUtil
from dmod.scheduler.job import Job, JobExecStep, JobUtil
from pathlib import Path
from typing import Dict, List, NoReturn, Optional, Set, Tuple, Type, TypeVar, Union
from uuid import UUID, uuid4
from websockets import WebSocketServerProtocol
from fastapi.websockets import WebSocket
from .dataset_inquery_util import DatasetInqueryUtil
from .data_derive_util import DataDeriveUtil
from .dataset_user_impl import JobDatasetUser
from .service_settings import ServiceSettings
from .dataset_manager_collection import DatasetManagerCollection

import logging


DATASET_MGR = TypeVar('DATASET_MGR', bound=DatasetManager)


class DockerS3FSPluginHelper(SimpleDockerUtil):
    """
    A utility to assist with creating Docker volumes for object store datasets.

    The primary function for this type is ::method:`init_volumes`.  It creates a ``global`` Docker service that runs on
    all Swarm nodes and creates any necessary object store dataset volumes on each node.
    """

    DOCKER_SERVICE_NAME = 's3fs-volumes-initializer'

    def __init__(self, dataset_manager_collection: DatasetManagerCollection, obj_store_access: str, obj_store_secret: str,
                 docker_image_name: str, docker_image_tag: str, docker_networks: List[str], obj_store_url: Optional[str],
                 docker_plugin_alias: str = 's3fs', access_docker_secret_name: str = 'object_store_exec_user_name',
                 secret_docker_secret_name: str = 'object_store_exec_user_passwd', *args, **kwargs):
        super(DockerS3FSPluginHelper, self).__init__(*args, **kwargs)
        self._image_name = docker_image_name
        self._image_tag = docker_image_tag
        self.image = '{}:{}'.format(self._image_name, self._image_tag)
        self.networks = docker_networks
        self._docker_plugin_alias = docker_plugin_alias
        self._managers = dataset_manager_collection
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
        all_dataset = self._managers.known_datasets()
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
            for _ in range(5):
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


class ServiceManager:
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

    def __init__(
        self,
        job_util: JobUtil,
        dataset_manager_collection: DatasetManagerCollection,
        dataset_inquery_util: DatasetInqueryUtil,
    ):
        self._job_util = job_util
        self._managers: DatasetManagerCollection = dataset_manager_collection
        self._dataset_inquery_util: DatasetInqueryUtil = dataset_inquery_util

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

    async def _async_process_data_request(self, message: DatasetManagementMessage, websocket: WebSocket) -> DatasetManagementResponse:
        """
        Process and respond to a ::class:`ManagementAction` ``REQUEST_DATA`` dataset management message.

        Process a ::class:`DatasetManagementMessage` having the ``REQUEST_DATA`` action, sending back the data over the
        supplied websocket connection if possible via ::class:`DataTransmitMessage` objects. If data cannot be provided,
        or once it has been, finish by returning (but not actually sending) a ::class:`DatasetManagementResponse` that
        reflects the result.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message requesting some data from the service.
        websocket
            The websocket connection over which to transmit data when this is possible.

        Returns
        -------
        DatasetManagementResponse
            A response message indicating the success or failure of the request for data.
        """
        # Check if the data request can actually be fulfilled
        can_provide: BasicResultIndicator = await self._dataset_inquery_util.async_can_provide_data(
            dataset_name=message.dataset_name, data_item_name=message.data_location)
        if not can_provide.success:
            return DatasetManagementResponse(action=message.management_action, success=can_provide.success,
                                             reason=can_provide.reason, message=can_provide.message)

        chunk_size = 1024
        manager = self._managers.known_datasets()[message.dataset_name].manager
        chunking_keys = manager.data_chunking_params
        if chunking_keys is None:
            raw_data = manager.get_data(dataset_name=message.dataset_name, item_name=message.data_location)
            transmit = DataTransmitMessage(data=raw_data, series_uuid=uuid4(), is_last=True)
            await websocket.send_json(transmit.to_dict())
            response = DataTransmitResponse.factory_init_from_deserialized_json(await websocket.receive_json())
        else:
            offset = 0
            actual_length = chunk_size
            while actual_length == chunk_size:
                chunk_params = {chunking_keys[0]: offset, chunking_keys[1]: chunk_size}
                raw_data = manager.get_data(message.dataset_name, message.data_location, **chunk_params)
                offset += chunk_size
                actual_length = len(raw_data)
                transmit = DataTransmitMessage(data=raw_data, series_uuid=uuid4(), is_last=True)
                await websocket.send_json(transmit.to_dict())
                json_response = await websocket.receive_json()
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

    async def _async_process_dataset_search(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Process a ``SEARCH`` management message for a dataset to search for a appropriate dataset.

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
        dataset = await self._dataset_inquery_util.async_find_dataset_for_requirement(requirement)
        if isinstance(dataset, Dataset):
            return DatasetManagementResponse(action=message.management_action, dataset_name=dataset.name, success=True,
                                             reason='Qualifying Dataset Found', data_id=str(dataset.uuid))
        else:
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason='No Qualifying Dataset Found')

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
        if message.dataset_name in self._managers.known_datasets():
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="Dataset Already Exists", dataset_name=message.dataset_name)
        # Handle when message to create fails to include a dataset domain
        elif message.data_domain is None:
            msg = "Invalid {} for dataset creation: no dataset domain provided.".format(message.__class__.__name__)
            return DatasetManagementResponse(action=message.management_action, success=False, message=msg,
                                             reason="No Dataset Domain", dataset_name=message.dataset_name)

        dataset_type = self._determine_dataset_type(message)

        # Create the dataset
        try:
            dataset = self._managers.manager(dataset_type).create(name=message.dataset_name,
                                                                   category=message.data_category,
                                                                   domain=message.data_domain, is_read_only=False)
            # TODO: determine if there is an expectation to find data
            # TODO:     if so, attempt to find data, setting pending response based on result
            return DatasetManagementResponse(action=message.management_action, success=True, reason="Dataset Created",
                                             data_id=str(dataset.uuid), dataset_name=dataset.name,
                                             is_awaiting=message.is_pending_data)
        # Do something a little differently for this particular known special cases
        except ValueError as e:
            # TODO: (later) strictly speaking, this or something similar will probably applies to AWS S3 datasets later;
            #   see https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
            if str(e) == f"invalid bucket name {message.dataset_name}" and dataset_type == DatasetType.OBJECT_STORE:
                return DatasetManagementResponse(action=message.management_action, success=False,
                                                 reason="Unsupported Name For Backing Storage Type",
                                                 dataset_name=message.dataset_name, is_awaiting=message.is_pending_data,
                                                 message=f"Datasets of {dataset_type.name} type have additional name "
                                                         f"restrictions; names can consist only of lowercase letters, "
                                                         f"numbers, and hyphens (-)")
            else:
                return DatasetManagementResponse(action=message.management_action, success=False, message=str(e),
                                                 reason=f"Encountered {e.__class__.__name__}",
                                                 dataset_name=message.dataset_name, is_awaiting=message.is_pending_data)
        except Exception as e:
            return DatasetManagementResponse(action=message.management_action, success=False, message=str(e),
                                             reason=f"Encountered {e.__class__.__name__}",
                                             dataset_name=message.dataset_name, is_awaiting=message.is_pending_data)

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
        known_datasets = self._managers.known_datasets()
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
        manager = self._managers.known_datasets()[dataset_name].manager
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
        if message.dataset_name and message.dataset_name not in self._managers.known_datasets():
            return DatasetManagementResponse(action=message.management_action, success=False,
                                             reason="Dataset Not Found", dataset_name=message.dataset_name)
        query_type = message.query.query_type
        if query_type == QueryType.LIST_FILES:
            dataset_name = message.dataset_name
            list_of_files = self._managers.known_datasets()[dataset_name].manager.list_files(dataset_name)
            return DatasetManagementResponse(action=message.management_action, success=True, dataset_name=dataset_name,
                                             reason=f'Obtained {dataset_name} Items List',
                                             data={"query_results": {QueryType.LIST_FILES.name: list_of_files}})
        elif query_type == QueryType.GET_STATE:
            return DatasetManagementResponse(action=message.management_action, success=True,
                                             dataset_name=message.dataset_name,
                                             reason=f'Obtained {message.dataset_name} State',
                                             data={"dataset_state": self._managers.known_datasets()[message.dataset_name]})
            # TODO: (later) add support for messages with other query types also
        else:
            reason = 'Unsupported {} Query Type - {}'.format(DatasetQuery.__class__.__name__, query_type.name)
            return DatasetManagementResponse(action=message.management_action, success=False, reason=reason)

    async def listener(self, websocket: WebSocket):
        """
        Process incoming messages over the websocket and respond appropriately.
        """
        # wait for websocket handshake. this must be done
        await websocket.accept()
        try:
            # We may need to lazily load a dataset manager
            dataset_manager = None
            dest_dataset_name = None
            dest_item_name = None
            transmit_series_uuid = None
            partial_indx = 0
            async for data in websocket.iter_json():
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
                    assert dataset_manager is not None, "Dataset manager should not be 'None' at this point"
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
                    dataset_names = self._dataset_inquery_util.get_dataset_names(sort_result=True)
                    response = DatasetManagementResponse(action=ManagementAction.LIST_ALL, success=True,
                                                         reason='List Assembled', data={'datasets': dataset_names})
                elif inbound_message.management_action == ManagementAction.SEARCH:
                    response = await self._async_process_dataset_search(message=inbound_message)
                # TODO: (later) properly handle additional incoming messages
                else:
                    msg = "Unsupported data management message action {}".format(inbound_message.management_action)
                    response = DatasetManagementResponse(action=inbound_message.management_action, success=False,
                                                         reason="Unsupported Action", message=msg)
                await websocket.send_json(response.to_dict())
        # TODO: look into moving error handling to a middleware
        except json.JSONDecodeError as e:
            response = DatasetManagementResponse(action=ManagementAction.UNKNOWN, success=False,
                                                 reason="Invalid encoding", message="Invalid json encoding")
            # TODO: write custom `ws.iter_json` method that allows pulling out the data that could not be deserialized
            logging.info("Received invalid json")
            await websocket.send_json(response.to_dict())
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
         # TODO: handle logging
         # TODO: handle exceptions appropriately
        except TypeError as te:
            logging.error("Problem with object types when processing received message", te)
        # TODO: provide a way to catch this. improve handling / logging
        #except websockets.exceptions.ConnectionClosed:
        #    logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.error("Cancelling listener task")
        except Exception as e:
            logging.error("Encountered error: {}".format(str(e)))
        finally:
            # SAFETY: this is idempotent
            await websocket.close()


class RequiredDataChecksManager:
    """
    Async task that periodically examines whether required data for jobs is available.
    Start the task by calling ::method:`start`.

    Parameters
    ----------
    job_util : JobUtil
        Access and update jobs
    dataset_manager_collection : DatasetManagerCollection
        Facilitates creating and accessing Datasets
    checks_underway_tracker : ActiveOperationTracker
        Semaphore-like object for signaling that data checks are underway
    dataset_inquery_util : DatasetInqueryUtil
        Facilitates dataset detail queries and searches
    """
    def __init__(
        self,
        job_util: JobUtil,
        dataset_manager_collection: DatasetManagerCollection,
        checks_underway_tracker: "ActiveOperationTracker",
        dataset_inquery_util: DatasetInqueryUtil,
    ):
        self._job_util = job_util
        self._managers = dataset_manager_collection
        self._checks_underway_tracker = checks_underway_tracker
        self._dataset_inquery_util: DatasetInqueryUtil = dataset_inquery_util

    async def start(self) -> NoReturn:
        await self._manage_required_data_checks()

    async def _manage_required_data_checks(self):
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
                    job.set_status_step(JobExecStep.AWAITING_PARTITIONING if job.cpu_count > 1 else JobExecStep.AWAITING_ALLOCATION)
                else:
                    logging.error("Some or all required data for {} is unprovideable.".format(job.job_id))
                    job.set_status_step(JobExecStep.DATA_UNPROVIDEABLE)
                # Regardless, save the updated job state
                try:
                    self._job_util.save_job(job)
                except:
                    # TODO: logging would be good, and perhaps maybe retries
                    pass
            self._job_util.unlock_active_jobs(lock_id)
            await asyncio.sleep(5)

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
        # TODO: aaraney harden
        for i in range(len(job.model_request.output_formats)):

            id_restrict = DiscreteRestriction(variable=StandardDatasetIndex.ELEMENT_ID, values=[])

            time_range = None
            for data_domain in [req.domain for req in job.data_requirements if req.category == DataCategory.FORCING]:
                time_restrictions = [r for k, r in data_domain.continuous_restrictions.items() if r.variable == 'Time']
                if len(time_restrictions) > 0:
                    time_range = time_restrictions[0]
                    break

            # TODO: (later) more intelligently determine type
            dataset_type = DatasetType.OBJECT_STORE
            mgr = self._managers.manager(dataset_type)

            data_format = job.model_request.output_formats[i]
            # If we are writing to an object store, lots of CSV files will kill us, so switch to archived variant
            if dataset_type == DatasetType.OBJECT_STORE and data_format == DataFormat.NGEN_CSV_OUTPUT:
                data_format = DataFormat.ARCHIVED_NGEN_CSV_OUTPUT

            dataset = mgr.create(name='job-{}-output-{}'.format(job.job_id, i),
                                 is_read_only=False,
                                 category=DataCategory.OUTPUT,
                                 domain=DataDomain(data_format=data_format,
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

    async def perform_checks_for_job(self, job: Job) -> bool:
        """
        Check whether all requirements for this job can be fulfilled, setting fulfillment associations and usage links.

        Check whether all the requirements for the provided job can be fulfilled, such that the job can move on to the
        next successful step in the execution workflow.  Potentially do some other tracking and linking steps as well,
        depending on whether the fulfilling dataset already exists.

        When an existing dataset is found to fulfill a ::class:`DataRequirement`, update the requirement object with the
        name of the fulfilling dataset and the location at which the dataset will be accessible to the job.
        Additionally, link the fulfilling dataset to a ::class:`JobDatasetUser` for the provided job.

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
        # Ensure here that we block mark-and-sweep routing for temporary datasets
        self._checks_underway_tracker.acquire()
        try:
            # Create/lookup dataset user job wrapper instance for this job
            existing_ds_users: Dict[UUID, DatasetUser] = _get_ds_users(self._managers)
            job_uuid = UUID(job.job_id)
            job_ds_user = existing_ds_users.get(job_uuid, JobDatasetUser(job_uuid))

            for requirement in [req for req in job.data_requirements if req.fulfilled_by is None]:
                can_fulfill, dataset = await self._dataset_inquery_util.can_be_fulfilled(requirement=requirement,
                                                                                         job=job)
                if not can_fulfill:
                    logging.error("Cannot fulfill '{}' category data requirement".format(requirement.category.name))
                    return False
                elif dataset is not None:
                    # Link user when we've found an existing fulfilling dataset
                    job_ds_user.link_to_dataset(dataset=dataset)
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
        finally:
            # Unblock mark and sweep
            self._checks_underway_tracker.release()

class TempDataTaskManager:
    """
    Async task that purges and prolongs the expiration of temporary datasets.

    Start the task by calling ::method:`start`.

    Parameters
    ----------
    dataset_manager_collection : DatasetManagerCollection
        Facilitates creating and accessing Datasets
    safe_to_exec_tracker : ActiveOperationTracker
        Used to determine if it is okay to purge or prolong temporary datasets
    """

    def __init__(self, dataset_manager_collection: DatasetManagerCollection, safe_to_exec_tracker: "ActiveOperationTracker"):
        self._safe_to_exec_tracker = safe_to_exec_tracker
        self._managers = dataset_manager_collection

        self._marked_expired_datasets: Set[str] = set()
        """ Names of expired datasets marked for deletion the next time through ::method:`manage_temp_datasets`. """

    async def start(self) -> NoReturn:
        await self._manage_temp_datasets()

    async def _manage_temp_datasets(self) -> NoReturn:
        """
        Async task for managing temporary datasets, including updating expire times and purging of expired datasets.
        """
        while True:
            # Ensure that mark and sweep doesn't proceed while something is potentially to linking datasets
            while self._safe_to_exec_tracker.value > 0:
                await asyncio.sleep(10)
            self._temp_dataset_mark_and_sweep()
            await asyncio.sleep(3600)

    def _temp_dataset_mark_and_sweep(self):
        """
        Encapsulation of the required behavior for a single iteration through ::method:`manage_temp_datasets`.

        Method scans for in use temporary datasets, updating the expire times of each.  It then deletes any expired
        datasets marked for deletion already within the instance's private field.  Finally, it updates the instance's
        private field for marked-for-deletion datasets with any that are now expired (and thus will be removed on the
        next invocation).
        """
        # Get these upfront, since no meaningful changes can happen during the course of an iteration
        temp_datasets = {ds_name: ds for ds_name, ds in self._managers.known_datasets().items() if ds.is_temporary}

        # Account for any in-use temporary datasets by potentially unmarking and updating expire time
        for ds in (ds for _, ds in temp_datasets.items() if ds.manager.get_user_ids_for_dataset(ds)):
            if ds.name in self._marked_expired_datasets:
                self._marked_expired_datasets.remove(ds.name)

            assert ds.expires is not None
            ds.extend_life(timedelta(days=1) if ds.expires < (datetime.now()+timedelta(days=1)) else timedelta(hours=1))

        # Delete any datasets previously marked for deletion
        for ds in (temp_datasets.pop(ds_name) for ds_name in self._marked_expired_datasets):
            ds.manager.delete(dataset=ds)

        # Mark any expired datasets for deletion on the next iteration
        self._marked_expired_datasets.update(n for n, ds in temp_datasets.items() if ds.expires > datetime.now())

class DataProvisionManager:
    """
    Task method to periodically associate, un-associate, and (when needed) generate required datasets with/for jobs.
    Start the task by calling ::method:`start`.

    Parameters
    ----------
    job_util : JobUtil
        Access and update jobs
    dataset_manager_collection : DatasetManagerCollection
        Facilitates creating and accessing Datasets
    docker_s3fs_helper : DockerS3FSPluginHelper
        Facilitates initialize Docker volumes for jobs
    data_derive_util : DataDeriveUtil
        Facilitates deriving data and datasets
    provision_underway_tracker: ActiveOperationTracker
        Semaphore-like object for signaling that provisioning is underway
    """
    def __init__(
        self,
        job_util: JobUtil,
        dataset_manager_collection: DatasetManagerCollection,
        docker_s3fs_helper: DockerS3FSPluginHelper,
        data_derive_util: DataDeriveUtil,
        provision_underway_tracker: "ActiveOperationTracker",
    ):
        self._job_util = job_util
        self._managers = dataset_manager_collection
        self._docker_s3fs_helper = docker_s3fs_helper
        self._provision_underway_tracker = provision_underway_tracker
        self._data_derive_util: DataDeriveUtil = data_derive_util

    async def start(self) -> NoReturn:
        await self._manage_data_provision()

    async def _manage_data_provision(self):
        """
        Task method to periodically associate, un-associate, and (when needed) generate required datasets with/for jobs.
        """
        logging.debug("Starting task loop for performing data provisioning for requested jobs.")
        while True:
            lock_id = str(uuid4())
            while not self._job_util.lock_active_jobs(lock_id):
                await asyncio.sleep(2)

            # Get any previously existing dataset users linked to any of the managers
            prior_users: Dict[UUID, DatasetUser] = _get_ds_users(self._managers)

            for job in [j for j in self._job_util.get_all_active_jobs() if j.status_step == JobExecStep.AWAITING_DATA]:
                logging.debug("Managing provisioning for job {} that is awaiting data.".format(job.job_id))
                try:
                    # Block temp dataset purging and maintenance while we handle things here
                    self._provision_underway_tracker.acquire()
                    # Derive any datasets as required
                    reqs_w_derived_datasets = await self._data_derive_util.derive_datasets(job)
                    logging.info('Job {} had {} datasets derived.'.format(job.job_id, len(reqs_w_derived_datasets)))

                    # Create or retrieve dataset user job wrapper instance and link associated, newly-derived datasets
                    # It should be the case that pre-existing datasets were linked when found to be fulfilling
                    known_ds = self._managers.known_datasets()
                    job_uuid = UUID(job.job_id)
                    job_ds_user = prior_users[job_uuid] if job_uuid in prior_users else JobDatasetUser(job_uuid)
                    for ds in (known_ds[req.fulfilled_by] for req in reqs_w_derived_datasets if req.fulfilled_by):
                        job_ds_user.link_to_dataset(ds)

                    # Initialize dataset Docker volumes required for a job
                    logging.debug('Initializing any required S3FS dataset volumes for {}'.format(job.job_id))
                    self._docker_s3fs_helper.init_volumes(job=job)
                except Exception:
                    job.set_status_step(JobExecStep.DATA_FAILURE)
                    self._job_util.save_job(job)
                    continue
                finally:
                    self._provision_underway_tracker.release()

                job.set_status_step(JobExecStep.AWAITING_SCHEDULING)
                self._job_util.save_job(job)

            # Also, unlink usage for any previously existing, job-based users for which the job is no longer active ...
            self._unlink_finished_jobs(ds_users=prior_users)

            self._job_util.unlock_active_jobs(lock_id)
            await asyncio.sleep(5)

    def _unlink_finished_jobs(self, ds_users: Dict[UUID, DatasetUser]) -> Set[UUID]:
        """
        Unlink dataset use for any provided job-based users for which the job is no longer active.

        Unlink dataset use for any of the given dataset users that are specifically ::class`JobDatasetUser` and are
        associated with a job that is not in the set of active jobs.

        Parameters
        ----------
        ds_users: Dict[UUID, DatasetUser]
            A mapping of applicable dataset user objects, mapped by uuid; for the subset of interest, which are
            ::class`JobDatasetUser` instances, the key will also be the id of the associated job (as a ::class:`UUID`).

        Returns
        -------
        Set[UUID]
            Set of the UUIDs of all users associated with finished jobs for which unlinking was performed.
        """
        finished_job_users: Set[UUID] = set()
        active_job_ids = {UUID(j.job_id) for j in self._job_util.get_all_active_jobs()}
        for user in (u for uid, u in ds_users.items() if isinstance(u, JobDatasetUser) and uid not in active_job_ids):
            for ds in (self._managers.known_datasets()[ds_name] for ds_name in user.datasets_and_managers):
                user.unlink_to_dataset(ds)
            finished_job_users.add(user.uuid)
        return finished_job_users

def _get_ds_users(managers: DatasetManagerCollection) -> Dict[UUID, DatasetUser]:
    """
    Get dataset users from all associated managers of the service.

    Returns
    -------
    Dict[UUID, DatasetUser]
        Map of all ::class:`DatasetUser` from all associated managers of the service, keyed by the UUID of each.
    """
    return {uuid: mgr.get_dataset_user(uuid)
            for _, mgr in managers.managers() for uuid in mgr.get_dataset_user_ids()}

# TODO: replace with RWLock implementation
class ActiveOperationTracker:
    """
    Unbound Semaphore-like synchronization object for counting acquisitions and releases. Unlike a
    semaphore, neither `acquire()` nor `release()` block. `acquire()` and `release()` increment and
    decrement an internal value respectively. The internal count can be read via the `value`
    property. Unlike most semaphore implementations, `value` < 0 does not throw.

    Example:
        def foo(tracker: ActiveOperationTracker):
            tracker.acquire()
            # do something e.g. contact data store
            tracker.release()

        def bar(tracker: ActiveOperationTracker):
            while tracker.value > 0:
                sleep(5)
            # do something
    """
    def __init__(self, value: int = 0):
        self._count = value

    def acquire(self):
        self._count += 1

    def release(self):
        self._count -= 1

    @property
    def value(self) -> int:
        return self._count
