#!/usr/bin/env python3

"""
Author: Nels Frazier
Date: November 25, 2019

This module provides communication interfaces for reuse across components.
Currently, a WebSocketInterface implementing asyncio event handling acros SSL
connections is provided, with an abstract listener method required by subclasses.

"""

from abc import ABC, abstractmethod
import asyncio
import websockets
import ssl
import signal
import logging
from pathlib import Path
from websockets import WebSocketServerProtocol

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class WebSocketInterface(ABC):
    """
    SSL Enabeled aysncio server interface

    Attributes
    ----------
    loop: aysncio event loop

    signals: list-like
        List of signals (from the signal package) this handler will use to shutdown

    ssl_context:
        ssl context for websocket

    server:
        websocket server
    """
    @abstractmethod
    def listener(self, websocket: WebSocketServerProtocol, path):
        """
            Abstract method to be overridden by subclasses to define the behaviour
            of the server's listener.
        """
        pass

    def __init__(self, hostname='', port='3012', ssl_dir=None, localhost_pem=None, localhost_key=None):
        """
            Parameters
            ----------
            hostname: str
                Hostname of the websocket server

            port: str
                port for the handler to listen on

            ssl_dir: Path
                path of directory for default SSL files, by default initialized to the ssl/ subdirectory in the parent
                directory of this file; not used if both localhost_pem and localhost_key are set

            localhost_pem: Path
                path to SSL certificate file, initialized by default to 'certificate.pem' in ssl_dir if not set

            localhost_key: Path
                path to SSL private key file, initialized by default to 'privkey.pem' in ssl_dir if not set
        """

        # Async event loop
        self.loop = asyncio.get_event_loop()
        # register signals for tasks to respond to
        self.signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in self.signals:
            # Create a set of shutdown tasks, one for each signal type
            self.loop.add_signal_handler(s, lambda s=s: self.loop.create_task(self.shutdown(signal=s)))

        # add a default excpetion handler to the event loop
        self.loop.set_exception_handler(self.handle_exception)

        # Set up server/listener ssl context
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Initialize SSL cert/key file paths as needed
        if ssl_dir is None and (localhost_pem is None or localhost_key is None):
            current_dir = Path(__file__).resolve().parent
            ssl_dir = current_dir.parent.joinpath('ssl')
        if localhost_pem is None:
            localhost_pem = ssl_dir.joinpath('certificate.pem')
        if localhost_key is None:
            localhost_key = ssl_dir.joinpath('privkey.pem')

        self.ssl_context.load_cert_chain(localhost_pem, keyfile=localhost_key)
        # print(hostname)
        # Setup websocket server
        self.server = websockets.serve(self.listener, hostname, int(port), ssl=self.ssl_context)


    def handle_exception(self, loop, context):
        message = context.get('exception', context['message'])
        logging.error(f"Caught exception: {message}")
        logging.info("Shutting down due to exception")
        asyncio.create_task(self.shutdown())

    async def shutdown(self, signal=None):
        """
            Wait for current task to finish, cancel all others
        """
        if signal:
            logging.info(f"Exiting on signal {signal.name}")

        #Let the current task finish gracefully
        #3.7 asyncio.all_tasks()
        tasks = [task for task in asyncio.Task.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            #Cancel pending tasks
            task.cancel()
        logging.info(f"Cancelling {len(tasks)} pending tasks")
        #wait for tasks to cancel
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()

    def run(self):
        """
            Run the handler indefinitely
        """
        try:
            #Establish the server funtion
            self.loop.run_until_complete(self.server)
            #Run server forever
            self.loop.run_forever()
        finally:
            self.loop.close()
            logging.info("Handler Finished")


class NoOpHandler(WebSocketInterface):
    """
        Example WebSocketInterface implementation with default server init.
        Custom server init can be done by calling super().__init__(...)
    """

    async def listener(self, websocket: WebSocketServerProtocol, path):
        print("NoOp Listener")
        await websocket.send("")

if __name__ == '__main__':
    #handler = CommHandler(print("NoOp Listener"), ssl_dir=Path("./ssl/"))
    handler = NoOpHandler(ssl_dir=Path("./ssl/"))
    handler.run()
