#!/usr/bin/env python3

import asyncio
import json
import logging
from typing import Optional, Tuple, Type, Union

import websockets
from nwmaas.communication import Response, InvalidMessageResponse, FullAuthSession, SessionInitMessage, MaaSRequest, \
    SessionInitResponse, FailedSessionInitInfo, MessageEventType, WebSocketInterface, WebSocketSessionsInterface, \
    SessionInitFailureReason,  NWMRequestResponse, RedisBackendSessionManager, SchedulerClient, SchedulerRequestMessage
from websockets import WebSocketServerProtocol

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class UnsupportedMessageTypeResponse(Response):

    def __init__(self, actual_event_type: MessageEventType, listener_type: Type[WebSocketInterface],
                 message: str = None, data=None):
        if message is None:
            message = 'The {} event type is not supported by this {} listener'.format(
                actual_event_type, listener_type.__name__)
        super().__init__(success=False, reason='Message Event Type Unsupported', message=message, data=data)
        self.actual_event_type = actual_event_type
        self.listener_type = listener_type


class RequestHandler(WebSocketSessionsInterface):
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

    def __init__(self, listen_host='', port='3012', scheduler_host: str = 'localhost',
                 scheduler_port: Union[str, int] = 3013, ssl_dir=None, cert_pem=None, priv_key_pem=None,
                 scheduler_ssl_dir=None):
        super().__init__(listen_host=listen_host, port=port, ssl_dir=ssl_dir, cert_pem=cert_pem,
                         priv_key_pem=priv_key_pem)
        self._session_manager: RedisBackendSessionManager = RedisBackendSessionManager()
        self.scheduler_host = scheduler_host
        self.scheduler_port = int(scheduler_port)
        self.scheduler_client_ssl_dir = scheduler_ssl_dir if scheduler_ssl_dir is not None else self.ssl_dir

        scheduler_url = "wss://{}:{}".format(self.scheduler_host, self.scheduler_port)

        self._scheduler_client = SchedulerClient(scheduler_url, self.scheduler_client_ssl_dir)
        """SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

    @property
    def session_manager(self):
        return self._session_manager

    async def _authenticate_user_session(self, session_init_message: SessionInitMessage, session_ip_addr: str
                                         ) -> Tuple[Optional[FullAuthSession], bool, Optional[FailedSessionInitInfo]]:
        """
        Authenticate and return a user :obj:`FullAuthSession` from the given request message, creating and persisting a
        new instance and record if the user does not already have a session.

        Notes
        ----------
        The method returns a tuple, with both the session and an indication of whether a new session was created.  I.e.,
        in the future, it is possible existing sessions may be identified and re-used if appropriate.

        Parameters
        ----------
        session_init_message : SessionInitMessage
            The validate session init request message object
        session_ip_addr : str
            The IP address or host name of the client for the session

        Returns
        -------
        Tuple[Optional[Session], bool, Optional[FailedSessionInitInfo]
            The authenticated :obj:`Session` if an authenticate/authorized session was obtained (or None if not),
            whether a new session was created, and the failure info object if an authenticate/authorized session was not
            obtained (or else None)

        """
        session = None
        new_created = False
        init_failure_info: Optional[FailedSessionInitInfo] = None

        username = session_init_message.username
        # TODO: finish implementing the methods used below
        is_user_authenticated = await self._check_user_authenticated(username, session_init_message.user_secret)
        is_user_authorized = is_user_authenticated and await self._check_user_authorized(username)
        needs_new_session = is_user_authorized and not(await self._check_existing_session(username))

        if is_user_authenticated and is_user_authorized and needs_new_session:
            new_created = True
            try:
                session = self._session_manager.create_session(ip_address=session_ip_addr,
                                                               username=session_init_message.username)
            except Exception as e:
                details = 'The session manager encountered a {} when attempting to create a new session: {}'.format(
                    e.__class__.__name__, str(e))
                init_failure_info = FailedSessionInitInfo(user=session_init_message.username,
                                                          reason=SessionInitFailureReason.SESSION_MANAGER_FAIL,
                                                          details=details)
        elif is_user_authenticated and is_user_authorized:
            # TODO: when this is changed, make sure to properly create the init failure object as needed
            # session = TODO: lookup existing somehow
            pass
        elif is_user_authenticated:   # implies user was not authorized
            init_failure_info = FailedSessionInitInfo(user=session_init_message.username,
                                                      reason=SessionInitFailureReason.USER_NOT_AUTHORIZED,
                                                      details='Authenticated user is not authorized for session access')
        else:  # implies user was not authenticated
            init_failure_info = FailedSessionInitInfo(user=session_init_message.username,
                                                      reason=SessionInitFailureReason.AUTHENTICATION_DENIED,
                                                      details='User was not authenticated')
        return session, new_created, init_failure_info

    async def _check_user_authenticated(self, username: str, secret: str) -> bool:
        # TODO: implement authentication piece; for now, assume always authenticated successfully
        return True

    async def _check_user_authorized(self, username: str) -> bool:
        """
        Check that the user with the given username is authorized to make model requests.

        Parameters
        ----------
        username : str
            the username of the user for which authorization is being checked

        Returns
        -------
        ``True`` if the represented user is authorized to make model requests, or ``False`` otherwise
        """
        # TODO: implement authorization piece; for now, assume always authenticated user is always authorized
        return True

    async def _check_existing_session(self, username: str) -> bool:
        """
        Check whether a user with the given username already has an active session over which model requests can be
        made, implying (assuming appropriate auth) the user requires a new session.

        Note that this method does not take into account whether such a user is currently authenticated or whether such
        a user is authorized to be granted sessions.  Further, it does not retrieve any existing session.  It only tests
        whether there is an active session for the user.

        Parameters
        ----------
        username : str
            the username of the user for which an existing useable session is being checked

        Returns
        -------
        ``True`` if the represented user already has an existing, active session over which model requests can be made,
        or ``False`` otherwise
        """
        # TODO: implement check for existing useable session; for now, there never is one
        return False

    async def handle_auth_request(self, auth_message: SessionInitMessage, websocket: WebSocketServerProtocol,
                                  client_ip: str) -> Tuple[Optional[FullAuthSession], SessionInitResponse]:
        """
        Handle data from a request determined to be RequestType.AUTHENTICATION, including attempting to get an auth
        session, and prepare an appropriate response.
        Parameters
        ----------
        auth_message
            The session init request message object
        websocket
            The websocket over which the request came
        client_ip
            The client's IP address

        Returns
        -------
        A tuple with the found or created authenticated session for the request (or None authentication is unsuccessful)
        and an prepared SessionInitResponse with details on the authentication attempt (including session info for the
        client if successful)
        """
        session, is_new_session, fail_info = await self._authenticate_user_session(session_init_message=auth_message,
                                                                                   session_ip_addr=client_ip)
        if session is not None:
            session_txt = 'new session' if is_new_session else 'session'
            logging.debug('*************** Obtained {} for auth message: {}'.format(session_txt, str(session)))
            result = await self.register_websocket_session(websocket, session)
            logging.debug('************************* Attempt to register session-websocket result: {}'.format(str(result)))
            resp = SessionInitResponse(success=True, reason='Successful Auth', data=session)
        else:
            msg = 'Unable to create or find authenticated user session from request'
            resp = SessionInitResponse(success=False, reason='Failed Auth', message=msg, data=fail_info)

        return session, resp

    async def handle_job_request(self, model_request: MaaSRequest, session: FullAuthSession):
        if session is None:
            session = self._lookup_session_by_secret(secret=model_request.session_secret)

        if session is not None and model_request.session_secret == session.session_secret:
            # TODO: push to redis stream, associating with this session somehow, and getting some kind of id back
            job_id = 0
            mesg = 'Awaiting implementation of handler-to-scheduler communication' if job_id == 0 else ''
            #The context manager manages a SINGLE connection to the scheduler server
            #Adhoc calls to the scheduler can be made for this connection via the scheduler_client
            #These adhoc calls will use the SAME connection the context was initialized with
            scheduler_url = "wss://{}:{}".format(self.scheduler_host, self.scheduler_port)
            logging.debug("************* Preparing scheduler request message")
            scheduler_message = SchedulerRequestMessage(model_request=model_request, user_id=session.user)
            logging.debug("************* Scheduler request message ready:\n{}".format(str(scheduler_message)))
            #async with SchedulerClient(scheduler_url, self.scheduler_client_ssl_dir) as scheduler_client:
            # Should be able to do this to reuse same object/context/connection across tasks, even from other methods
            async with self._scheduler_client as scheduler_client:
                initial_response = await scheduler_client.send_to_scheduler(scheduler_message)
                logging.debug("************* Scheduler client received response:\n{}".format(str(initial_response)))
                if initial_response.success:
                    job_id = initial_response.job_id
                    # TODO: maybe here, formalize responses to a degree containing data
                    #async for response in scheduler_client.get_results():
                    #    logging.debug("************* Results:\n{}".format(str(response)))
                    #    print(response)
                #TODO loop here to receive multiple requests, try while execpt connectionClosed, let server tell us when to stop listening
            # TODO: consider registering the job and relationship with session, etc.
            success = initial_response.success
            logging.error("************* initial response: " + str(initial_response))
            reason = ('Success' if success else 'Failure') + ' starting job (returned id ' + str(job_id) + ')'
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            response = NWMRequestResponse(success=success, reason=reason, message=mesg,
                                          data={'job_id': job_id, 'scheduler_response': initial_response.to_dict()})
        else:
            if session is not None and model_request.session_secret != session.session_secret:
                logging.debug("************* Secrets do not agree: " + model_request.session_secret + ' | ' + session.session_secret)
            msg = 'Request does not correspond to an authenticated session'
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            response = NWMRequestResponse(success=False, reason='Unauthorized', message=msg)
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
                event_type, errors_map = await self.parse_request_type(data=data, check_for_auth=should_check_for_auth)
                req_message = await self.deserialized_message(message_data=data, event_type=event_type)

                if event_type == MessageEventType.INVALID:
                    response = InvalidMessageResponse(data=req_message)
                    await websocket.send(str(response))
                elif event_type == MessageEventType.SESSION_INIT:
                    session, response = await self.handle_auth_request(auth_message=req_message, websocket=websocket,
                                                                       client_ip=client_ip)
                    await websocket.send(str(response))
                elif event_type == MessageEventType.NWM_MAAS_REQUEST:
                    session, response = await self.handle_job_request(model_request=req_message, session=session)
                    await websocket.send(str(response))
                # TODO: add another message type (here and in client) for data transmission
                # TODO: add another message type for closing a session
                else:
                    msg = 'Received valid ' + event_type.name + ' request, but listener does not currently support'
                    response = UnsupportedMessageTypeResponse(actual_event_type=event_type,
                                                              listener_type=self.__class__,
                                                              data=data)
                    logging.error(msg)
                    logging.error(response.message)
                    await websocket.send(str(response))

        except websockets.exceptions.ConnectionClosed:
            logging.info("Connection Closed at Consumer")
        except asyncio.CancelledError:
            logging.info("Cancelling listerner task")
        finally:
            if session is not None:
                await self.unregister_websocket_session(session=session)


if __name__ == '__main__':
    raise RuntimeError('Module {} called directly; use main package entrypoint instead')
