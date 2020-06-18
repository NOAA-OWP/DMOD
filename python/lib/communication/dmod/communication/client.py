import asyncio
import datetime
import json
import ssl
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import websockets

from .maas_request import MaaSRequest, MaaSRequestResponse, NWMRequest, NWMRequestResponse
from .message import Message, Response, InitRequestResponseReason
from .scheduler_request import SchedulerRequestMessage, SchedulerRequestResponse
from .validator import NWMRequestJsonValidator
from .update_message import UpdateMessage, UpdateMessageResponse

import logging

# TODO: refactor this to allow for implementation-specific overriding more easily
logger = logging.getLogger("gui_log")


class WebSocketClient(ABC):
    """

    """

    @classmethod
    def build_endpoint_uri(cls, host: str, port: Union[int, str], path: Optional[str] = None, is_secure: bool = True):
        proto = 'wss' if is_secure else 'ws'
        if path is None:
            path = ''
        else:
            path = path.strip()
            if path[0] != '/':
                path = '/' + path
        return proto + '://' + host.strip() + ':' + str(port).strip() + path

    def __init__(self, endpoint_uri: str, ssl_directory: Path):
        super().__init__()

        self.endpoint_uri = endpoint_uri
        """str: The endpoint for the client to connect to to open new websocket connections."""

        self._ssl_directory = ssl_directory
        """Path: The parent directory of the cert PEM file used for the client SSL context."""

        # Setup this as a property to allow more private means to override the actual filename of the cert PEM file
        self._client_ssl_context = None
        """ssl.SSLContext: The private field for the client SSL context property."""

        self._cert_pem_file_basename: str = 'certificate.pem'
        """str: The basename of the certificate PEM file to use."""

        self.connection = None
        """Optional[websockets.client.Connect]: The open websocket connection, if set, for this client's context."""

        self._opening_connection = False
        """bool: Whether some task is in the process of opening a new connection in the context, but is awaiting."""

        self.active_connections = 0
        """int: The number of active utilizations of the open :attr:`connection`."""

    async def __aenter__(self):
        """
            When context is entered, use existing connection or create if none exists
        """
        # Basically, block here using await+sleep (with a timeout) if another task/event exec is opening a connection
        # Implicitly, this would mean said task is in an await, and execution went back to event loop (i.e., this call)
        # Also, for efficiency, delay datetime-related ops until first loop iteration, to avoid if the loop never runs
        timeout_limit = None
        while self._opening_connection and (timeout_limit is None or datetime.datetime.now() < timeout_limit):
            if timeout_limit is None:
                timeout_limit = datetime.datetime.now() + datetime.timedelta(seconds=15)
            await asyncio.sleep(0.25)

        # Safely conclude at this point that nothing else (worth paying attention to) is in the middle of opening a
        # connection, so check whether there already is one ...
        if self.connection is None:
            # If not, mark that this exec is opening a connection, before giving up control during the await
            self._opening_connection = True
            # Then asynchronously open the connection ...
            self.connection = await websockets.client.connect(self.endpoint_uri, ssl=self.client_ssl_context)
            # And now, note that we are no longer in the middle of an attempt to open a connection
            self._opening_connection = False

        self.active_connections += 1
        return self

    async def __aexit__(self, *exc_info):
        """
            When context exits, decrement the connection count, when no active connections, close
        """
        self.active_connections -= 1
        if self.active_connections < 1:
            await self.connection.close()
            self.connection = None
            self.active_connections = 0

    async def async_send(self, data: Union[str, bytearray], await_response: bool = False):
        """
            Send data to websocket, by default returning immediately after, but optionally waiting for and returning the
            response.

            Parameters
            ----------
            data
                string or byte array

            await_response
                whether the method should also await a response on the websocket connection and return it

            Returns
            -------
            response
                the request response if one should be awaited, or None
        """
        async with self as websocket:
            #TODO ensure correct type for data???
            await websocket.connection.send(data)
            return await websocket.connection.recv() if await_response else None

    @abstractmethod
    async def async_make_request(self, message: Message) -> Response:
        """
        Send (within Python's async functionality) the appropriate type of request :class:`Message` for this client
        implementation type and return the response as a corresponding, appropriate :class:`Response` instance.

        Parameters
        ----------
        message
            the request message object

        Returns
        -------
        response
            the request response object
        """
        pass

    @property
    def client_ssl_context(self) -> ssl.SSLContext:
        """
        Get the client SSL context property, lazily instantiating if necessary.

        Returns
        -------
        ssl.SSLContext
            the client SSL context for secure connections
        """
        if self._client_ssl_context is None:
            self._client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            endpoint_pem = self._ssl_directory.joinpath(self._cert_pem_file_basename)
            self.client_ssl_context.load_verify_locations(str(endpoint_pem))
        return self._client_ssl_context


