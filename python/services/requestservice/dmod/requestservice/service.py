#!/usr/bin/env python3

import asyncio
import json
import logging
from typing import Union

import websockets
from websockets import WebSocketServerProtocol

from dmod.access import DummyAuthUtil, RedisBackendSessionManager
from dmod.communication import InvalidMessageResponse, MessageEventType, WebSocketSessionsInterface, \
    SchedulerClient, UnsupportedMessageTypeResponse
from dmod.externalrequests import AuthHandler, ModelExecRequestHandler, PartitionRequestHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class RequestService(WebSocketSessionsInterface):
    """
    Requests listener service class to receive and process async requests via websockets.

    Attributes
    ----------
    loop: asyncio event loop

    signals: list-like
        List of signals (from the signal package) this handler will use to shutdown

    ssl_context:
        ssl context for websocket

    server:
        websocket server
    """

    def __init__(self, listen_host='',
                 port='3012',
                 scheduler_host: str = 'localhost',
                 scheduler_port: Union[str, int] = 3013,
                 partitioner_host: str = 'localhost',
                 partitioner_port: Union[str, int] = 3014,
                 ssl_dir=None,
                 cert_pem=None,
                 priv_key_pem=None,
                 scheduler_ssl_dir=None,
                 partitioner_ssl_dir=None):
        super().__init__(listen_host=listen_host, port=port, ssl_dir=ssl_dir, cert_pem=cert_pem,
                         priv_key_pem=priv_key_pem)
        self._session_manager: RedisBackendSessionManager = RedisBackendSessionManager()
        self.scheduler_host = scheduler_host
        self.scheduler_port = int(scheduler_port)
        self.scheduler_client_ssl_dir = scheduler_ssl_dir if scheduler_ssl_dir is not None else self.ssl_dir

        self.partitioner_host = partitioner_host
        self.partitioner_port = int(partitioner_port)
        self.partitioner_ssl_dir = partitioner_ssl_dir if partitioner_ssl_dir is not None else self.ssl_dir

        # FIXME: implement real authenticator
        self.authenticator = DummyAuthUtil()
        # FIXME: implement real authorizer
        self.authorizer = self.authenticator

        scheduler_url = "wss://{}:{}".format(self.scheduler_host, self.scheduler_port)

        self._scheduler_client = SchedulerClient(scheduler_url, self.scheduler_client_ssl_dir)
        """SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

        self._auth_handler: AuthHandler = AuthHandler(session_manager=self._session_manager,
                                                      authenticator=self.authenticator,
                                                      authorizer=self.authorizer)
        # TODO: make sure this is still valid after finishing implementation

        self._model_exec_request_handler = ModelExecRequestHandler(session_manager=self._session_manager,
                                                                   authorizer=self.authorizer,
                                                                   scheduler_host=scheduler_host,
                                                                   scheduler_port=int(scheduler_port),
                                                                   scheduler_ssl_dir=self.scheduler_client_ssl_dir)

        self._partition_request_handler = PartitionRequestHandler(session_manager=self._session_manager,
                                                                  authorizer=self.authorizer,
                                                                  partition_service_host=partitioner_host,
                                                                  partition_service_port=int(partitioner_port),
                                                                  partition_service_ssl_dir=self.partitioner_ssl_dir)

    @property
    def session_manager(self):
        return self._session_manager

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
                    response = await self._auth_handler.handle_request(request=req_message, client_ip=client_ip)
                    #
                    if response is not None and response.success:
                        session = response.data
                        result = await self.register_websocket_session(websocket, session)
                        logging.debug('************************* Attempt to register session-websocket: {}'.format(
                            str(result)))
                    await websocket.send(str(response))
                elif event_type == MessageEventType.MODEL_EXEC_REQUEST:
                    response = self._model_exec_request_handler.handle_request(requests=req_message)
                    logging.debug('************************* Handled request response: {}'.format(str(response)))
                    await websocket.send(str(response))

                    # TODO loop here to handle a series of multiple requests, as job goes from requested to allocated to
                    #  scheduled to finished (and of course, the messages for output data)
                    #  try while except connectionClosed; let server tell us when to stop listening
                elif event_type == MessageEventType.PARTITION_REQUEST:
                    response = await self._partition_request_handler.handle_request(request=req_message)
                    logging.debug('************************* Handled request response: {}'.format(str(response)))
                    await websocket.send(str(response))
                # TODO: handle data management messages for creating datasets and adding data
                # FIXME: add another message type for closing a session
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
