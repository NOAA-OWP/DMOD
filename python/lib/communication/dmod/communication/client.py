import asyncio
import datetime
import json
import ssl
import traceback
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import Generic, Optional, Type, TypeVar, Union
from dmod.core.serializable import Serializable

import websockets

from .maas_request import ExternalRequest, ExternalRequestResponse, ModelExecRequest, ModelExecRequestResponse, NWMRequest, \
    NGENRequest
from .message import AbstractInitRequest, Message, Response, InitRequestResponseReason
from .partition_request import PartitionRequest, PartitionResponse
from .dataset_management_message import DatasetManagementMessage, DatasetManagementResponse
from .scheduler_request import SchedulerRequestMessage, SchedulerRequestResponse
from .validator import NWMRequestJsonValidator
from .update_message import UpdateMessage, UpdateMessageResponse

import logging

# TODO: refactor this to allow for implementation-specific overriding more easily
logger = logging.getLogger("gui_log")

M = TypeVar("M", bound=AbstractInitRequest)
R = TypeVar("R", bound=Response)

EXTERN_REQ_M = TypeVar("EXTERN_REQ_M", bound=ExternalRequest)
EXTERN_REQ_R = TypeVar("EXTERN_REQ_R", bound=ExternalRequestResponse)

MOD_EX_M = TypeVar("MOD_EX_M", bound=ModelExecRequest)
MOD_EX_R = TypeVar("MOD_EX_R", bound=ModelExecRequestResponse)