class SchedulerClient(WebSocketClient):

    async def async_send_update(self, message: UpdateMessage) -> UpdateMessageResponse:
        """
        Send a serialized update message to the Scheduler service.

        Note that this function will return an ::class:`UpdateMessageResponse` in all situations, even if the response
        back from the scheduler service could not be deserialized back to an ::class:`UpdateMessageResponse` object.  In
        such cases, a response object is initialized with attributes set appropriately to indicated failure.  The raw
        response text is included if applicable, and the name of the exception raised is included in the ``reason``
        attribute.

        Parameters
        ----------
        message : UpdateMessage
            The update message to send.

        Returns
        -------
        UpdateMessageResponse
            A response message object in response to the update sent to the Scheduler service.
        """
        response_json = {}
        serialized_response = None
        try:
            serialized_response = await self.async_send(data=str(message), await_response=True)
            if serialized_response is None:
                raise ValueError('Response from {} async update message was `None`'.format(self.__class__.__name__))
            response_object = UpdateMessageResponse.factory_init_from_deserialized_json(json.loads(serialized_response))
            if response_object is None:
                raise ValueError('Could not deserialize update response to {}'.format(UpdateMessageResponse.__name__))
            else:
                return response_object
        except Exception as e:
            reason = 'Update Scheduler Failure: {} ({})'.format(str(e), e.__class__.__name__)
            logger.error('Encountered {} sending update to scheduler service: {}'.format(e.__class__.__name__, str(e)))
            return UpdateMessageResponse(digest=message.digest, object_found=False, success=False, reason=reason,
                                         response_text='None' if serialized_response is None else serialized_response)

    async def async_make_request(self, message: SchedulerRequestMessage) -> SchedulerRequestResponse:
        """
        Send (within Python's async functionality) the appropriate type of request :class:`Message` for this client
        implementation type and return the response as a corresponding, appropriate :class:`Response` instance.

        Parameters
        ----------
        message
            the request message object

        Returns
        -------
        response
            the request response object
        """
        response_json = {}
        try:
            # Send the request and get the scheduler confirmation of job submission
            serialized_response = await self.async_send(data=str(message), await_response=True)
            if serialized_response is None:
                raise ValueError('Serialized response from {} async message was `None`'.format(self.__class__.__name__))
        except Exception as e:
            logger.error('Encountered {} sending scheduler request: {}'.format(e.__class__.__name__, str(e)))
            reason = 'Request Send Failure ({})'.format(e.__class__.__name__)
            return SchedulerRequestResponse(success=False, reason=reason, message=str(e), data=response_json)
        try:
            # Consume the response confirmation by deserializing first to JSON, then from this to a response object
            response_json = json.loads(serialized_response)
            try:
                response_object = SchedulerRequestResponse.factory_init_from_deserialized_json(response_json)
                if response_object is None:
                    logging.error('********** Client did not deserialize response content to scheduler response object')
                    logging.error('********** Content was: ' + serialized_response)
                    reason = 'Could Not Deserialize Response Object'
                    response_object = SchedulerRequestResponse(success=False, reason=reason, data=response_json)
            except Exception as e2:
                logging.error('********** While deserialize response from scheduler, client encountered {}: {}'.format(
                    str(e2.__class__.__name__), str(e2)))
                reason = 'Deserializing scheduler request response failed due to {}'.format(e2.__class__.__name__)
                response_object = SchedulerRequestResponse(success=False, reason=reason, message=str(e2),
                                                           data=response_json)
        except Exception as e:
            reason = 'Invalid JSON Response'
            msg = 'Encountered ' + e.__class__.__name__ + ' loading response to JSON: ' + str(e)
            response_object = SchedulerRequestResponse(success=False, reason=reason, message=msg, data=response_json)

        logging.debug('************* Scheduler client returning response object {}'.format(response_object.to_json()))
        return response_object

    async def get_results(self):
        logging.debug('************* Scheduler client preparing to yield results')
        async for message in self.connection:
            logging.debug('************* Scheduler client yielding result: {}'.format(str(message)))
            yield message


