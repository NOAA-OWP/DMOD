import asyncio
import datetime
import json
import ssl
import typing
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from deprecated import deprecated
from pathlib import Path
from typing import Generic, Optional, Type, TypeVar, Union

import websockets

from .maas_request import ExternalRequest, ExternalRequestResponse
from .message import AbstractInitRequest, Response
from .partition_request import PartitionResponse
from .dataset_management_message import DatasetManagementResponse
from .scheduler_request import SchedulerRequestResponse
from .evaluation_request import EvaluationConnectionRequestResponse
from .update_message import UpdateMessage, UpdateMessageResponse

import logging

# TODO: refactor this to allow for implementation-specific overriding more easily
logger = logging.getLogger("gui_log")

CONN = TypeVar("CONN")

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


class TransportLayerClient(ABC):
    """
    Abstract client capable of communicating with a server at some endpoint.

    Abstract client for interacting with a service at the OSI transport layer.  It provides an interface for sending
    data to accept data and send this data to a server at some endpoint.  The interface function for this behavior
    supports optionally waiting for and returning a raw data response.  Alternatively, the type provides a function for
    receiving a response from the server independently.

    Instances are capable of securing communications using an ::class:`SSLContext`.  A customized context or default
    context can be created, depending on the parameters passed during init.
    """

    @classmethod
    @abstractmethod
    def get_endpoint_protocol_str(cls, use_secure_connection: bool = True) -> str:
        """
        Get the protocol substring portion for valid connection URI strings for an instance of this class.

        Parameters
        ----------
        use_secure_connection : bool
            Whether to get the protocol substring applicable for secure connections (``True`` by default).

        Returns
        -------
        str
            The protocol substring portion for valid connection URI strings for an instance of this class.
        """
        pass

    def __init__(self, endpoint_host: str, endpoint_port: Union[int, str], endpoint_path: Optional[str] = None,
                 cafile: Optional[Path] = None, capath: Optional[Path] = None, use_default_context: bool = False,
                 *args, **kwargs):
        """
        Initialize this instance.

        Initialization may or may not include creation of an ::class:`SSLContext`, according to these rules:
            - If ``cafile`` is ``None``, ``capath`` is ``None``, and ``use_default_context`` is ``False`` (which are the
              default values for each), then no ::class:`SSLContext` is created.
            - If ``use_default_context`` is ``True``, ::function:`ssl.create_default_context` is used to create a
              context object, with ``cafile`` and ``capath`` passed as kwargs.
            - If either ``cafile`` or ``capath`` is not ``None``, and ``use_default_context`` is ``False``, a customized
              context object is created, with certificates loaded from locations at ``cafile`` and/or ``capath``.

        Parameters
        ----------
        endpoint_host: str
            The host component for building this client's endpoint URI for opening a connection.
            The endpoint for the client to connect to when opening a connection.
        endpoint_port: Union[int, str]
            The host port component for building this client's endpoint URI for opening a connection.
        endpoint_path: Optional[str]
            The optional path component for building this client's endpoint URI for opening a connection.
        cafile: Optional[Path]
            Optional path to CA certificates PEM file.
        capath: Optional[Path]
            Optional path to directory containing CA certificates PEM files, following an OpenSSL specific layout (see
            ::function:`ssl.SSLContext.load_verify_locations`).
        use_default_context: bool
            Whether to use ::function:`ssl.create_default_context` to create a ::class:`SSLContext` (default ``False``).
        args
            Other unused positional parameters.
        kwargs
            Other unused keyword parameters.
        """
        super().__init__(*args, **kwargs)

        self._endpoint_host: str = endpoint_host.strip()
        self._endpoint_port = endpoint_port.strip() if isinstance(endpoint_port, str) else endpoint_port
        self._endpoint_path: str = '' if endpoint_path is None else endpoint_path.strip()

        self._endpoint_uri = None

        if use_default_context:
            self._client_ssl_context = ssl.create_default_context(cafile=cafile, capath=capath)
        elif cafile is not None or capath is not None:
            self._client_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self._client_ssl_context.load_verify_locations(cafile=cafile, capath=capath)
        else:
            self._client_ssl_context = None

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
    def endpoint_uri(self) -> str:
        """
        The endpoint for the client to connect to when opening a connection.

        Returns
        -------
        str
            The endpoint for the client to connect to when opening a connection.
        """
        pass

    @property
    def client_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        The client SSL context for securing connections, if one was created.

        Returns
        -------
        Optional[ssl.SSLContext]
            The client SSL context for securing connections, if one was created; otherwise ``None``.
        """
        return self._client_ssl_context


class AuthClient:
    """
    Simple client object responsible for handling acquiring and applying authenticated session details to requests.
    """
    def __init__(self, transport_client: TransportLayerClient, *args, **kwargs):
        self._transport_client: TransportLayerClient = transport_client
        # TODO: get full session implementation if possible
        self._session_id, self._session_secret, self._session_created = None, None, None
        self._force_reauth = False

    def _acquire_session(self) -> bool:
        """
        Synchronous function to acquire an authenticated session.

        Wrapper convenience function for use outside of the async event loop.

        Returns
        -------
        bool
            Whether acquiring an authenticated session was successful.

        See Also
        -------
        _async_acquire_session
        """
        try:
            return get_or_create_eventloop().run_until_complete(self._async_acquire_session())
        except Exception as e:
            msg = f"{self.__class__.__name__} failed to acquire auth credential due to {e.__class__.__name__}: {str(e)}"
            logger.error(msg)
            return False

    async def _async_acquire_session(self) -> bool:
        """
        Acquire an authenticated session.

        Returns
        -------
        bool
            Whether acquiring an authenticated session was successful.
        """
        # Clear anything previously set when forced reauth
        if self.force_reauth:
            self._session_id, self._session_secret, self._session_created = None, None, None
            self.force_reauth = False
        # Otherwise, if we have the session details already, just return True
        elif all([self._session_id, self._session_secret, self._session_created]):
            return True

        try:
            auth_resp = await self._transport_client.async_send(data=json.dumps(self._prepare_auth_request_payload()),
                                                                await_response=True)
            return self._parse_auth_data(auth_resp)
        # In the future, consider whether we should treat ConnectionResetError separately
        except Exception as e:
            msg = f"{self.__class__.__name__} failed to acquire auth credential due to {e.__class__.__name__}: {str(e)}"
            logger.error(msg)
            return False

    def _parse_auth_data(self, auth_data_str: str):
        """
        Parse serialized authentication data and update instance state accordingly.

        Parse the given serialized authentication data and update the state of the instance accordingly to represent the
        successful authentication (assuming the data parses appropriately).  This method must support, at minimum,
        parsing the text data returned from the service as the response to the authentication payload,

        Note that a return value of ``True`` indicates the instance holds valid authentication details that can be
        applied to requests.

        Parameters
        ----------
        auth_data_str : str
            The data to be parsed, such as that returned in the service response to an authentication payload.

        Returns
        ----------
        bool
            Whether parsing was successful.
        """
        try:
            auth_response = json.loads(auth_data_str)
            # TODO: consider making sure this parses to a SessionInitResponse
            session_id = auth_response['data']['session_id']
            session_secret = auth_response['data']['session_secret']
            session_created = auth_response['data']['created']
            if all((session_id, session_secret, session_created)):
                self._session_id, self._session_secret, self._session_created = session_id, session_secret, session_created
                return True
            else:
                return False
        except Exception as e:
            return False

    def _prepare_auth_request_payload(self) -> dict:
        """
        Generate JSON payload to be transmitted by ::method:`async_acquire_session` to service when requesting auth.

        Returns
        -------
        dict
            The JSON payload to be transmitted by ::method:`async_acquire_session` to the service when requesting auth.
        """
        # Right now, it doesn't matter as long as it is valid
        # TODO: Fix this to not be ... fixed ...
        return {'username': 'someone', 'user_secret': 'something'}

    async def apply_auth(self, external_request: ExternalRequest) -> bool:
        """
        Apply appropriate authentication details to this request object, acquiring them first if needed.

        Parameters
        ----------
        external_request : ExternalRequest
            A request that needs the appropriate session secret applied.

        Returns
        ----------
        bool
            Whether the secret was obtained and applied successfully.
        """
        if await self._async_acquire_session():
            external_request.session_secret = self._session_secret
            return True
        else:
            return False

    @property
    def force_reauth(self) -> bool:
        """
        Whether the client should be forced to reacquire a new authenticated session from the service.

        Returns
        -------
        bool
            Whether the client should be forced to re-authenticate and get a new session from the auth service.
        """
        return self._force_reauth

    @force_reauth.setter
    def force_reauth(self, should_force_new: bool):
        self._force_reauth = should_force_new

    @property
    def session_created(self) -> Optional[str]:
        return self._session_created

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id


class CachedAuthClient(AuthClient):
    """
    Extension of ::class:`AuthClient` that supports caching the session to a file.
    """

    def __init__(self, session_file: Optional[Path] = None, *args, **kwargs):
        """
        Initialize this instance, including creating empty session-related attributes.

        If a ``session_file`` is not given, a default path in the home directory with a timestamp-based name will be
        used.  If ``session_file`` is a directory, similiarly a timestamp-based default basename will be used for a file
        in this directory.

        Parameters
        ----------
        session_file : Optional[Path]
            Optional specified path to file for a serialized session, both for loading from and saving to.
        args
        kwargs

        Keyword Args
        ----------
        endpoint_uri : str
            The endpoint for the client to connect to when opening a connection, for ::class:`RequestClient`
            superclass init.
        """
        super().__init__(*args, **kwargs)

        self._is_new_session = None
        self._force_reload = False

        default_basename = '.dmod_session'

        if session_file is None:
            self._cached_session_file = Path.home().joinpath(default_basename)
        elif session_file.is_dir():
            self._cached_session_file = session_file.joinpath(default_basename)
        else:
            self._cached_session_file = session_file

        assert isinstance(self._cached_session_file, Path)
        assert self._cached_session_file.is_file() or not self._cached_session_file.exists()

    async def _async_acquire_session(self) -> bool:
        """
        Acquire an authenticated session.

        Returns
        -------
        bool
            Whether acquiring an authenticated session was successful.
        """
        if not self._check_if_new_session_needed():
            return True

        try:
            auth_resp = await self._transport_client.async_send(data=json.dumps(self._prepare_auth_request_payload()),
                                                                await_response=True)
            # Execute the call to the parsing function before attempting to write, but don't set the attributes yet
            session_attribute_vals_tuple = self._parse_auth_data(auth_resp)

            # Need a nested try block here to control what happens with a failure to cache the session
            try:
                self._cached_session_file.write_text(auth_resp)
            except Exception as inner_e:
                # TODO: consider having parameters/attributes to control exactly how this is handled ...
                #  ... for now just catch and pass so a bad save file doesn't tank us
                msg = f"{self.__class__.__name__} successfully authenticated but failed to cache details to file " \
                      f"'{str(self._cached_session_file)}' due to {inner_e.__class__.__name__}: {str(inner_e)}"
                logger.warning(msg)
                pass

            # Wait until after the cache file write section to modify any instance state
            self._session_id, self._session_secret, self._session_created = session_attribute_vals_tuple
            self.force_reauth = False
            self._is_new_session = True
            return True
        # In the future, consider whether we should treat ConnectionResetError separately
        except Exception as e:
            msg = f"{self.__class__.__name__} failed to acquire auth credential due to {e.__class__.__name__}: {str(e)}"
            logger.error(msg)
            return False

    def _check_if_new_session_needed(self) -> bool:
        """
        Check if a new session is required, potentially loading a cached session from an implementation-specific source.

        Check whether a new session must be acquired.  As a side effect, potentially load a cached session from a source
        specific to this type as an alternative to acquiring a new session.

        For the default implementation of this function, the source for a cached session is a serialized session file.

        For a new session to be needed, there must be no other **acceptable** source of authenticated session data.

        If ::attribute:`force_reauth` is set to ``True``, any currently stored session attributes are cleared and the
        function returns ``True``.  Nothing is loaded from a cached session file.

        If ::attribute:`force_reload` is set to ``True``, any currently stored session attributes are cleared. However,
        the function does not return at this point, and instead proceeds with remaining logic.

        The session attributes of this instance subsequently checked for acceptable session data.  If at this point they
        are all properly set (i.e., non-``None`` and non-empty) and ::attribute:`force_reload` is ``False``, then the
        function returns ``False``.

        If any session attributes are not properly set or ::attribute:`force_reload` is ``True``, the function attempts
        to load a session from the cached session file.  If valid session attributes can be loaded, the function then
        returns ``False``.  If they could not be loaded, the function will return ``True``, indicating a new session
        needs to be acquired.

        The function will return ``False`` IFF all session attributes are non-``None`` and non-empty at the end of the
        function's execution.

        Returns
        -------
        bool
            Whether a new session must be acquired.
        """
        # If we need to re-auth, clear any old session data and immediately return True (i.e., new session is needed)
        if self.force_reauth:
            self._session_id, self._session_secret, self._session_created = None, None, None
            return True

        # If we need to reload, also clear any old session data, but this time proceed with the rest of the function
        if self.force_reload:
            self._session_id, self._session_secret, self._session_created = None, None, None
            # Once we force clearing these to ensure a reload is attempted, reset the attribute
            self.force_reload = False
        # If not set to force a reload, we may already have valid session attributes; short here if so
        elif all([self._session_id, self._session_secret, self._session_created]):
            return False

        # If there is a cached session file, we will try to load from it
        if self._cached_session_file.exists():
            try:
                session_id, secret, created = self._parse_auth_data(self._cached_session_file.read_text())
                # Only set if all three read properties are valid
                if all([session_id, secret, created]):
                    self._session_id = session_id
                    self._session_secret = secret
                    self._session_created = created
                    self._is_new_session = False
            except Exception as e:
                pass
            # Return opposite of whether session properties are now set correctly (that would mean don't need a session)
            return not all([self._session_id, self._session_secret, self._session_created])
        else:
            return True

    @property
    def force_reload(self) -> bool:
        """
        Whether client should be forced to reload cached auth data on the next call to ::method:`async_acquire_session`.

        Note that this property will be (re)set to ``False`` after the next call to ::method:`async_acquire_session`.

        Returns
        -------
        bool
            Whether to force reloading cached auth data on the next called to ::method:`async_acquire_session`.
        """
        return self._force_reload

    @force_reload.setter
    def force_reload(self, should_force_reload: bool):
        self._force_reload = should_force_reload

    @property
    def is_new_session(self) -> Optional[bool]:
        """
        Whether the current session was obtained newly from the service, as opposed to read from cache.

        Returns
        -------
        Optional[bool]
            Whether the current session was obtained newly from the service, as opposed to read from cache; ``None`` if
            no session is yet acquired/loaded.
        """
        return self._is_new_session


class RequestClient:
    """
    Simple DMOD service client, dealing with DMOD request message and response objects.

    Basic client type for interaction with a DMOD service. Its primary function, ::method:`async_make_request`, accepts
    some DMOD ::class:`AbstractInitRequest` object, uses a ::class:`TransportLayerClient` to submit the request object
    to a service, and receives/returns the service's response.

    To parse responses, instances must know the appropriate class type for a response.  This can be provided as an
    optional parameter to ::method:`async_make_request`.  A default response class type can also be supplied to an
    instance during init, which is used by ::method:`async_make_request` if a class type is not provided.  One of the
    two must be set for ::method:`async_make_request` to function.
    """

    def __init__(self, transport_client: TransportLayerClient, default_response_type: Optional[Type[Response]] = None,
                 *args, **kwargs):
        """
        Initialize.

        Parameters
        ----------
        transport_client : TransportLayerClient
            The client for handling the underlying raw OSI transport layer communications with the service.
        default_response_type: Optional[Type[Response]]
            Optional class type for responses, to use when no response class param is given when making a request.
        args
        kwargs
        """
        self._transport_client = transport_client
        self._default_response_type: Optional[Type[Response]] = default_response_type

    def _process_request_response(self, response_str: str, response_type: Optional[Type[Response]] = None) -> Response:
        """
        Process the serial form of a response returned by ::method:`async_send` into a response object.

        Parameters
        ----------
        response_str : str
            The string returned by a request made via ::method:`async_send`.
        response_type: Optional[Type[Response]]
            An optional class type for the response that, if ``None`` (the default) is replaced with the default
            provided at initialization.

        Returns
        -------
        Response
            The inflated response object.

        See Also
        -------
        async_send
        """
        if response_type is None:
            response_type = self._default_response_type

        response_json = {}
        try:
            # Consume the response confirmation by deserializing first to JSON, then from this to a response object
            response_json = json.loads(response_str)
            try:
                response_object = response_type.factory_init_from_deserialized_json(response_json)
                if response_object is None:
                    msg = f'********** {self.__class__.__name__} could not deserialize {response_type.__name__} ' \
                          f'from raw websocket response: `{str(response_str)}`'
                    reason = f'{self.__class__.__name__} Could Not Deserialize To {response_type.__name__}'
                    response_object = response_type(success=False, reason=reason, message=msg, data=response_json)
            except Exception as e2:
                msg = f'********** While deserializing {response_type.__name__}, {self.__class__.__name__} ' \
                      f'encountered {e2.__class__.__name__}: {str(e2)}'
                reason = f'{self.__class__.__name__} {e2.__class__.__name__} Deserialize {response_type.__name__}'
                response_object = response_type(success=False, reason=reason, message=msg, data=response_json)
        except Exception as e:
            reason = 'Invalid JSON Response'
            msg = f'Encountered {e.__class__.__name__} loading response to JSON: {str(e)}'
            response_object = response_type(success=False, reason=reason, message=msg, data=response_json)

        if not response_object.success:
            logging.error(response_object.message)
        logging.debug(f'{self.__class__.__name__} returning {str(response_type)} {response_str}')
        return response_object

    async def async_make_request(self, message: AbstractInitRequest, response_type: Optional[Type[Response]] = None) -> Response:
        """
        Async send a request message object and return the received response.

        Send (within Python's async functionality) the appropriate type of request :class:`Message` for this client
        implementation type and return the response as a corresponding, appropriate :class:`Response` instance.

        Parameters
        ----------
        message : AbstractInitRequest
            The request message object.
        response_type: Optional[Type[Response]]
            An optional class type for the response that, if ``None`` (the default) is replaced with the default
            provided at initialization.

        Returns
        -------
        Response
            the request response object
        """
        if response_type is None:
            if self._default_response_type is None:
                msg = f"{self.__class__.__name__} can't make request with neither response type parameter or default"
                raise RuntimeError(msg)
            else:
                response_type = self._default_response_type

        response_json = {}
        try:
            # Send the request and get the service response
            serialized_response = await self._transport_client.async_send(data=str(message), await_response=True)
            if serialized_response is None:
                raise ValueError(f'Serialized response from {self.__class__.__name__} async message was `None`')
        except Exception as e:
            reason = f'{self.__class__.__name__} Send {message.__class__.__name__} Failure ({e.__class__.__name__})'
            msg = f'Sending {message.__class__.__name__} raised {e.__class__.__name__}: {str(e)}'
            logger.error(msg)
            return response_type(success=False, reason=reason, message=msg, data=response_json)

        assert isinstance(serialized_response, str)
        return self._process_request_response(serialized_response)


class ConnectionContextClient(Generic[CONN], TransportLayerClient, ABC):
    """
    Transport client subtype that maintains connections via an async managed contexts.

    Instances of this type will increment an active connections counter upon entering the context.  If the counter was
    at ``0``, a new connection will be opened using ::method:`_establish_connection` and assigned to
    ::attribute:`connection`.  The reverse happens on context close, with ::method:`_close_connection` being used to
    close the connection once the counter is ``0`` again.

    Subtypes should provide implementations for ::method:`_establish_connection` and ::method:`_close_connection`.

    Implementations of ::method:`async_send` and ::method:`async_recv` functions are provided.  They can be used without
    already being in an active context (i.e., they will enter a new context for the scope of the function). However,
    within in an already open context, calls to ::method:`async_send` and ::method:`async_recv` can be used as needed to
    support arbitrarily communication over the websocket.

    The ::method:`async_send` and ::method:`async_recv` implementations depend on ::method:`_connection_send` and
    ::method:`_connection_recv`, which must be provided by subtypes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection: typing.Optional[CONN] = None
        """Optional[CONN]: The open connection, if set, for this client's context."""

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
        if self._connection is None:
            # If not, mark that this exec is opening a connection, before giving up control during the await
            self._opening_connection = True
            # Then asynchronously open the connection ...
            try:
                self._connection = await self._establish_connection()
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
            await self._close_connection()
            self._connection = None
            self.active_connections = 0

    @abstractmethod
    async def _connection_recv(self) -> Optional[str]:
        """
        Perform operations to receive data over already opened ::attribute:`connection`.

        Returns
        -------
        Optional[str]
            Data received over already opened ::attribute:`connection`.
        """
        pass

    @abstractmethod
    async def _connection_send(self, data: Union[str, bytearray]):
        """
        Perform operations to send data over already opened ::attribute:`connection`.

        Parameters
        ----------
        data
            The data to send.
        """
        pass

    @abstractmethod
    async def _close_connection(self):
        """
        Close the managed context's established connection.
        """
        pass

    @abstractmethod
    async def _establish_connection(self) -> CONN:
        """
        Establish a connection for the managed context.

        Returns
        -------
        CONN
            A newly established connection.
        """
        pass

    async def async_send(self, data: Union[str, bytearray], await_response: bool = False):
        """
        Send data over connection, by default returning immediately, but optionally receiving and returning response.

        The function will cause the runtime context to be entered, opening a connection if needed.  In such cases,
        the connection will also be closed at the conclusion of this function.

        Parameters
        ----------
        data: Optional[str]
            The data to send.
        await_response
            Whether the method should also await a response on the connection and return it.

        Returns
        -------
        Optional[str]
            The response to the sent data, if one should be awaited; otherwise ``None``.
        """
        async with self as connection_owner:
            await connection_owner._connection_send(data)
            return await connection_owner._connection_recv() if await_response else None

    async def async_recv(self) -> Union[str, bytes]:
        """
        Receive data over the connection.

        Returns
        -------
        Union[str, bytes]
            The data received over the connection.
        """
        with self as connection_owner:
            return await connection_owner._connection_recv()

    @property
    def connection(self) -> Optional[CONN]:
        return self._connection


class WebSocketClient(ConnectionContextClient[websockets.WebSocketClientProtocol]):
    """
    Subtype of ::class:`ConnectionContextClient` that specifically works over SSL-secured websocket connections.

    A websocket-based implementation of ::class:`ConnectionContextClient`.  Instances are also async context managers for
    runtime contexts that handle websocket connections, with the manager function returning the instance itself.

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
    def get_endpoint_protocol_str(cls, use_secure_connection: bool = True) -> str:
        """
        Get the protocol substring portion for valid connection URI strings for an instance of this class.

        Parameters
        ----------
        use_secure_connection : bool
            Whether to get the protocol substring applicable for secure connections (``True`` by default).

        Returns
        -------
        str
            The protocol substring portion for valid connection URI strings for an instance of this class.
        """
        return 'wss' if use_secure_connection else 'ws'

    async def _connection_recv(self) -> Optional[str]:
        """
        Perform operations to receive data over already opened ::attribute:`connection`.

        Returns
        -------
        Optional[str]
            Data received over already opened ::attribute:`connection`.
        """
        return await self.connection.recv()

    @abstractmethod
    async def _connection_send(self, data: Union[str, bytearray]):
        """
        Perform operations to send data over already opened ::attribute:`connection`.

        Parameters
        ----------
        data
            The data to send.
        """
        await self.connection.send(data)

    async def _close_connection(self):
        """
        Close the managed context's established connection.
        """
        await self.connection.close()

    async def _establish_connection(self) -> CONN:
        """
        Establish a connection for the managed context.

        Returns
        -------
        CONN
            A newly established connection.
        """
        return await websockets.connect(self.endpoint_uri, ssl=self.client_ssl_context)

    @property
    def endpoint_uri(self) -> str:
        """
        The endpoint for the client to connect to when opening a connection.

        Returns
        -------
        str
            The endpoint for the client to connect to when opening a connection.
        """
        if self._endpoint_uri is None:
            proto = self.get_endpoint_protocol_str(use_secure_connection=self.client_ssl_context is not None)

            if self._endpoint_path and self._endpoint_path[0] != '/':
                path_str = '/' + self._endpoint_path
            else:
                path_str = self._endpoint_path

            self._endpoint_uri = f"{proto}://{self._endpoint_host}:{self._endpoint_port!s}{path_str}"
        return self._endpoint_uri

    async def listen(self) -> typing.Union[str, bytes]:
        """
        Waits for a message through the websocket connection

        Returns:
            A string for data sent through the socket as a string and bytes for data sent as binary
        """
        async with self as websocket:
            return await websocket.connection.recv()


@deprecated("Use RequestClient or ExternalRequestClient instead")
class SchedulerClient(RequestClient):

    def __init__(self, *args, **kwargs):
        super().__init__(default_response_type=SchedulerRequestResponse, *args, **kwargs)

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
            serialized_response = await self._transport_client.async_send(data=str(message), await_response=True)
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


class ExternalRequestClient(RequestClient):

    def __init__(self, auth_client: AuthClient, *args, **kwargs):
        """
        Initialize instance.

        Parameters
        ----------
        args
        kwargs

        Other Parameters
        ----------
        transport_client: TransportLayerClient
        """
        super().__init__(*args, **kwargs)

        self._auth_client: AuthClient = auth_client

        self._errors = None
        self._warnings = None
        self._info = None

    async def async_make_request(self, message: ExternalRequest,
                                 response_type: Optional[Type[ExternalRequestResponse]] = None) -> ExternalRequestResponse:
        """
        Async send a request message object and return the received response.

        Send (within Python's async functionality) the appropriate type of request :class:`Message` for this client
        implementation type and return the response as a corresponding, appropriate :class:`Response` instance.

        Parameters
        ----------
        message : ExternalRequest
            The request message object.
        response_type: Optional[Type[ExternalRequestResponse]]
            An optional class type for the response that, if ``None`` (the default) is replaced with the default
            provided at initialization.

        Returns
        -------
        EXTERN_REQ_R
            the request response object
        """
        if response_type is None:
            response_type = self._default_response_type

        if await self._auth_client.apply_auth(message):
            return await super().async_make_request(message, response_type=response_type)
        else:
            reason = f'{self.__class__.__name__} Request Auth Failure'
            msg = f'{self.__class__.__name__} async_make_request could not apply auth to {message.__class__.__name__}'
            logger.error(msg)
            return response_type(success=False, reason=reason, message=msg)

    @property
    def errors(self):
        return self._errors

    @property
    def info(self):
        return self._info

    @property
    def warnings(self):
        return self._warnings


@deprecated("Use RequestClient or ExternalRequestClient instead")
class DataServiceClient(RequestClient):
    """
    Client for data service communication between internal DMOD services.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(default_response_type=DatasetManagementResponse, *args, **kwargs)


@deprecated("Use RequestClient or ExternalRequestClient instead")
class PartitionerServiceClient(RequestClient):
    """
    A client for interacting with the partitioner service.

    Because it is for the partitioner service, and this service is internal to the system and not publicly exposed, this
    does not need to be a (public) ::class:`ExternalRequestClient` based type.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(default_response_type=PartitionResponse, *args, **kwargs)


@deprecated("Use RequestClient or ExternalRequestClient instead")
class EvaluationServiceClient(RequestClient):
    """
    A client for interacting with the evaluation service
    """
    def __init__(self, *args, **kwargs):
        super().__init__(default_response_type=EvaluationConnectionRequestResponse, *args, **kwargs)
