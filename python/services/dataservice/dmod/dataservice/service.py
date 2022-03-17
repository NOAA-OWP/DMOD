import asyncio
import json
from dmod.communication import WebSocketInterface, MessageEventType, UnsupportedMessageTypeResponse
from dmod.modeldata.data.object_store_dataset import ObjectStoreDatasetManager
from typing import List
from websockets import WebSocketServerProtocol


class ServiceManager(WebSocketInterface):
    """
    Primary service management class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj_store_data_mgr = None
        self._obj_store_access_key = None
        self._obj_store_secret_key = None

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

