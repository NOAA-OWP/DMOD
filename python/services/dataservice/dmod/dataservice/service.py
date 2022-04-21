import asyncio
import json
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, WebSocketInterface
from dmod.core.meta_data import DataRequirement
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_dataset import Dataset, DatasetManager, ObjectStoreDataset, \
    ObjectStoreDatasetManager
from dmod.scheduler.job import JobExecStep, JobUtil
from typing import Dict, Optional, Tuple, Type, TypeVar
from uuid import UUID
from websockets import WebSocketServerProtocol


DATASET_MGR = TypeVar('DATASET_MGR', bound=DatasetManager)
DATASET_TYPE = TypeVar('DATASET_TYPE', bound=Dataset)


class ServiceManager(WebSocketInterface):
    """
    Primary service management class.
    """

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

    async def _async_can_dataset_be_derived(self, requirement: DataRequirement) -> bool:
        """
        Asynchronously determine if a dataset can be derived from existing datasets to fulfill this requirement.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirement : DataRequirement
            The requirement that needs to be fulfilled.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill this requirement.

        See Also
        -------
        ::method:`can_dataset_be_derived`
        """
        return self.can_dataset_be_derived(requirement)

    async def _async_find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Asynchronously search for an existing dataset that will fulfill this requirement.

        This function essentially just provides an async wrapper around the synchronous analog.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The dataset fulfilling the requirement, if one is found; otherwise ``None``.

        See Also
        -------
        ::method:`find_dataset_for_requirement`
        """
        return self.find_dataset_for_requirement(requirement)

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
            return DatasetManagementResponse(success=False, reason="Unparseable Message Received")
        elif message.management_action != ManagementAction.ADD_DATA:
            msg_txt = "Expected {} action but received {}".format(ManagementAction.ADD_DATA, message.management_action)
            return DatasetManagementResponse(success=False, reason="Unexpected Management Action", message=msg_txt)
        elif message.data is None:
            return DatasetManagementResponse(success=False, reason="No Data In ADD_DATA Message")
        elif mngr.add_data(message.dataset_name, dest=message.data_location, data=message.data):
            return DatasetManagementResponse(success=True, reason="Data Added", is_awaiting=message.is_pending_data)
        else:
            return DatasetManagementResponse(success=False, reason="Failure Adding Data To Dataset", is_awaiting=False)

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
            return DatasetManagementResponse(success=False, reason="Dataset Already Exists")
        # Handle when message to create fails to include a dataset domain
        elif message.data_domain is None:
            msg = "Invalid {} for dataset creation: no dataset domain provided.".format(message.__class__.__name__)
            return DatasetManagementResponse(success=False, reason="No Dataset Domain", message=msg)

        # Create the dataset
        dataset_type = self._determine_dataset_type(message)
        self._all_data_managers[dataset_type].create(name=message.dataset_name, category=message.data_category,
                                                     domain=message.data_domain, is_read_only=False)
        return DatasetManagementResponse(success=True, reason="Dataset Created", is_awaiting=message.is_pending_data)

    async def can_be_fulfilled(self, requirement: DataRequirement) -> Tuple[bool, Optional[str]]:
        """
        Determine whether this requirement for this job can be fulfilled, either directly or by deriving a new dataset.

        The returned tuple will return two items.  The first is whether the data requirement can be fulfilled given the
        currently existing datasets.  The second is the name of the fulfilling dataset, if a fulfilling dataset already
        exists.  If data among known datasets is sufficient to fulfill the requirement, but deriving a new dataset is
        necessary (e.g., in a different format, or by combining data from multiple datasets), then the second value will
        be ``None``.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement in question that needs to be fulfilled.

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple of whether the requirement can be fulfilled and, if one exists, the name of the fulfilling dataset.
        """
        fulfilling_dataset = await self._async_find_dataset_for_requirement(requirement)
        if isinstance(fulfilling_dataset, Dataset):
            return True, fulfilling_dataset.name
        else:
            return await self._async_can_dataset_be_derived(requirement), None

    def can_dataset_be_derived(self, requirement: DataRequirement) -> bool:
        """
        Determine if it is possible for a dataset to be derived from existing datasets to fulfill this requirement.

        Parameters
        ----------
        requirement : DataRequirement
            The requirement that needs to be fulfilled.

        Returns
        -------
        bool
            Whether it is possible for a dataset to be derived from existing datasets to fulfill this requirement.
        """
        return False

    def find_dataset_for_requirement(self, requirement: DataRequirement) -> Optional[Dataset]:
        """
        Search for an existing dataset that will fulfill this requirement.

        Parameters
        ----------
        requirement : DataRequirement
            The data requirement that needs to be fulfilled.

        Returns
        -------
        Optional[Dataset]
            The dataset fulfilling the requirement, if one is found; otherwise ``None``.
        """
        for name, dataset in self.get_known_datasets().items():
            if dataset.category == requirement.category and dataset.data_domain.contains(requirement.domain):
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

    def init_object_store_dataset_manager(self, obj_store_host: str, access_key: str, secret_key: str):
        mgr = ObjectStoreDatasetManager(obj_store_host_str=obj_store_host, access_key=access_key, secret_key=secret_key)
        self._add_manager(mgr)
        self._obj_store_data_mgr = mgr

        self._obj_store_access_key = access_key
        self._obj_store_secret_key = secret_key

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Process incoming messages over the websocket and respond appropriately.
        """
        try:
            is_awaiting = True
            # We may need to lazily load a dataset manager
            dataset_manager = None
            while is_awaiting:
                message = await websocket.recv()
                data = json.loads(message)
                mgr_msg = DatasetManagementMessage.factory_init_from_deserialized_json(data)

                # If we were not able to otherwise process the message into a response, then it is unsupported
                if mgr_msg is None:
                    response = DatasetManagementResponse(success=False, reason="Unparseable Message Received")
                elif mgr_msg.management_action == ManagementAction.CREATE:
                    response = await self._async_process_dataset_create(message=mgr_msg)
                elif mgr_msg.management_action == ManagementAction.ADD_DATA:
                    # Lazily load the right manager when needed
                    if dataset_manager is None:
                        dataset_manager = self.get_known_datasets()[mgr_msg.dataset_name].manager
                    response = await self._async_process_add_data(message, dataset_manager)
                else:
                    msg = "Unsupported data management message action {}".format(mgr_msg.management_action)
                    response = DatasetManagementResponse(success=False, reason="Unsupported Action", message=msg)
                await websocket.send(str(response))
                is_awaiting = response.is_awaiting

        # TODO: handle logging
        # TODO: handle exceptions appropriately
        except TypeError as te:
            #logging.error("Problem with object types when processing received message", te)
            pass
        #except websockets.exceptions.ConnectionClosed:
            #logging.info("Connection Closed at Consumer")
        #except asyncio.CancelledError:
        #    logging.info("Cancelling listener task")

    async def manage_required_data_checks(self):
        """
        Task method to periodically examine whether required data for jobs is available.

        Method is expected to be a long-running async task.  In its main routine, it iterates through the job-level
        ::class:`DataRequirement`, in each active job in the ``AWAITING_DATA_CHECK`` ::class:`JobExecStep`.  For each 
        job, it checks whether each individual requirement can be fulfilled, updating the requirement's 
        ::attribute:`DataRequirement.fulfilled_by` property if so.  However, as soon as any requirement is found that
        cannot be fulfilled, the function breaks out of the inner loop through the current job's requirements, moving
        that job to the ``DATA_UNPROVIDEABLE`` step and continuing to the next job to process.

        Assuming iterations for all possible requirements of the current job are processed, with all requirements found
        the be fulfillable, the current job is moved to the ``AWAITING_ALLOCATION`` step.  The routine then advances to
        the next iteration in the outer job loop. 

        After all active jobs have been processed, the function sleeps for a brief period, then repeats its routine.
        """
        while True:
            for job in self._job_util.get_all_active_jobs():
                if job.status_step != JobExecStep.AWAITING_DATA_CHECK:
                    continue
                for requirement in job.data_requirements:
                    # TODO: (later) do we need to check whether this dataset exists, or handle this differently?
                    if requirement.fulfilled_by is not None:
                        continue
                    can_fulfill, dataset_name = await self.can_be_fulfilled(requirement)
                    # When this can't be fulfilled, update status appropriately
                    # Also, we don't need to bother checking the other requirements, so break inner loop
                    if not can_fulfill:
                        job.status_step = JobExecStep.DATA_UNPROVIDEABLE
                        break
                    # Also if can fulfill and already a specific existing dataset that will, associate with requirement
                    elif dataset_name is not None:
                        requirement.fulfilled_by = dataset_name
                # If we didn't deem job as `DATA_UNPROVIDEABLE`, then check is good, so move to `AWAITING_ALLOCATION`
                if job.status_step != JobExecStep.DATA_UNPROVIDEABLE:
                    job.status_step = JobExecStep.AWAITING_ALLOCATION
                # Regardless, save the updated job state
                self._job_util.save_job(job)
            await asyncio.sleep(30)