def get_or_create_eventloop() -> AbstractEventLoop:
    """
    Retrieves an async event loop

    An event loop is created and assigned if it is not present

    Returns:
    An async event loop
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        # If the error was due to a non-existent loop, create, assign, and return a new one
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()
        raise


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
        return '{}://{}:{}{}'.format(proto, host.strip(), str(port).strip(), path)

    def __init__(self, endpoint_uri: str, ssl_directory: Path, *args, **kwargs):
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
            try:
                self.connection = await websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context)
            except Exception as e:
                raise e
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
            self.client_ssl_context.load_verify_locations(endpoint_pem)
        return self._client_ssl_context


class InternalServiceClient(WebSocketClient, Generic[M, R], ABC):
    """
    Abstraction for a client that interacts with some internal, non-public-facing DMOD service.
    """

    @classmethod
    @abstractmethod
    def get_response_subtype(cls) -> Type[R]:
        """
        Return the response subtype class appropriate for this client implementation.

        Returns
        -------
        Type[R]
            The response subtype class appropriate for this client implementation.
        """
        pass

    def build_response(self, success: bool, reason: str, message: str = '', data: Optional[dict] = None,
                       **kwargs) -> R:
        """
        Build a response of the appropriate subtype from the given response details.

        Build a response of the appropriate subtype for this particular implementation, using the given parameters for
        this function as the initialization params for the response.  Per the design of ::class:`Response`, the primary
        attributes are ::attribute:`Response.success`, ::attribute:`Response.reason`, ::attribute:`Response.message`,
        and ::attribute:`Response.data`.  However, implementations may permit or require additional param values, which
        can be supplied via keyword args.

        As with the init of ::class:`Request`, defaults of ``''`` (empty string) and  ``None`` are in place for for
        ``message`` and ``data`` respectively.

        A default implementation is provided that initializes an instance of the type return by
        ::method:`get_response_subtype`.  Keyword args are not used in this default implementation.

        Parameters
        ----------
        success : bool
            The value for ::attribute:`Response.success` to use when initializing the response object.
        reason : str
            The value for ::attribute:`Response.reason` to use when initializing the response object.
        message : str
            The value for ::attribute:`Response.message` to use when initializing the response object (default: ``''``).
        data : dict
            The value for ::attribute:`Response.data` to use when initializing the response object (default: ``None``).
        kwargs : dict
            A dict for any additional implementation specific init params for the response object.

        Returns
        -------
        R
            A response object of the appropriate subtype.
        """
        return self.get_response_subtype()(success=success, reason=reason, message=message, data=data)

    def _process_request_response(self, response_str: str):
        response_type = self.get_response_subtype()
        my_class_name = self.__class__.__name__
        response_json = {}
        try:
            # Consume the response confirmation by deserializing first to JSON, then from this to a response object
            response_json = json.loads(response_str)
            try:
                response_object = response_type.factory_init_from_deserialized_json(response_json)
                if response_object is None:
                    msg = '********** {} could not deserialize {} from raw websocket response: `{}`'.format(
                        my_class_name, response_type.__name__, str(response_str))
                    reason = '{} Could Not Deserialize To {}'.format(my_class_name, response_type.__name__)
                    response_object = self.build_response(success=False, reason=reason, message=msg, data=response_json)
            except Exception as e2:
                msg = '********** While deserializing {}, {} encountered {}: {}'.format(
                    response_type.__name__, my_class_name, e2.__class__.__name__, str(e2))
                reason = '{} {} Deserializing {}'.format(my_class_name, e2.__class__.__name__, response_type.__name__)
                response_object = self.build_response(success=False, reason=reason, message=msg, data=response_json)
        except Exception as e:
            reason = 'Invalid JSON Response'
            msg = 'Encountered {} loading response to JSON: {}'.format(e.__class__.__name__, str(e))
            response_object = self.build_response(success=False, reason=reason, message=msg, data=response_json)

        if not response_object.success:
            logging.error(response_object.message)
        logging.debug('************* {} returning {} object {}'.format(self.__class__.__name__, response_type.__name__,
                                                                       response_object.to_json()))
        return response_object

    async def async_make_request(self, message: M) -> R:
        """
        Async send the given request and return the corresponding response.

        Send (within Python's async functionality) the appropriate type of request :class:`Message` for this client
        implementation type and return the response as a corresponding, appropriate :class:`Response` instance.

        Parameters
        ----------
        message : M
            The request message object.

        Returns
        -------
        response : R
            The request response object.
        """
        response_type = self.get_response_subtype()
        expected_req_type = response_type.get_response_to_type()
        my_class_name = self.__class__.__name__
        req_class_name = message.__class__.__name__

        if not isinstance(message, expected_req_type):
            reason = '{} Received Unexpected Type {}'.format(my_class_name, req_class_name)
            msg = '{} received unexpected {} instance as request, rather than a {} instance; not submitting'.format(
                my_class_name, req_class_name, expected_req_type.__name__)
            logger.error(msg)
            return self.build_response(success=False, reason=reason, message=msg)

        response_json = {}
        try:
            # Send the request and get the service response
            serialized_response = await self.async_send(data=str(message), await_response=True)
            if serialized_response is None:
                raise ValueError('Serialized response from {} async message was `None`'.format(my_class_name))
        except Exception as e:
            reason = '{} Send {} Failure ({})'.format(my_class_name, req_class_name, e.__class__.__name__)
            msg = '{} encountered {} sending {}: {}'.format(my_class_name, e.__class__.__name__, req_class_name, str(e))
            logger.error(msg)
            return self.build_response(success=False, reason=reason, message=msg, data=response_json)

        return self._process_request_response(serialized_response)


class SchedulerClient(InternalServiceClient[SchedulerRequestMessage, SchedulerRequestResponse]):

    @classmethod
    def get_response_subtype(cls) -> Type[SchedulerRequestResponse]:
        return SchedulerRequestResponse

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

    async def get_results(self):
        logging.debug('************* {} preparing to yield results'.format(self.__class__.__name__))
        async for message in self.connection:
            logging.debug('************* {} yielding result: {}'.format(self.__class__.__name__, str(message)))
            yield message

class MaasRequestClient(WebSocketClient, Generic[EXTERN_REQ_M, EXTERN_REQ_R], ABC):

    @staticmethod
    def _request_failed_due_to_expired_session(response_obj: EXTERN_REQ_R):
        """
        Test if request failed due to an expired session.

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

    @classmethod
    def _run_validation(cls, message: Union[EXTERN_REQ_M, EXTERN_REQ_R]):
        """
        Run validation for the given message object using the appropriate validator subtype.

        Parameters
        ----------
        message
            The message to validate, which will be either a ``ExternalRequest``  or a ``ExternalRequestResponse`` subtype.

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
        elif isinstance(message, NGENRequest):
            is_valid, error = NWMRequestJsonValidator().validate(message.to_dict())
            return is_valid, error
        elif isinstance(message, Serializable):
            return message.__class__.factory_init_from_deserialized_json(message.to_dict()) == message, None
        else:
            raise RuntimeError('Unsupported ExternalRequest subtype: ' + str(message.__class__))

    def __init__(self, endpoint_uri: str, ssl_directory: Path, *args, **kwargs):
        super().__init__(endpoint_uri=endpoint_uri, ssl_directory=ssl_directory)

        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created, self._is_new_session = None, None, None, None

        self._errors = None
        self._warnings = None
        self._info = None

    def _acquire_new_session(self):
        try:
            return get_or_create_eventloop().run_until_complete(self._async_acquire_new_session())
        except Exception as e:
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

    async def _async_acquire_new_session(self, cached_session_file: Optional[Path] = None):
        try:
            logger.info("Connection to request handler web socket")
            auth_details = await self.authenticate_over_websocket(cached_session_file=cached_session_file)
            logger.info("auth_details returned")
            self._session_id, self._session_secret, self._session_created = auth_details
            self._is_new_session = True
            return True
        except ConnectionResetError as e:
            logger.info("Expecting exception to follow")
            logger.exception("Failed _acquire_session_info")
            return False
        except Exception as e:
            logger.info("Expecting exception to follow")
            logger.exception("Failed _acquire_session_info")
            return False

    @abstractmethod
    def _update_after_valid_response(self, response: EXTERN_REQ_R):
        """
        Perform any required internal updates immediately after a request gets back a successful, valid response.

        This provides a way of extending the behavior of this type specifically regarding the ::method:make_maas_request
        function. Any updates specific to the type, which should be performed after a request receives back a valid,
        successful response object, can be implemented here.

        In the base implementation, no further action is taken.

        See Also
        -------
        ::method:make_maas_request
        """
        pass

    # TODO: this can probably be taken out, as the superclass implementation should suffice
    async def async_make_request(self, request: EXTERN_REQ_M) -> EXTERN_REQ_R:
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            await websocket.send(request.to_json())
            response = await websocket.recv()
            return request.__class__.factory_init_correct_response_subtype(json_obj=json.loads(response))

    def parse_session_auth_text(self, auth_text: str):
        auth_response = json.loads(auth_text)
        # TODO: consider making sure this parses to a SessionInitResponse
        maas_session_id = auth_response['data']['session_id']
        maas_session_secret = auth_response['data']['session_secret']
        maas_session_created = auth_response['data']['created']
        return maas_session_id, maas_session_secret, maas_session_created

    # TODO: ...
    async def authenticate_over_websocket(self, cached_session_file: Optional[Path] = None):
        async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
            #async with websockets.connect(self.maas_endpoint_uri) as websocket:
            # return await EditView._authenticate_over_websocket(websocket)
            # Right now, it doesn't matter as long as it is valid
            # TODO: Fix this to not be ... fixed ...
            json_as_dict = {'username': 'someone', 'user_secret': 'something'}
            # TODO: validate before sending
            await websocket.send(json.dumps(json_as_dict))
            response_txt = await websocket.recv()
            try:
                if cached_session_file is not None and not cached_session_file.is_dir() \
                        and cached_session_file.parent.is_dir():
                    cached_session_file.write_text(response_txt)
            except Exception as e:
                # TODO: consider logging something here, but for now just handle so a bad save file doesn't tank us
                pass
            #print('*************** Auth response: ' + json.dumps(response_txt))
            return self.parse_session_auth_text(response_txt)

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

    def make_maas_request(self, maas_request: EXTERN_REQ_M, force_new_session: bool = False):
        request_type_str = maas_request.__class__.__name__
        logger.debug("client Making {} type request".format(request_type_str))
        self._acquire_session_info(force_new=force_new_session)
        # Make sure to set if empty or reset if a new session was forced and just acquired
        if force_new_session or maas_request.session_secret is None:
            maas_request.session_secret = self._session_secret
        # If able to get session details, proceed with making a job request
        if self._session_secret is not None:
            print("******************* Request: " + maas_request.to_json())
            try:
                is_request_valid, request_validation_error = self._run_validation(message=maas_request)
                if is_request_valid:
                    try:
                        response_obj: EXTERN_REQ_R = get_or_create_eventloop().run_until_complete(
                            self.async_make_request(maas_request))
                        print('***************** Response: ' + str(response_obj))
                        # Try to get a new session if session is expired (and we hadn't already gotten a new session)
                        if self._request_failed_due_to_expired_session(response_obj) and not force_new_session:
                            return self.make_maas_request(maas_request=maas_request, force_new_session=True)
                        elif not self.validate_maas_request_response(response_obj):
                            raise RuntimeError('Invalid response received for requested job: ' + str(response_obj))
                        elif not response_obj.success:
                            template = 'Request failed (reason: {}): {}'
                            raise RuntimeError(template.format(response_obj.reason, response_obj.message))
                        else:
                            self._update_after_valid_response(response_obj)
                            return response_obj
                    except Exception as e:
                        # TODO: log error instead of print
                        msg_template = 'Encountered error submitting {} over session {} : \n{}: {}'
                        msg = msg_template.format(request_type_str, str(self._session_id), str(type(e)), str(e))
                        print(msg)
                        traceback.print_exc()
                        self.errors.append(msg)
                else:
                    msg_template = 'Could not submit invalid MaaS request over session {} ({})'
                    msg = msg_template.format(str(self._session_id), str(request_validation_error))
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

    def validate_maas_request_response(self, maas_request_response: EXTERN_REQ_R):
        return self._run_validation(message=maas_request_response)[0]

    @property
    @abstractmethod
    def warnings(self):
        pass


class DataServiceClient(InternalServiceClient[DatasetManagementMessage, DatasetManagementResponse]):
    """
    Client for data service communication between internal DMOD services.
    """
    @classmethod
    def get_response_subtype(cls) -> Type[DatasetManagementResponse]:
        return DatasetManagementResponse


class ModelExecRequestClient(MaasRequestClient[MOD_EX_M, MOD_EX_R], ABC):

    def __init__(self, endpoint_uri: str, ssl_directory: Path):
        super().__init__(endpoint_uri=endpoint_uri, ssl_directory=ssl_directory)

    def _update_after_valid_response(self, response: MOD_EX_R):
        """
        Perform any required internal updates immediately after a request gets back a successful, valid response.

        This provides a way of extending the behavior of this type specifically regarding the ::method:make_maas_request
        function. Any updates specific to the type, which should be performed after a request receives back a valid,
        successful response object, can be implemented here.

        In this implementation, the ::attribute:`info` property is appended to, noting that the job of the given id has
        just been started by the scheduler.

        See Also
        -------
        ::method:make_maas_request
        """
        #self.job_id = self.resp_as_json['data']['job_id']
        #results = self.resp_as_json['data']['results']
        #jobs = self.resp_as_json['data']['all_jobs']
        #self.info.append("Scheduler started job, id {}, results: {}".format(self.job_id, results))
        #self.info.append("All user jobs: {}".format(jobs))
        self.info.append("Scheduler started job, id {}".format(response.data['job_id']))


class PartitionerServiceClient(InternalServiceClient[PartitionRequest, PartitionResponse]):
    """
    A client for interacting with the partitioner service.

    Because it is for the partitioner service, and this service is internal to the system and not publicly exposed, this
    does not need to be a (public) ::class:`MaasRequestClient` based type.
    """

    @classmethod
    def get_response_subtype(cls) -> Type[PartitionResponse]:
        """
        Return the response subtype class appropriate for this client implementation.

        Returns
        -------
        Type[PartitionResponse]
            The response subtype class appropriate for this client implementation.
        """
        return PartitionResponse
