import asyncio
import json
from dmod.communication import DatasetManagementMessage, DatasetManagementResponse, ManagementAction, MessageEventType,\
    WebSocketInterface, UnsupportedMessageTypeResponse
from dmod.core.exception import DmodRuntimeError
from dmod.modeldata.data.object_store_dataset import Dataset, DatasetManager, ObjectStoreDataset, \
    ObjectStoreDatasetManager
from typing import Dict, Type, TypeVar
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
        self._known_dataset_names: Dict[str, Type[DATASET_TYPE]] = {}
        """ Map of names (key) of datasets known to this service, to each dataset's type (value). """
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
        if not self._known_dataset_names.keys().isdisjoint(manager.datasets.keys()):
            duplicates = set(self._known_dataset_names.keys()).intersection(manager.datasets.keys())
            msg = "Can't add {} to service with already known dataset names {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        if not manager.supported_dataset_types.isdisjoint(self._all_data_managers.keys()):
            duplicates = manager.supported_dataset_types.intersection(self._all_data_managers.keys())
            msg = "Can't add new {} to service for managing already managed dataset types {}."
            raise DmodRuntimeError(msg.format(manager.__class__.__name__, duplicates))

        # We've already done sanity checking for duplicates, so just add things.
        for name, dataset in manager.datasets.items():
            self._known_dataset_names[name] = dataset.__class__
        for dataset_type in manager.supported_dataset_types:
            self._all_data_managers[dataset_type] = manager

    def init_object_store_dataset_manager(self, obj_store_host: str, access_key: str, secret_key: str):
        self._obj_store_data_mgr = ObjectStoreDatasetManager(obj_store_host_str=obj_store_host, access_key=access_key,
                                                             secret_key=secret_key)
        self._obj_store_access_key = access_key
        self._obj_store_secret_key = secret_key

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Process incoming messages over the websocket and respond appropriately.
        """
        try:
            message = await websocket.recv()
            data = json.loads(message)

            # TODO: properly handle incoming messages
            #  - create dataset
            #  - query whether data to satisfy a set of requirements is available

            # TODO: (later) properly handle additional incoming messages
            #  - delete dataset
            #  - add data to dataset
            #  - query for list of dataset names (and possibly types and categories)
            response = UnsupportedMessageTypeResponse(actual_event_type=MessageEventType.INVALID,
                                                      listener_type=self.__class__,
                                                      message="Listener protocol not yet implemented",
                                                      data=data)
            await websocket.send(str(response))

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

