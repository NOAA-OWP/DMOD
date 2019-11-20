#!/usr/bin/env python3

"""
This script is the entry point for the request hanlder service
This script will:
    Parse and validate a user request
    Signal the scheduler to allocate and create the correct model service
        Signal via redis stream (publish): req_id -> req_meta
    Wait for responses to communicate back to user
    Should be threaded with async hanlders

"""
import asyncio
import websockets
import ssl
import json
import signal
import logging

from .RequestType import RequestType
from .session import Session, SessionManager
from .validator import JsonRequestValidator, JsonJobRequestValidator, JsonAuthRequestValidator
from jsonschema.exceptions import ValidationError
from pathlib import Path
from typing import Dict, Optional, Tuple
from websockets import WebSocketServerProtocol

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class RequestResponse:

    def __init__(self, success: bool, reason: str, message: str = '', data=None):
        self.success = success
        self.reason = reason
        self.message = message
        self.data = data

    def __str__(self):
        return str(self.as_json())

    def as_json(self):
        return json.dumps({'success': self.success, 'reason': self.reason, 'message': self.message, 'data': self.data})


class RequestHandler(object):
    """
    Request Handling class to manage async requests

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

    def __init__(self, hostname='', port='3012', schema_dir=None, ssl_dir=None, localhost_pem=None, localhost_key=None):
        """
            Parameters
            ----------
            hostname: str
                Hostname of the websocket server

            port: str
                port for the handler to listen on

            schema_dir: Path
                JSON schemas directory

            ssl_dir: Path
                path of directory for default SSL files, by default initialized to the ssl/ subdirectory in the parent
                directory of this file; not used if both localhost_pem and localhost_key are set

            localhost_pem: Path
                path to SSL certificate file, initialized by default to 'certificate.pem' in ssl_dir if not set

            localhost_key: Path
                path to SSL private key file, initialized by default to 'privkey.pem' in ssl_dir if not set
        """
        self._schema_dir = schema_dir
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

        self._session_manager: SessionManager = SessionManager()
        self._sessions_to_websockets: Dict[Session, WebSocketServerProtocol] = {}
        self._websockets_to_sessions: Dict[WebSocketServerProtocol, Session] = {}

        self.ssl_context.load_cert_chain(localhost_pem, keyfile=localhost_key)
        # print(hostname)
        # Setup websocket server
        self.server = websockets.serve(self.listener, hostname, int(port), ssl=self.ssl_context)

    def _lookup_session_by_secret(self, secret: str) -> Optional[Session]:
        """
        Search for the :obj:`Session` instance with the given session secret value within the instance's
        :attr:`_sessions_to_websockets` mapping.

        Parameters
        ----------
        secret

        Returns
        -------
        Optional[Session]
            The session from the sessions-to-websockets mapping having the given secret, or None
        """
        for s in self._sessions_to_websockets.keys():
            if secret == s.session_secret:
                return s
        return None

    def handle_exception(self, loop, context):
        message = context.get('exception', context['message'])
        logging.error(f"Caught exception: {message}")
        logging.info("Shutting down due to exception")
        asyncio.create_task(self.shutdown())

    async def _authenticate_user_session(self, valid_auth_req_data: dict, session_ip_addr: str
                                         ) -> Tuple[Optional[Session], bool]:
        """
        Authenticate and return a user :obj:`Session` from the given request message, creating and persisting a new
        instance and record if the user does not already have a session.

        Notes
        ----------
        The method returns a tuple, with both the session and an indication of whether a new session was created.  I.e.,
        in the future, it is possible existing sessions may be identified and re-used if appropriate.

        Parameters
        ----------
        valid_auth_req_data : dict
            A valid authentication request message as JSON data.
        session_ip_addr : str
            The IP address or host name of the client for the session.

        Returns
        -------
        Tuple[Optional[Session], bool]
            The authenticated :obj:`Session` if the user was authenticated (or None if not), and whether a new session
            was created

        """
        session = None
        new_created = False

        # TODO: For now, every valid auth request is considered authorized and has a new session created; change later
        is_user_authorized = True
        needs_new_session = True

        if is_user_authorized and needs_new_session:
            session = self._session_manager.create_session(ip_address=session_ip_addr,
                                                           username=valid_auth_req_data['username'])
            new_created = True
        elif is_user_authorized:
            # session = TODO: lookup existing somehow
            pass

        return session, new_created

    async def parse_request_type(self, data, check_for_auth=False) -> Tuple[RequestType, dict]:
        """
        Parse for request for validity, optionally for authentication type, determining which type of request this is.

        Parameters
        ----------
        data
        check_for_auth

        Returns
        -------
        A tuple of the determined :obj:`RequestType`, and a map of parsing errors encountered for attempted types
        """
        errors = {}
        for t in RequestType:
            if t != RequestType.INVALID:
                errors[t] = None

        if check_for_auth:
            is_auth_req, error = JsonAuthRequestValidator(schemas_dir=self._schema_dir).validate_request(data)
            errors[RequestType.AUTHENTICATION] = error
            if is_auth_req:
                return RequestType.AUTHENTICATION, errors

        is_job_req, error = JsonJobRequestValidator(schemas_dir=self._schema_dir).validate_request(data)
        errors[RequestType.JOB] = error
        if is_job_req:
            return RequestType.JOB, errors

        return RequestType.INVALID, errors

    async def handle_auth_request(self, data, websocket, client_ip: str) -> Tuple[Optional[Session], RequestResponse]:
        """
        Handle data from a request determined to be RequestType.AUTHENTICATION, including attempting to get an auth
        session, and prepare an appropriate response.
        Parameters
        ----------
        data
            The JSON data for the received message
        websocket
            The websocket over which the request came
        client_ip
            The client's IP address

        Returns
        -------
        A tuple with the found or created authenticated session for the request (or None authentication is unsuccessful)
        and an prepared response with details on the authentication attempt (including session info for the client if
        successful)
        """
        session, is_new_session = await self._authenticate_user_session(valid_auth_req_data=data,
                                                                        session_ip_addr=client_ip)
        if session is not None:
            await self.register_websocket_session(websocket, session)
            response = RequestResponse(success=True, reason='Successful Auth',
                                       data=(None if session is None else session.get_as_json()))
        else:
            msg = 'Unable to create or find authenticated user session from request'
            response = RequestResponse(success=False, reason='Failed Auth', message=msg, data=data)

        return session, response

    async def handle_job_request(self, data, session):
        if session is None:
            session = self._lookup_session_by_secret(secret=data['session-secret'])
        if session is not None and data['session-secret'] == session.session_secret:
            # TODO: push to redis stream, associating with this session somehow, and getting some kind of id back
            # job_id = # TODO
            job_id = -1
            success = job_id > 0
            # TODO: consider registering the job and relationship with session, etc.
            reason = ('Success' if success else 'Failure') + ' starting job (returned id ' + str(job_id) + ')'
            response = RequestResponse(success=job_id > 0, reason=reason, data=json.dumps({'job_id': job_id}))
        else:
            msg = 'Request does not correspond to an authenticated session'
            response = RequestResponse(success=False, reason='Unauthorized', message=msg)
        return session, response

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Async function listening for incoming information on websocket.
        """
        session = None
        client_ip = websocket.remote_address[0]
        try:
            async for message in websocket:
                data = json.loads(message)
                logging.info(f"Got payload: {data}")
                should_check_for_auth = session is None
                request_type, errors_map = await self.parse_request_type(data=data, check_for_auth=should_check_for_auth)

                if request_type == RequestType.INVALID:
                    r = RequestResponse(success=False, reason="Invalid request", message="Request not in valid format")
                    await websocket.send(str(r))
                elif should_check_for_auth and request_type == RequestType.AUTHENTICATION:
                    session, response = await self.handle_auth_request(data=data, websocket=websocket, client_ip=client_ip)
                    await websocket.send(str(response))
                elif request_type == RequestType.JOB:
                    session, response = await self.handle_job_request(data=data, session=session)
                    await websocket.send(str(response))
                else:
                    msg = 'Received valid ' + request_type.name + ' request, but listener does not currently support'
                    resp = RequestResponse(success=False, reason="Unsupported request type", message=msg)
                    logging.error(message)
                    await websocket.send(str(resp))
        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listerner task")
        finally:
            await self.unregister_websocket_session(websocket=websocket, session=session)

    async def register_websocket_session(self, websocket: WebSocketServerProtocol, session: Session):
        self._sessions_to_websockets[session] = websocket
        self._websockets_to_sessions[websocket] = session

    async def unregister_websocket_session(self, websocket: WebSocketServerProtocol = None, session: Session = None):
        if websocket is None and session is None:
            return
        elif websocket is None:
            websocket = self._sessions_to_websockets.pop(session)
            self._websockets_to_sessions.pop(websocket)
        elif session is None:
            session = self._websockets_to_sessions.pop(websocket)
            self._sessions_to_websockets.pop(session)
        else:
            self._sessions_to_websockets.pop(session)
            self._websockets_to_sessions.pop(websocket)

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
            Run the request handler indefinitely
        """
        try:
            #Establish the websocket
            self.loop.run_until_complete(self.server)
            #Run server forever
            self.loop.run_forever()
        finally:
            self.loop.close()
            logging.info("Request Handler Finished")


if __name__ == '__main__':
    handler = RequestHandler()
    handler.run()
