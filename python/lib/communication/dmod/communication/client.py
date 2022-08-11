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


class AbstractClient(ABC):
    """
    Abstract client capable of securely communicating with a server at some endpoint.

    Abstract client with an interface for securely sending data to a server at some endpoint.  The interface function
    for this behavior supports optionally waiting for and returning a raw response.  Alternatively, the type provides an
    interface for receiving a response from the server independently.
    """
    def __init__(self, endpoint_uri: str, *args, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
        endpoint_uri: str
            The endpoint for the client to connect to when opening a connection.
        args
            Other unused positional parameters.
        kwargs
            Other unused keyword parameters.
        """
        super().__init__(*args, **kwargs)

        self.endpoint_uri = endpoint_uri
        """str: The endpoint for the client to connect to when opening a connection."""

    @abstractmethod
    async def async_send(self, data: Union[str, bytearray, bytes], await_response: bool = False) -> Optional[str]:
        """
        Send data to server, either returning immediately after or optionally waiting for and returning the response.

        Parameters
        ----------
        data: Union[str, bytearray, bytes]
            The data to send.
        await_response: bool
            Whether the method should also await a response on from the server connection and return it.

        Returns
        -------
        Optional[str]
            The server's response to the sent data, if one should be awaited; or ``None``
        """
        pass

    @abstractmethod
    async def async_recv(self) -> str:
        """
        Receive data from server.

        Returns
        -------
        str
            The data received from the server, as a string.
        """
        pass

    @property
    @abstractmethod
    def client_ssl_context(self) -> ssl.SSLContext:
        """
        Get the client SSL context property.

        Returns
        -------
        ssl.SSLContext
            The client SSL context for secure connections.
        """
        pass


class ExternalClient(AbstractClient, ABC):
    """
    Abstract client encapsulating the logic for using external connections secured using sessions.

    Abstract client type that requires connections that work using secure sessions.  It is able to serialize session
    details to a file and, by default, load them from this file if appropriate.
    """

    def __init__(self, session_file: Optional[Path] = None, *args, **kwargs):
        """
        Initialize this instance, including creating empty session-related attributes.

        If a ``session_file`` is not given, a default path in the home directory with a timestamp-based name will be
        used.

        Parameters
        ----------
        session_file : Optional[Path]
            Optional path to file for a serialized session, both for loading from and saving to.
        args
        kwargs

        Keyword Args
        ----------
        endpoint_uri : str
            The endpoint for the client to connect to when opening a connection, for ::class:`RequestClient`
            superclass init.
        """
        super().__init__(*args, **kwargs)
        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created, self._is_new_session = None, None, None, None
        if session_file is None:
            self._cached_session_file = Path.home().joinpath(
                '.{}_session'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S%s')))
        else:
            self._cached_session_file = session_file

    def _acquire_new_session(self):
        try:
            return get_or_create_eventloop().run_until_complete(self._async_acquire_new_session())
        except Exception as e:
            logger.info("Expecting exception to follow")
            logger.exception("Failed _acquire_session_info")
            return False

    def _acquire_session_info(self, use_current_values: bool = True, force_new: bool = False) -> bool:
        """
        Attempt to set the session information properties needed for a secure connection.

        Parameters
        ----------
        use_current_values : bool
            Whether to use currently held attribute values for session details, if already not None (disregarded if
            ``force_new`` is ``True``).
        force_new : bool
            Whether to force acquiring a new session, regardless of data available is available on an existing session.

        Returns
        -------
        bool
            Whether session details were acquired and set successfully.
        """
        logger.debug("{}._acquire_session_info:  getting session info".format(self.__class__.__name__))
        if not force_new and not self._check_if_new_session_needed(use_current_values=use_current_values):
            logger.debug('Using previously acquired session details (new session not forced)')
            return True
        else:
            logger.debug("Session from {}}: force_new={}".format(self.__class__.__name__, force_new))
            tmp = self._acquire_new_session()
            logger.debug("Session Info Return: {}".format(tmp))
            return tmp

    async def _async_acquire_session_info(self, use_current_values: bool = True, force_new: bool = False) -> bool:
        """
        Async attempt to set the session information properties needed for a secure connection.

        Parameters
        ----------
        use_current_values : bool
            Whether to use currently held attribute values for session details, if already not None (disregarded if
            ``force_new`` is ``True``).
        force_new : bool
            Whether to force acquiring a new session, regardless of data available is available on an existing session.

        Returns
        -------
        bool
            Whether session details were acquired and set successfully.
        """
        if not force_new and not self._check_if_new_session_needed(use_current_values=use_current_values):
            logger.debug('Using previously acquired session details (new session not forced)')
            return True
        else:
            tmp = await self._async_acquire_new_session(cached_session_file=self._cached_session_file)
            logger.debug("Session Info Return: {}".format(tmp))
            return tmp

    async def _async_acquire_new_session(self, cached_session_file: Optional[Path] = None):
        try:
            logger.info("Connection to request handler web socket")
            auth_details = await self.authenticate(cached_session_file=cached_session_file)
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

    def _check_if_new_session_needed(self, use_current_values: bool = True) -> bool:
        """
        Check if a new session is required, potentially loading a cached session from an implementation-specific source.

        Check whether a new session must be acquired.  As a side effect, potentially load a cached session from a source
        specific to this type as an alternative to acquiring a new session.

        For the default implementation of this function, the source for a cached session is a serialized session file.

        Loading of a cached session will not be done if ``use_current_values`` is ``True`` and session attributes are
        properly set (i.e., non-``None`` and non-empty).  Further, loaded cached session details will not be used if any
        is empty or ``None``.

        The function will return ``False`` IFF all session attributes are non-``None`` and non-empty at the end of the
        function's execution.

        Parameters
        ----------
        use_current_values : bool
            Whether it is acceptable to use the current values of the instance's session-related attributes, if all such
            attributes already have values set.

        Returns
        -------
        bool
            Whether a new session must be acquired.
        """
        # If we should use current values, and current values constitute a valid session, then we do not need a new one
        if use_current_values and all([self._session_id, self._session_secret, self._session_created]):
            return False
        # If there is a cached session file, we will try to load from it
        if self._cached_session_file.exists():
            try:
                session_id, secret, created = self.parse_session_auth_text(self._cached_session_file.read_text())
                # Only set if all three read properties are valid
                if all([session_id, secret, created]):
                    self._session_id = session_id
                    self._session_secret = secret
                    self._session_created = created
            except Exception as e:
                pass
            # Return opposite of whether session properties are now set correctly (that would mean don't need a session)
            return not all([self._session_id, self._session_secret, self._session_created])
        # Otherwise (i.e., don't/can't use current session details + no cached file to load), need a new session
        else:
            return True

    # TODO: ...
    async def authenticate(self, cached_session_file: Optional[Path] = None):
        #async with websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context) as websocket:
        #async with websockets.connect(self.maas_endpoint_uri) as websocket:
        # return await EditView._authenticate_over_websocket(websocket)
        # Right now, it doesn't matter as long as it is valid
        # TODO: Fix this to not be ... fixed ...
        json_as_dict = {'username': 'someone', 'user_secret': 'something'}
        response_txt = await self.async_send(data=json.dumps(json_as_dict), await_response=True)
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
    def is_new_session(self):
        return self._is_new_session

    def parse_session_auth_text(self, auth_text: str):
        auth_response = json.loads(auth_text)
        # TODO: consider making sure this parses to a SessionInitResponse
        maas_session_id = auth_response['data']['session_id']
        maas_session_secret = auth_response['data']['session_secret']
        maas_session_created = auth_response['data']['created']
        return maas_session_id, maas_session_secret, maas_session_created

    @property
    def session_created(self):
        return self._session_created

    @property
    def session_id(self):
        return self._session_id

    @property
    def session_secret(self):
        return self._session_secret


class WebSocketClient(AbstractClient, ABC):
    """
    Abstract subtype of ::class:`AbstractClient` that specifically works over websocket connections.

    An abstract websocket-based implementation of ::class:`AbstractClient`.  Instances are also async context managers
    for runtime contexts that handle websocket connections, with the manager function returning the instance itself.

    A new runtime context will check whether there is an open websocket connection already and open a connection if not.
    In all cases, it maintains an instance attribute that is a counter of the number of active usages of the connection
    (i.e., the number of separate, active contexts).  When the context is exited, the instance's active usage counter is
    reduced by one and, if that context represents the last active use of the connection, the connection object is
    closed and then has its reference removed.

    The ::method:`async_send` and ::method:`async_recv` functions can be used without already being in an active context
    (i.e., they will enter a new context for the scope of the function). However, within in an already open context,
    calls to ::method:`async_send` and ::method:`async_recv` can be used as needed to support arbitrarily communication
    over the websocket.
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

    def __init__(self, ssl_directory: Path, *args, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
        ssl_directory
        args
        kwargs

        Other Parameters
        ----------
        endpoint_uri : str
            The endpoint for the client to connect to when opening a connection, for superclass init.
        """
        super().__init__(*args, **kwargs)

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
        Send data to websocket, by default returning immediately, but optionally receiving and returning response.

        The function will cause the runtime context to be entered, opening a connection if needed.  In such cases,
        the connection will also be closed at the conclusion of this function.

        Parameters
        ----------
        data: Optional[str]
            The data to send.
        await_response
            Whether the method should also await a response on the websocket connection and return it.

        Returns
        -------
        Optional[str]
            The response to the sent data, if one should be awaited; otherwise ``None``.
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

    async def async_recv(self) -> Union[str, bytes]:
        """
        Receive data over the websocket connection.

        Returns
        -------
        Union[str, bytes]
            The data received over the connection.
        """
        with self as websocket:
            return await websocket.connection.recv()

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


class ExternalRequestClient(ExternalClient, WebSocketClient, Generic[EXTERN_REQ_M, EXTERN_REQ_R], ABC):

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

    def __init__(self, *args, **kwargs):
        """
        Initialize instance.

        Parameters
        ----------
        args
        kwargs

        Other Parameters
        ----------
        endpoint_uri : str
            The client connection endpoint for opening new websocket connections, required for superclass init.
        ssl_directory : Path
            The directory of the SSL certificate files for the client SSL context.
        session_file : Optional[Path]
            Optional path to file for a serialized session, both for loading from and saving to.
        """
        super().__init__(*args, **kwargs)

        self._errors = None
        self._warnings = None
        self._info = None

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

    @property
    def errors(self):
        return self._errors

    @property
    def info(self):
        return self._info

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

    def validate_maas_request_response(self, maas_request_response: EXTERN_REQ_R):
        return self._run_validation(message=maas_request_response)[0]

    @property
    def warnings(self):
        return self._warnings


class DataServiceClient(InternalServiceClient[DatasetManagementMessage, DatasetManagementResponse]):
    """
    Client for data service communication between internal DMOD services.
    """
    @classmethod
    def get_response_subtype(cls) -> Type[DatasetManagementResponse]:
        return DatasetManagementResponse


class ModelExecRequestClient(ExternalRequestClient[MOD_EX_M, MOD_EX_R], ABC):

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
    does not need to be a (public) ::class:`ExternalRequestClient` based type.
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
