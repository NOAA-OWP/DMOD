#!/usr/bin/env python3

"""
This script is the entry point for the request handler service
This script will:
    Parse and validate a user request
    Signal the scheduler to allocate and create the correct model service
        Signal via redis stream (publish): req_id -> req_meta
    Wait for responses to communicate back to user
    Should be threaded with async hanlders

"""
import asyncio
import websockets
import json
import logging
from nwmaas.communication import Response, InvalidMessageResponse, Session, SessionInitMessage, SessionInitResponse, \
    MessageEventType, WebSocketInterface, WebSocketSessionsInterface, MaaSRequest, NWMRequestResponse, \
    RedisBackendSessionManager
from typing import Dict, Optional, Tuple, Type
from websockets import WebSocketServerProtocol

logging.basicConfig(
    level=logging.ERROR,
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

    def __init__(self, listen_host='', port='3012', ssl_dir=None, cert_pem=None, priv_key_pem=None):
        super().__init__(listen_host=listen_host, port=port, ssl_dir=ssl_dir, cert_pem=cert_pem,
                         priv_key_pem=priv_key_pem)
        self._session_manager: RedisBackendSessionManager = RedisBackendSessionManager()

    @property
    def session_manager(self):
        return self._session_manager

    async def _authenticate_user_session(self, session_init_message: SessionInitMessage, session_ip_addr: str
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
        session_init_message : SessionInitMessage
            The validate session init request message object
        session_ip_addr : str
            The IP address or host name of the client for the session

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
                                                           username=session_init_message.username)
            new_created = True
        elif is_user_authorized:
            # session = TODO: lookup existing somehow
            pass

        return session, new_created

    async def handle_auth_request(self, auth_message: SessionInitMessage, websocket: WebSocketServerProtocol,
                                  client_ip: str) -> Tuple[Optional[Session], SessionInitResponse]:
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
        session, is_new_session = await self._authenticate_user_session(session_init_message=auth_message,
                                                                        session_ip_addr=client_ip)
        if session is not None:
            await self.register_websocket_session(websocket, session)
            resp = SessionInitResponse(success=True, reason='Successful Auth', data=json.loads(session.get_as_json()))
        else:
            msg = 'Unable to create or find authenticated user session from request'
            resp = SessionInitResponse(success=False, reason='Failed Auth', message=msg, data=auth_message.to_dict())

        return session, resp

    async def handle_job_request(self, model_request: MaaSRequest, session: Session):
        if session is None:
            session = self._lookup_session_by_secret(secret=model_request.session_secret)

        if session is not None and model_request.session_secret == session.session_secret:
            # TODO: push to redis stream, associating with this session somehow, and getting some kind of id back
            # job_id = # TODO
            job_id = 0
            mesg = 'Awaiting implementation of handler-to-scheduler communication' if job_id == 0 else ''

            # TODO: consider registering the job and relationship with session, etc.
            success = job_id > 0
            reason = ('Success' if success else 'Failure') + ' starting job (returned id ' + str(job_id) + ')'
            data = json.dumps({'job_id': job_id})
            # TODO: right now, the only supported MaaSRequest we will see is a NWMRequest, but account for other things
            response = NWMRequestResponse(success=success, reason=reason, message=mesg, data=data)
        else:
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
            await self.unregister_websocket_session(session=session)


if __name__ == '__main__':
    handler = RequestHandler(ssl_dir="../../communication/ssl")
    handler.run()
