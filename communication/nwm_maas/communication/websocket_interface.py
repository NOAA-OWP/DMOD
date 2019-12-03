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

    def __del__(self):
        self.shutdown()

    def __init__(self, listen_host='', port=3012, ssl_dir=None, cert_pem=None, priv_key_pem=None):
        """
        Initialize this instance, starting its event loop and websocket server.

        Listen host for the websocket server will default to all interfaces if not set or set to None.

        Port for the websocket server will default to 3012.

        SSL certificate and private key files are required to initialize an SSL context for secure websocket
        communication. These can be set in two ways.  First, an SSL directory can be given, in which case the
        certificate and private key files will be inferred to be files within the SSL directory named 'certificate.pem'
        and 'privkey.pem' respectively.  Alternatively, a parameter can be set for either or both of these that
        references the appropriate path for a given file.

        By default, the parameter for SSL directory will be set to None.

        A value of None for SSL directory will be replaced with a path to a directory named 'ssl/' contained within the
        same directory as the instance's module file.  Since that does not even exist for the base
        :class:`WebSocketInterface`, it is generally recommended that the SSL directory be set explicitly to a non-None
        value unless specific paths for both of the files are set.

        Parameters
        ----------
        listen_host: Optional[str]
            Host on which the created :attr:`server` object binds and listens for websocket connections

        port: Union[str, int]
            Port on which the created websocket server attribute object binds and listens for websocket connections

        ssl_dir: Optional[Path]
            Value for parent directory for the SSL certificate and private key files, when using files with default
            names

        cert_pem: Optional[Path]
            Specific path to SSL certificate file, overriding using file with default name in SSL directory

        priv_key_pem: Optional[Path]
            Specific path to SSL private key file, overriding using file with default name in SSL directory
        """
        self._listen_host = listen_host.strip() if isinstance(listen_host, str) else None
        # TODO: consider printing/logging warning (or switching to error) in case of bad argument type
        self._port = int(port)
        # Async event loop
        self.loop = asyncio.get_event_loop()
        # register signals for tasks to respond to
        self.signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in self.signals:
            # Create a set of shutdown tasks, one for each signal type
            self.loop.add_signal_handler(s, lambda s=s: self.loop.create_task(self.shutdown(shutdown_signal=s)))

        # add a default excpetion handler to the event loop
        self.loop.set_exception_handler(self.handle_exception)

        # Set up server/listener ssl context
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Initialize SSL cert/privkey file paths as needed
        if ssl_dir is None and (cert_pem is None or priv_key_pem is None):
            current_dir = Path(__file__).resolve().parent
            ssl_dir = current_dir.parent.joinpath('ssl')
        if cert_pem is None:
            cert_pem = ssl_dir.joinpath('certificate.pem')
        if priv_key_pem is None:
            priv_key_pem = ssl_dir.joinpath('privkey.pem')

        self.ssl_context.load_cert_chain(cert_pem, keyfile=priv_key_pem)
        # print(hostname)
        # Setup websocket server
        self.server = websockets.serve(self.listener, self._listen_host, self._port, ssl=self.ssl_context)

    def handle_exception(self, loop, context):
        message = context.get('exception', context['message'])
        logging.error(f"Caught exception: {message}")
        logging.info("Shutting down due to exception")
        asyncio.create_task(self.shutdown())

    async def shutdown(self, shutdown_signal=None):
        """
            Wait for current task to finish, cancel all others
        """
        if shutdown_signal:
            logging.info(f"Exiting on signal {shutdown_signal.name}")

        #Let the current task finish gracefully
        #3.7 asyncio.all_tasks()
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
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


class EchoHandler(WebSocketInterface):
    """
    Example class, largely for testing purposes, which just echos out the same message received over a websocket as
    its reply, then shuts down the listener
    """
    async def listener(self, websocket: WebSocketServerProtocol, path):
        received_data = await websocket.recv()
        print("Echo Listener")
        await websocket.send(received_data)


if __name__ == '__main__':
    #handler = CommHandler(print("NoOp Listener"), ssl_dir=Path("./ssl/"))
    handler = NoOpHandler(ssl_dir=Path("./ssl/"))
    handler.run()