class MaasRequestClient(WebSocketClient, ABC):

    @staticmethod
    def _job_request_failed_due_to_expired_session(response_obj: MaaSRequestResponse):
        """
        Test if the response to a websocket-sent request failed specifically because the utilized session is consider to
        be expired, either because the session is explicitly expired or there is no longer a record of the session with
        the session secret in the init request (i.e., it is implicitly expired).

        Parameters
        ----------
        response_obj

        Returns
        -------
        bool
            whether a failure occur and it specifically was due to a lack of authorization over the used session
        """
        is_expired = response_obj.reason_enum == InitRequestResponseReason.UNRECOGNIZED_SESSION_SECRET
        is_expired = is_expired or response_obj.reason_enum == InitRequestResponseReason.EXPIRED_SESSION
        return response_obj is not None and not response_obj.success and is_expired

    @staticmethod
    def _run_validation(message: Union[MaaSRequest, MaaSRequestResponse]):
        """
        Run validation for the given message object using the appropriate validator subtype.

        Parameters
        ----------
        message
            The message to validate, which will be either a ``MaaSRequest``  or a ``MaaSRequestResponse`` subtype.

        Returns
        -------
        tuple
            A tuple with the first item being whether or not the message was valid, and the second being either None or
            the particular error that caused the message to be identified as invalid

        Raises
        -------
        RuntimeError
            Raised if the message is of a particular type for which there is not a supported validator type configured.
        """
        if message is None:
            return False, None
        elif isinstance(message, NWMRequest):
            is_valid, error = NWMRequestJsonValidator().validate(message.to_dict())
            return is_valid, error
        elif isinstance(message, NWMRequestResponse):
            # TODO: implement (in particular, a suitable validator type)
            return True, None
        else:
            raise RuntimeError('Unsupported MaaSRequest subtype: ' + str(message.__class__))

    def __init__(self, endpoint_uri: str, ssl_directory: Path):
        super().__init__(endpoint_uri=endpoint_uri, ssl_directory=ssl_directory)

        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created, self._is_new_session = None, None, None, None

        self._errors = None
        self._warnings = None
        self._info = None

    async def async_make_request(self, maas_request: MaaSRequest) -> MaaSRequestResponse:
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            await websocket.send(maas_request.to_json())
            response = await websocket.recv()
            return maas_request.__class__.factory_init_correct_response_subtype(json_obj=json.loads(response))

    # TODO: ...
    async def authenticate_over_websocket(self):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            #async with websockets.connect(self.maas_endpoint_uri) as websocket:
            # return await EditView._authenticate_over_websocket(websocket)
            # Right now, it doesn't matter as long as it is valid
            # TODO: Fix this to not be ... fixed ...
            json_as_dict = {'username': 'someone', 'user_secret': 'something'}
            # TODO: validate before sending
            await websocket.send(json.dumps(json_as_dict))
            auth_response = json.loads(await websocket.recv())
            print('*************** Auth response: ' + json.dumps(auth_response))
            maas_session_id = auth_response['data']['session_id']
            maas_session_secret = auth_response['data']['session_secret']
            maas_session_created = auth_response['data']['created']
            return maas_session_id, maas_session_secret, maas_session_created

    def _acquire_new_session(self):
        try:
            logger.info("Connection to request handler web socket")
            auth_details = asyncio.get_event_loop().run_until_complete(self.authenticate_over_websocket())
            logger.info("auth_details returned")
            self._session_id, self._session_secret, self._session_created = auth_details
            self._is_new_session = True
            return True
        except:
            logger.info("Expecting exception to follow")
            logger.exception("Failed _acquire_session_info")
            return False

    @abstractmethod
    def _acquire_session_info(self, use_current_values: bool = True, force_new: bool = False):
        """
        Attempt to set the session information properties needed to submit a maas job request.

        Parameters
        ----------
        use_current_values
            Whether to use currently held attribute values for session details, if already not None (disregarded if
            ``force_new`` is ``True``).
        force_new
            Whether to force acquiring a new session, regardless of data available is available on an existing session.

        Returns
        -------
        bool
            whether session details were acquired and set successfully
        """
        pass

    @abstractmethod
    def _init_maas_job_request(self):
        pass

    @property
    @abstractmethod
    def errors(self):
        pass

    @property
    @abstractmethod
    def info(self):
        pass

    @property
    def is_new_session(self):
        return self._is_new_session

    def make_job_request(self, maas_job_request: MaaSRequest, force_new_session: bool = False):
        logger.debug("client Making Job Request")
        self._acquire_session_info(force_new=force_new_session)
        # Make sure to set if empty or reset if a new session was forced and just acquired
        if force_new_session or maas_job_request.session_secret is None:
            maas_job_request.session_secret = self._session_secret
        # If able to get session details, proceed with making a job request
        if self._session_secret is not None:
            print("******************* Request: " + maas_job_request.to_json())
            try:
                is_request_valid, request_validation_error = self._run_validation(message=maas_job_request)
                if is_request_valid:
                    try:
                        response_obj: MaaSRequestResponse = asyncio.get_event_loop().run_until_complete(
                            self.async_make_request(maas_job_request))
                        print('***************** Response: ' + str(response_obj))
                        # Try to get a new session if session is expired (and we hadn't already gotten a new session)
                        if self._job_request_failed_due_to_expired_session(response_obj) and not force_new_session:
                            return self.make_job_request(maas_job_request=maas_job_request, force_new_session=True)
                        elif not self.validate_job_request_response(response_obj):
                            raise RuntimeError('Invalid response received for requested job: ' + str(response_obj))
                        elif not response_obj.success:
                            template = 'Request failed (reason: {}): {}'
                            raise RuntimeError(template.format(response_obj.reason, response_obj.message))
                        else:
                            #self.job_id = self.resp_as_json['data']['job_id']
                            #results = self.resp_as_json['data']['results']
                            #jobs = self.resp_as_json['data']['all_jobs']
                            #self.info.append("Scheduler started job, id {}, results: {}".format(self.job_id, results))
                            #self.info.append("All user jobs: {}".format(jobs))
                            self.info.append("Scheduler started job, id {}".format(response_obj.data['job_id']))
                            return response_obj
                    except Exception as e:
                        # TODO: log error instead of print
                        msg = 'Encountered error submitting maas job request over session ' + str(self._session_id)
                        msg += " : \n" + str(type(e)) + ': ' + str(e)
                        print(msg)
                        traceback.print_exc()
                        self.errors.append(msg)
                else:
                    msg = 'Could not submit invalid maas job request over session ' + str(self._session_id)
                    msg += ' (' + str(request_validation_error) + ')'
                    print(msg)
                    self.errors.append(msg)
            except RuntimeError as e:
                print(str(e))
                self.errors.append(str(e))
        else:
            logger.info("client Unable to aquire session details")
            self.errors.append("Unable to acquire session details or authenticate new session for request")
        return None

    @property
    def session_created(self):
        return self._session_created

    @property
    def session_id(self):
        return self._session_id

    @property
    def session_secret(self):
        return self._session_secret

    def validate_job_request_response(self, maas_request_response: MaaSRequestResponse):
        return self._run_validation(message=maas_request_response)[0]

    @property
    @abstractmethod
    def warnings(self):
        pass
