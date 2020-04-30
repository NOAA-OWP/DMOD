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
from .maas_request import get_request, MaaSRequest
from .message import Message, MessageEventType, InvalidMessage
from .session import Session, SessionInitMessage
from .validator import NWMRequestJsonValidator, SessionInitMessageJsonValidator
from pathlib import Path
from typing import Dict, Optional, Tuple
from websockets import WebSocketServerProtocol

#logging.basicConfig(
#    level=logging.ERROR,
#    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
#    datefmt="%H:%M:%S"
#)


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

    @classmethod
    def _get_async_loop(cls):
        """
        Class method for getting the appropriate asyncio event loop, primarily to allow test-only implementations a way
        to override the value used during instantiation without directly providing a constructor param.

        The base implementation just returns the current event loop from :meth:`asyncio.get_event_loop`.

        Returns
        -------
        AbstractEventLoop
            the current event loop
        """
        return asyncio.get_event_loop()

    def __del__(self):
        try:
            asyncio.run(self.shutdown())
        except Exception as e:
            pass


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
        self.loop = self._get_async_loop()
        # register signals for tasks to respond to
        self.signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in self.signals:
            # Create a set of shutdown tasks, one for each signal type
            self.loop.add_signal_handler(s, lambda s=s: self.loop.create_task(self.shutdown(shutdown_signal=s)))

        # add a default excpetion handler to the event loop
        self.loop.set_exception_handler(self.handle_exception)

        self.ssl_dir = ssl_dir

        # Set up server/listener ssl context
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Initialize SSL cert/privkey file paths as needed
        if self.ssl_dir is None and (cert_pem is None or priv_key_pem is None):
            current_dir = Path(__file__).resolve().parent
            self.ssl_dir = current_dir.parent.joinpath('ssl')
        if cert_pem is None:
            cert_pem = ssl_dir.joinpath('certificate.pem')
        if priv_key_pem is None:
            priv_key_pem = ssl_dir.joinpath('privkey.pem')

        self.ssl_context.load_cert_chain(cert_pem, keyfile=priv_key_pem)
        # print(hostname)
        # Setup websocket server
        self.server = websockets.serve(self.listener, self._listen_host, self._port, ssl=self.ssl_context, loop=self.loop)

    async def deserialized_message(self, message_data: dict, event_type: MessageEventType = None, check_for_auth=False):
        """
        Deserialize

        Parameters
        ----------
        message_data
        event_type
        check_for_auth

        Returns
        -------

        """
        try:
            if event_type is None:
                event_type, errors = await self.parse_request_type(data=message_data, check_for_auth=check_for_auth)

            if event_type is None:
                raise RuntimeError('Cannot deserialize message: could not parse request to any enumerated event type')
            elif event_type == MessageEventType.NWM_MAAS_REQUEST:
                # By default, but don't stick with this ...
                model_name = MaaSRequest.model_name
                # ... get based on key in the message
                if isinstance(message_data['model'], dict):
                    for key in message_data['model']:
                        if key != 'session_secret':
                            model_name = key
                return get_request(model=model_name,
                                   session_secret=message_data['session-secret'],
                                   version=message_data['model'][model_name]['version'],
                                   output=message_data['model'][model_name]['output'],
                                   parameters=message_data['model'][model_name]['parameters'])
            elif event_type == MessageEventType.SESSION_INIT:
                return SessionInitMessage(username=message_data['username'], user_secret=message_data['user_secret'])
            elif event_type == MessageEventType.INVALID:
                return InvalidMessage(content=message_data)
            else:
                raise RuntimeError("Cannot deserialize message for unsupported event type {}".format(event_type))
        except RuntimeError as re:
            raise re

    def handle_exception(self, loop, context):
        message = context.get('exception', context['message'])
        logging.error(f"Caught exception: {message}")
        logging.info("Shutting down due to exception")
        asyncio.create_task(self.shutdown())

    async def parse_request_type(self, data: dict, check_for_auth=False) -> Tuple[MessageEventType, dict]:
        """
        Parse for request for validity, optionally for authentication type, determining which type of request this is.

        Parameters
        ----------
        data
            The data, expected to be a request, to be examined

        check_for_auth
            Whether the logic for should be run to see if the data is a valid session initialization request

        Returns
        -------
        A tuple of the determined :obj:`MessageEventType`, and a map of parsing errors encountered for attempted types
        """
        errors = {}
        for t in MessageEventType:
            if t != MessageEventType.INVALID:
                errors[t] = None

        if check_for_auth:
            is_auth_req, error = SessionInitMessageJsonValidator().validate(data)
            errors[MessageEventType.SESSION_INIT] = error
            if is_auth_req:
                return MessageEventType.SESSION_INIT, errors

        is_job_req, error = NWMRequestJsonValidator().validate(data)
        errors[MessageEventType.NWM_MAAS_REQUEST] = error
        if is_job_req:
            return MessageEventType.NWM_MAAS_REQUEST, errors

        return MessageEventType.INVALID, errors

    def run(self):
        """
            Run the handler indefinitely
        """
        try:
            # For each requested task, create a scheduled tasks
            for requested_coro in self._requested_tasks:
                self._scheduled_tasks.append(self.loop.create_task(requested_coro))

            # Then establish the main server function (and append to scheduled tasks list)
            # Make sure this gets put into the list of requested tasks
            self._requested_tasks.append(self.server)
            self._scheduled_tasks.append(self.loop.run_until_complete(self.server))

            # Run server forever
            self.loop.run_forever()
        finally:
            self.loop.close()
            logging.info("Handler Finished")

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


