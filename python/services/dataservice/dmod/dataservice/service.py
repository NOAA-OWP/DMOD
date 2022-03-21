import asyncio
import json
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, MessageEventType,\
    WebSocketInterface, UnsupportedMessageTypeResponse
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_dataset import Dataset, DatasetManager, ObjectStoreDataset, \
    ObjectStoreDatasetManager
from typing import Dict, Type, TypeVar
from uuid import UUID
from websockets import WebSocketServerProtocol


DATASET_MGR = TypeVar('DATASET_MGR', bound=DatasetManager)
DATASET_TYPE = TypeVar('DATASET_TYPE', bound=Dataset)


class ServiceManager(WebSocketInterface):
    """
    Primary service management class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._all_data_managers: Dict[Type[DATASET_TYPE], DatasetManager] = {}
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

    async def _handle_data_creation(self, message: DatasetManagementMessage, websocket: WebSocketServerProtocol):
        """
        As part of the communication protocol for the service, handle incoming messages that request dataset creation.

        Parameters
        ----------
        message : DatasetManagementMessage
            The message that initiated the process of creating a new dataset
        websocket : WebSocketServerProtocol
            The websocket over which the communication protocol messages are sent and received.
        """
        # Make sure there is no conflict/existing dataset already
        if message.dataset_name in self.get_known_datasets():
            response = DatasetManagementResponse(success=False, reason="Dataset Already Exists")
            await websocket.send(str(response))
            return

        # Handle when message to create fails to include a dataset domain
        if message.data_domain is None:
            msg = "Invalid {} for dataset creation: no dataset domain provided.".format(self.__class__.__name__)
            response = DatasetManagementResponse(success=False, reason="No Dataset Domain", message=msg)
            await websocket.send(str(response))
            return

        # Create the dataset
        dataset_type = self._determine_dataset_type(message)
        self._all_data_managers[dataset_type].create(name=message.dataset_name, category=message.data_category,
                                                     domain=message.data_domain, is_read_only=False)

        response = DatasetManagementResponse(success=True, reason="Dataset Created", is_awaiting=False)
        await websocket.send(str(response))
        return

    def get_known_datasets(self) -> Dict[str, Dataset]:
        """
        Get all datasets known to the service via its manager objects, in a map keyed by dataset name.

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
            message = await websocket.recv()
            data = json.loads(message)
            mgr_msg = DatasetManagementMessage.factory_init_from_deserialized_json(data)

            # If we were not able to otherwise process the message into a response, then it is unsupported
            if mgr_msg is None:
                response = UnsupportedMessageTypeResponse(actual_event_type=MessageEventType.INVALID,
                                                          listener_type=self.__class__,
                                                          message="Listener protocol not yet implemented",
                                                          data=data)
                await websocket.send(str(response))
            elif mgr_msg.management_action == ManagementAction.CREATE:
                await self._handle_data_creation(message=mgr_msg, websocket=websocket)
            else:
                msg = "Unsupported data management message action {}".format(mgr_msg.management_action)
                response = DatasetManagementResponse(success=False, reason="Unsupported Action", message=msg)
                await websocket.send(str(response))

            # TODO: (later) properly handle additional incoming messages

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
        while True:
            # TODO: implement
            await asyncio.sleep(30)

