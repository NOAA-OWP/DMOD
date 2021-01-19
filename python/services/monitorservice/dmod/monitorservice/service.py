#!/usr/bin/env python3
from websockets import WebSocketServerProtocol
from dmod.communication import WebSocketInterface
from dmod.monitor import Monitor
import logging


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class MonitorService(WebSocketInterface):
    """
    Core class of the monitor service, handling communication and main logic.
    """
    def __init__(self, monitor: Monitor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitor = monitor

    async def exec_monitoring(self):
        """
        Async task performing repeating, regular monitoring tasks within service.
        """
        # TODO:
        pass

    async def listener(self, websocket: WebSocketServerProtocol, path):
        # TODO: figure out what this might listen for and need to communicate
        pass