class WebSocketSessionsInterface(WebSocketInterface, ABC):
    """
    Extension of :class:`WebSocketInterface` for authenticated communication via sessions.

    Note that implementations of this type are not necessarily required to handle the logic for session init and/or
    authentication.  They merely must recognize within their :meth:`listener` method whether applicable messages
    properly demonstrate they are "within" a known session.
    """
    def __init__(self, listen_host='', port='3012', ssl_dir=None, cert_pem=None, priv_key_pem=None):
        super().__init__(listen_host=listen_host, port=port, ssl_dir=ssl_dir, cert_pem=cert_pem,
                         priv_key_pem=priv_key_pem)
        self._sessions_to_websockets: Dict[Session, WebSocketServerProtocol] = {}

    @property
    @abstractmethod
    def session_manager(self):
        pass

    def _lookup_session_by_secret(self, secret: str) -> Optional[Session]:
        """
        Search for the :obj:`Session` instance with the given session secret value.

        Parameters
        ----------
        secret

        Returns
        -------
        Optional[Session]
            The session from the sessions-to-websockets mapping having the given secret, or None
        """
        return self.session_manager.lookup_session_by_secret(session_secret=secret)

    async def register_websocket_session(self, websocket: WebSocketServerProtocol, session: Session):
        """
        Register the known relationship of a session keyed to a specific websocket.

        Parameters
        ----------
        websocket
        session
        """
        self._sessions_to_websockets[session] = websocket

    async def unregister_websocket_session(self, session: Session):
        """
        Unregister the known relationship of a session keyed to a specific websocket.

        Parameters
        ----------
        websocket
        session
        """
        if session is None or session.session_id is None:
            return
        else:
            logging.debug('************* Session Arg: ({}) {}'.format(session.__class__.__name__, str(session)))
            for session_key in self._sessions_to_websockets:
                logging.debug('************* Knowns Session: ({}) {}'.format(session.__class__.__name__, str(session_key)))
            if session in self._sessions_to_websockets:
                logging.debug('************* Popping websocket for session {}'.format(str(session)))
                self._sessions_to_websockets.pop(session)


class NoOpHandler(WebSocketInterface):
    """
        Example WebSocketInterface implementation with default server init.
        Custom server init can be done by calling super().__init__(...)
    """

    @classmethod
    def _get_async_loop(cls):
        """
        Override of default, to provide a new, non-primary loop for testing purposes.

        Returns
        -------
        AbstractEventLoop
            a new asyncio event loop
        """
        return asyncio.new_event_loop()

    async def listener(self, websocket: WebSocketServerProtocol, path):
        print("NoOp Listener")
        await websocket.send("")


class EchoHandler(WebSocketInterface):
    """
    Example class, largely for testing purposes, which just echos out the same message received over a websocket as
    its reply, then shuts down the listener
    """

    @classmethod
    def _get_async_loop(cls):
        """
        Override of default, to provide a new, non-primary loop for testing purposes.

        Returns
        -------
        AbstractEventLoop
            a new asyncio event loop
        """
        return asyncio.new_event_loop()

    async def listener(self, websocket: WebSocketServerProtocol, path):
        received_data = await websocket.recv()
        print("Echo Listener")
        await websocket.send(received_data)


if __name__ == '__main__':
    #handler = CommHandler(print("NoOp Listener"), ssl_dir=Path("./ssl/"))
    handler = NoOpHandler(ssl_dir=Path("./ssl/"))
    handler.run()
