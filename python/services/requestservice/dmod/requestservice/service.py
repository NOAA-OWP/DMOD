#!/usr/bin/env python3

import asyncio
import json
import logging
from typing import List
from typing import Type
from typing import Union

import websockets
from websockets import WebSocketServerProtocol

from dmod.access import DummyAuthUtil, RedisBackendSessionManager
from dmod.communication import AbstractInitRequest, InvalidMessageResponse, MessageEventType, NGENRequest, NWMRequest, \
    NgenCalibrationRequest, PartitionRequest, WebSocketSessionsInterface, SessionInitMessage, \
    UnsupportedMessageTypeResponse
from dmod.communication.dataset_management_message import MaaSDatasetManagementMessage
from dmod.communication.maas_request.job_message import JobControlRequest, JobInfoRequest, JobListRequest
from dmod.externalrequests import AuthHandler, DatasetRequestHandler, ModelExecRequestHandler, \
    NgenCalibrationRequestHandler, PartitionRequestHandler, EvaluationRequestHandler, ExistingJobRequestHandler

from .alternate_service import LaunchEvaluationMessage, OpenEvaluationMessage

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
    _PARSEABLE_REQUEST_TYPES = [
        SessionInitMessage,
        NgenCalibrationRequest,
        NWMRequest,
        NGENRequest,
        MaaSDatasetManagementMessage,
        PartitionRequest,
        LaunchEvaluationMessage,
        OpenEvaluationMessage,
        JobControlRequest,
        JobInfoRequest,
        JobListRequest
    ]
    """ Parseable request types, which are all authenticated ::class:`ExternalRequest` subtypes for this implementation. """

    @classmethod
    def get_parseable_request_types(cls) -> List[Type[AbstractInitRequest]]:
        """
        Get the ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.

        Returns
        -------
        List[Type[AbstractInitRequest]]
            The ::class:`AbstractInitRequest` subtypes this type supports parsing when handling incoming messages.
        """
        return cls._PARSEABLE_REQUEST_TYPES

    def __init__(self, listen_host='',
                 port='3012',
                 scheduler_host: str = 'localhost',
                 scheduler_port: Union[str, int] = 3013,
                 partitioner_host: str = 'partitioner-service',
                 data_service_host: str = 'data-service',
                 evaluation_service_host: str = 'evaluation-service',
                 partitioner_port: Union[str, int] = 3014,
                 data_service_port: Union[str, int] = 3015,
                 evaluation_service_port: Union[str, int] = 3016,
                 ssl_dir=None,
                 cert_pem=None,
                 priv_key_pem=None,
                 scheduler_ssl_dir=None,
                 partitioner_ssl_dir=None,
                 data_service_ssl_dir=None,
                 evaluation_service_ssl_dir=None,
                 **kwargs
                 ):
        super().__init__(listen_host=listen_host, port=port, ssl_dir=ssl_dir, cert_pem=cert_pem,
                         priv_key_pem=priv_key_pem)
        self._session_manager: RedisBackendSessionManager = RedisBackendSessionManager()
        self.scheduler_host = scheduler_host
        self.scheduler_port = int(scheduler_port)
        self.scheduler_client_ssl_dir = scheduler_ssl_dir if scheduler_ssl_dir is not None else self.ssl_dir

        self.partitioner_host = partitioner_host
        self.partitioner_port = int(partitioner_port)
        self.partitioner_ssl_dir = partitioner_ssl_dir if partitioner_ssl_dir is not None else self.ssl_dir

        self.data_service_host = data_service_host
        self.data_service_port = int(data_service_port)
        self.data_service_ssl_dir = data_service_ssl_dir if data_service_ssl_dir is not None else self.ssl_dir

        self.evaluation_service_host = evaluation_service_host
        self.evaluation_service_port = int(evaluation_service_port)
        self.evaluation_service_ssl_dir = evaluation_service_ssl_dir or self.ssl_dir

        # FIXME: implement real authenticator
        self.authenticator = DummyAuthUtil()
        # FIXME: implement real authorizer
        self.authorizer = self.authenticator

        # TODO: make sure this isn't still needed (or shouldn't be re-added)
        #self._scheduler_client = SchedulerClient(transport_client=WebSocketClient(endpoint_host=self.scheduler_host,
        #                                                                          endpoint_port=self.scheduler_port,
        #                                                                          capath=self.scheduler_client_ssl_dir))
        #"""SchedulerClient: Client for interacting with scheduler, which also is a context manager for connections."""

        self._auth_handler: AuthHandler = AuthHandler(session_manager=self._session_manager,
                                                      authenticator=self.authenticator,
                                                      authorizer=self.authorizer)
        # TODO: make sure this is still valid after finishing implementation

        self._model_exec_request_handler = ModelExecRequestHandler(session_manager=self._session_manager,
                                                                   authorizer=self.authorizer,
                                                                   service_host=scheduler_host,
                                                                   service_port=int(scheduler_port),
                                                                   service_ssl_dir=self.scheduler_client_ssl_dir)

        self._calibration_request_handler = NgenCalibrationRequestHandler(session_manager=self._session_manager,
                                                                          authorizer=self.authorizer,
                                                                          service_host=scheduler_host,
                                                                          service_port=int(scheduler_port),
                                                                          service_ssl_dir=self.scheduler_client_ssl_dir)

        self._partition_request_handler = PartitionRequestHandler(session_manager=self._session_manager,
                                                                  authorizer=self.authorizer,
                                                                  service_host=partitioner_host,
                                                                  service_port=int(partitioner_port),
                                                                  service_ssl_dir=self.partitioner_ssl_dir)

        self._data_service_handler = DatasetRequestHandler(session_manager=self._session_manager,
                                                           authorizer=self.authorizer,
                                                           service_host=data_service_host,
                                                           service_port=int(data_service_port),
                                                           service_ssl_dir=self.data_service_ssl_dir)

        self._existing_job_request_handler = ExistingJobRequestHandler(session_manager=self._session_manager,
                                                                       authorizer=self.authorizer,
                                                                       service_host=scheduler_host,
                                                                       service_port=int(scheduler_port),
                                                                       service_ssl_dir=self.scheduler_client_ssl_dir)
        # This probably won't work until evaluation service is properly added in Docker stack, so wrap in try for now
        try:
            self._evaluation_service_handler = EvaluationRequestHandler(
                target_service='evaluation-service',
                service_host=evaluation_service_host,
                service_port=evaluation_service_port,
                ssl_directory=evaluation_service_ssl_dir
            )
            self._eval_handler_exception = None
        except Exception as e:
            self._evaluation_service_handler = None
            self._eval_handler_exception = e

    @property
    def session_manager(self):
        return self._session_manager

    async def listener(self, websocket: WebSocketServerProtocol):
        """
        Async function listening for incoming information on websocket.
        """
        session = None
        client_ip = websocket.remote_address[0]
        try:
            async for message in websocket:
                data = json.loads(message)
                logging.info(f"Got payload: {data}")
                req_message = await self.deserialized_message(message_data=data)
                event_type = MessageEventType.INVALID if req_message is None else req_message.get_message_event_type()

                if isinstance(req_message, LaunchEvaluationMessage) or isinstance(req_message, OpenEvaluationMessage):
                    if self._evaluation_service_handler is None:
                        msg = (f"{self.__class__.__name__} could not initialize evaluation handler due to "
                               f"{self._eval_handler_exception.__class__.__name__}: {self._eval_handler_exception!s}")
                        raise RuntimeError(msg)
                    response = await self._evaluation_service_handler.handle_request(
                        request=req_message,
                        socket=websocket,
                        path=websocket.path
                    )
                    logging.debug('************************* Handled request response: {}'.format(str(response)))
                    await websocket.send(str(response))
                elif event_type == MessageEventType.INVALID:
                    response = InvalidMessageResponse(data=req_message)
                    await websocket.send(str(response))
                elif event_type == MessageEventType.SESSION_INIT:
                    response = await self._auth_handler.handle_request(request=req_message, client_ip=client_ip)
                    if response is not None and response.success:
                        session = response.data
                        result = await self.register_websocket_session(websocket, session)
                        logging.debug('************************* Attempt to register session-websocket: {}'.format(
                            str(result)))
                    await websocket.send(str(response))
                # Handle data management messages for creating datasets and adding data
                elif event_type == MessageEventType.DATASET_MANAGEMENT:
                    response = await self._data_service_handler.handle_request(request=req_message,
                                                                               upstream_websocket=websocket)
                    await websocket.send(str(response))
                elif event_type == MessageEventType.MODEL_EXEC_REQUEST:
                    response = await self._model_exec_request_handler.handle_request(request=req_message)
                    logging.debug('************************* Handled request response: {}'.format(str(response)))
                    await websocket.send(str(response))

                    # TODO loop here to handle a series of multiple requests, as job goes from requested to allocated to
                    #  scheduled to finished (and of course, the messages for output data)
                    #  try while except connectionClosed; let server tell us when to stop listening
                elif event_type == MessageEventType.PARTITION_REQUEST:
                    response = await self._partition_request_handler.handle_request(request=req_message)
                    logging.debug('************************* Handled request response: {}'.format(str(response)))
                    await websocket.send(str(response))
                elif event_type == MessageEventType.CALIBRATION_REQUEST:
                    logging.debug('Handled calibration request')
                    response = await self._calibration_request_handler.handle_request(request=req_message)
                    logging.debug('Processed calibration request; response was: {}'.format(str(response)))
                    await websocket.send(str(response))
                elif event_type == MessageEventType.SCHEDULER_REQUEST:
                    response = await self._existing_job_request_handler.handle_request(request=req_message)
                    logging.debug('Handled existing jobs request')
                    await websocket.send(str(response))
                # FIXME: add another message type for closing a session
                else:
                    msg = 'Received valid ' + event_type.name + ' request, but listener does not currently support'
                    response = UnsupportedMessageTypeResponse(actual_event_type=event_type,
                                                              listener_type=self.__class__,
                                                              data=data)
                    logging.error(msg)
                    logging.error(response.message)
                    await websocket.send(str(response))

        except websockets.exceptions.ConnectionClosed as e:
            logging.info("Connection Closed at Consumer ({})".format(str(e)))
        except asyncio.CancelledError as e:
            logging.info("Cancelling listerner task - {}".format(str(e)))
        except Exception as e:
            logging.info('Unexpected exception - {}'.format(str(e)))
        finally:
            if session is not None:
                await self.unregister_websocket_session(session=session)


if __name__ == '__main__':
    raise RuntimeError('Module {} called directly; use main package entrypoint instead')
