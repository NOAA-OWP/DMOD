import asyncio
import json
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, WebSocketInterface
from dmod.core.meta_data import DataCategory, DataDomain, DataRequirement, DiscreteRestriction
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_dataset import Dataset, DatasetManager, ObjectStoreDataset, \
    ObjectStoreDatasetManager
from dmod.scheduler.job import Job, JobExecStep, JobUtil
from typing import Dict, List, Optional, Tuple, Type, TypeVar
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

    async def _async_dataset_search(self, message: DatasetManagementMessage) -> DatasetManagementResponse:
        """
        Search for a dataset that fulfills the requirements of this ::class:`ManagementAction` ``SEARCH`` message.

        Parameters
        ----------
        message : DatasetManagementResponse
            A data management message with the ``SEARCH`` :class:`ManagementAction` set.

        Returns
        -------
        DatasetManagementResponse
            A response indicating the success of the search and, if successful, the
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
                    response = DatasetManagementResponse(action=ManagementAction.UNKNOWN, success=False,
                                                         reason="Unparseable Message Received")
                elif mgr_msg.management_action == ManagementAction.CREATE:
                    response = await self._async_process_dataset_create(message=mgr_msg)
                elif mgr_msg.management_action == ManagementAction.ADD_DATA:
                    # Lazily load the right manager when needed
                    if dataset_manager is None:
                        dataset_manager = self.get_known_datasets()[mgr_msg.dataset_name].manager
                    response = await self._async_process_add_data(message, dataset_manager)
                elif mgr_msg.management_action == ManagementAction.SEARCH:
                    response = await self._async_dataset_search(message=mgr_msg)
                else:
                    msg = "Unsupported data management message action {}".format(mgr_msg.management_action)
                    response = DatasetManagementResponse(action=mgr_msg.management_action, success=False,
                                                         reason="Unsupported Action", message=msg)
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

