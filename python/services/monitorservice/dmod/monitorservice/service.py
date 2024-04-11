#!/usr/bin/env python3
from abc import ABC, abstractmethod
from asyncio import CancelledError, sleep
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
from dmod.scheduler.job import Job, JobStatus
from dmod.communication import MetadataPurpose, MetadataMessage, MetadataResponse, UpdateMessage, UpdateMessageResponse,\
    WebSocketInterface
from dmod.monitor import Monitor
from typing import Dict, List, Optional, Set, Tuple
import json
import logging
import uuid

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)


class MonitoredChange:
    """
    Simple private type to help keep track of a monitored change that will need an update sent out to one or more
    registered parties.
    """

    __slots__ = ["job", "original_status", "connection_id"]

    def __eq__(self, other):
        return isinstance(other, MonitoredChange) \
               and self.connection_id == other.connection_id \
               and self.original_status == other.original_status \
               and self.job.job_id == other.job.job_id \
               and self.job.status == other.job.status

    def __init__(self, job: Job, original_status: JobStatus, connection_id: str):
        self.job: Job = job
        self.original_status: JobStatus = original_status
        self.connection_id: str = connection_id


class MonitorService(ABC):
    """
    Core abstract class for monitor service, handling main service logic but abstracting connection details.

    The ::method:`exec_monitoring` method can be used to construct an async looping task to continuously monitor (in a
    poll/sleep manner) for changes.  Alternatively, ::method:`run_monitor_check` can run the logic for monitoring and
    queueing changes a single time.

    Connection details are abstracted, but certain things must be done by implementation when handling connections.
    First, details of opening connection and controlling what is monitored should be done over serialized
    ::class:`MetadataMessage` objects.  Actual changes should be communicated via serialized ::class:`UpdateMessage`
    object.

    When being established, a new connection needs to be associated with a unique identifier and set up for the
    ::method:`get_connection_object` method and ::attribute:`jobs_of_interest_by_connection` property.  The logic for
    much of this is provided in the ::method:`handle_connection_begin` function.  However, details for the actual
    connection and connection object are abstracted here, so that must be done by something else in subclasses (e.g.,
    a `listener` function).

    The initial `CONNECT` ::class:`MetadataMessage` may include an explicit group of jobs of interest.  This is done by
    including a config change entry keyed by the string returned by ::method:`get_jobs_of_interest_config_key`.  It must
    be a list of strings.  If the key is not present, all active jobs will be assumed to be of interest.
    """

    _JOBS_OF_INTEREST_CONFIG_KEY = 'jobs_of_interest'
    """ The config key value for use in metadata messages to indicate the list of jobs of interest. """

    @staticmethod
    def _generate_update_msg(monitored_change: MonitoredChange) -> UpdateMessage:
        return UpdateMessage(object_id=str(monitored_change.job.job_id),
                             object_type=monitored_change.job.__class__,
                             updated_data={'status': str(monitored_change.job.status)})

    @staticmethod
    def _proc_connect_json(json_msg: str, conn_id: str) -> Tuple[Optional[MetadataMessage], bool, str]:
        """
        Process incoming message contents at start of a listener connection.

        Function first takes the raw JSON string from the initial message establishing a connection and deserializes
        it into a metadata object (if possible).  It then saves a determination of whether the metadata conforms as
        required for creating a connection.  Finally, an informational message is constructed, either indicating the
        metadata can successfully open a connection or explaining why the metadata is invalid for doing so. These three
        items are then returned.

        If the raw message text doesn't deserialize to a metadata object, the function will have (and eventually return)
        a reference to `None` instead.  This also is a condition considered to not conform validly for creating the
        connection.

        Parameters
        ----------
        json_msg: str
            The raw JSON message (as a string) sent over the websocket.
        conn_id: str
            The connection id of the associated connection, used in return information message.

        Returns
        -------
        Tuple[Optional[MetadataMessage], bool, str]
            Tuple of the deserialized ::class:`MetadataMessage` (or `None` if the JSON was not valid), whether the
            metadata was valid for creating a connection, and an informational message relating to the (non)validity of
            the metadata.
        """
        metadata = MetadataMessage.factory_init_from_deserialized_json(json.loads(json_msg))
        if not metadata:
            return None, False, 'Invalid format of message JSON creating connection {} [{}]'.format(conn_id, json_msg)

        if metadata.purpose != MetadataPurpose.CONNECT:
            return metadata, False, 'Incorrect metadata PURPOSE creating connection {} [{}]'.format(conn_id, json_msg)

        if metadata.metadata_follows:
            return metadata, False, 'Further metadata indicated creating connection {} [{}]'.format(conn_id, json_msg)

        return metadata, True, 'Successfully opening connection with id: {}'.format(conn_id)

    @classmethod
    def get_jobs_of_interest_config_key(cls):
        """
        Get the config key value for use in metadata messages to indicate the list of jobs of interest.

        This is the key that should be present in initial `CONNECT` or later `CHANGE_CONFIG` metadata message, within
        the ::attribute:`MetadataMessage.config_changes` property, to indicate a specific list of jobs of interest for
        that particular client.

        Returns
        -------
        str
            The config key value for use in metadata messages to indicate the list of jobs of interest.
        """
        return cls._JOBS_OF_INTEREST_CONFIG_KEY

    def __init__(self, monitor: Monitor):
        self._monitor = monitor
        self._jobs_of_interest_by_connection = {}
        """ Collections of jobs of interest for registered connections, keyed by the connection id. """
        self._mapped_change_queues_by_connection: Dict[str, List[MonitoredChange]] = {}
        """ Lists of monitored job changes that should have updates sent out, keyed by connection id to send over."""

    def _apply_metadata_config_change(self, connection_id: str, metadata: MetadataMessage) -> Tuple[bool, str]:
        """
        Apply changes as described in a ::class:`MetadataMessage`, applicable to the given connection.

        Parameters
        ----------
        metadata
        connection_id

        Returns
        -------
        Tuple[bool, str]
            Whether the changes were applied and an explanatory string on the reason why or why not.
        """
        # TODO: actually come back and implement this later
        # For now, don't apply any changes, and since we don't, return False
        return False, 'Not Currently Supported By Service'

    def _dequeue_monitored_change(self, connection_id: str) -> Optional[MonitoredChange]:
        """
        Pop the next queued monitored change to send an update across the listener connection with the given id.

        From the queue of monitored changes of interest to the connection with the given id, remove and return the next
        change.  The expectation is that this will be used to send an update about the job's state over the
        aforementioned connection, as part of the ::method:`listener` method handling that websocket.

        In the event there are no monitored changes queued that require updates for this connection, simply return
        ``None``.

        Parameters
        ----------
        connection_id : str
            The unique id for the connection for which the next update to send is needed.

        Returns
        -------
        Optional[MonitoredChange]
            The next monitored change that needs to have an update sent over this connection, or ``None`` if there is
            no such change/updated necessary currently.

        See Also
        -------
        ::method:`listener`
        """
        if connection_id not in self._mapped_change_queues_by_connection:
            return None
        changes_queue = self._mapped_change_queues_by_connection[connection_id]
        # For reference, truth value testing as done below should yield False for None or empty sequence/collection.
        # See https://docs.python.org/3/library/stdtypes.html#truth-value-testing
        return changes_queue.pop(0) if changes_queue else None

    def _enqueue_monitored_change(self, change_obj: MonitoredChange):
        """
        Append a monitored change (that will require an update be sent over the associated connection) to the queue of
        such changes for the relevant websocket connection.

        Parameters
        ----------
        change_obj
        """
        if change_obj.connection_id not in self._mapped_change_queues_by_connection:
            self._mapped_change_queues_by_connection[change_obj.connection_id] = []
        self._mapped_change_queues_by_connection[change_obj.connection_id].append(change_obj)

    def _get_interested_connections(self, job_id: str) -> Set[str]:
        """
        Get the set of connection ids for connected listeners (via ::method:`listener`) that explicitly or implicitly
        registered to receive updates on the job with the given id.

        Returns
        -------
        Set[str]
            The set of connection ids for connected listeners that should receive updates on the job with the given id.
        """
        connection_ids = set()
        for connection_id in self.jobs_of_interest_by_connection:
            if self._is_connection_interested(connection_id, job_id):
                connection_ids.add(connection_id)
        return connection_ids

    def _is_connection_interested(self, connection_id: str, job_id: str) -> bool:
        """
        Return whether a connection is interested in updates for monitored changes of the job with the given id.

        Parameters
        ----------
        connection_id : str
            Connection string id key, as originally created by ::method:`listener`.
        job_id : str
            Identifier for some job.

        Returns
        -------
        bool
            Whether a connection is interested in updates for monitored changes of the job with the given id.
        """

        if connection_id not in self.jobs_of_interest_by_connection:
            return False
        job_ids_of_interest = self.jobs_of_interest_by_connection[connection_id]
        return job_ids_of_interest is None or job_id in job_ids_of_interest

    def _proc_metadata_jobs_of_interest(self, metadata_obj: MetadataMessage) -> Optional[List[str]]:
        """
        Process a ::class:`MetadataMessage` object to extract jobs of interest.

        Process a ::class:`MetadataMessage` object to extract contained collection of jobs of interest, returning `None`
        if no explicit collection is provided (thus implying `ALL`).  Raise ::class:`RuntimeError` if the collection is
        present but not formatted validly as either a list or set of job id strings.

        If a valid collection is presented as a set, also convert to a list before returning.

        Parameters
        ----------
        metadata_obj

        Returns
        -------

        Raises
        -------
        RuntimeError
            If a collection of jobs of interest is found but not formatted as either a list or set of strings.

        """
        if not (metadata_obj.config_changes and self._JOBS_OF_INTEREST_CONFIG_KEY in metadata_obj.config_changes):
            return None
        jobs_of_interest_subset = metadata_obj.config_changes[self._JOBS_OF_INTEREST_CONFIG_KEY]
        if not (isinstance(jobs_of_interest_subset, list) or isinstance(jobs_of_interest_subset, set)):
            raise RuntimeError('Invalid metadata with non-list \'jobs-of-interest\' collection')

        for i in jobs_of_interest_subset:
            if not isinstance(i, str):
                raise RuntimeError('Invalid metadata with non-string id value in \'jobs-of-interest\' list')

        return list(jobs_of_interest_subset)

    @abstractmethod
    async def communicate_change(self, change: MonitoredChange):
        """
        Inform the associated client of this monitored change.

        Inform some client, associated by the connection id contained in the change object, of the encapsulated change.

        Parameters
        ----------
        change: MonitoredChange
            Object containing a change found in monitoring and the id of a client needing to know about the change.
        """
        pass

    async def exec_monitoring(self):
        """
        Async task performing repeating, regular monitoring tasks within service, and queuing monitored changes that
        are of interest to parties with current connections to the service.

        See Also
        ----------
        ::method:`run_monitor_check`
        """
        while True:
            self.run_monitor_check()
            await sleep(60)

    @abstractmethod
    def get_connection_object(self, connection_id: str):
        """
        Get the object encapsulating some identified connection.

        Parameters
        ----------
        connection_id: str
            The identifier for the connection.

        Returns
        -------
        The desired connection object.
        """
        pass

    def handle_connection_begin(self, message: str) -> Tuple[str, Optional[MetadataMessage], MetadataResponse]:
        """
        Helper method for tasks to do at the beginning of a connection.

        Parameters
        ----------
        message: str
            The raw JSON string included in the first message, expected to be a serialized ::class:`MetadataMessage`.

        Returns
        -------
        Tuple[str, Optional[MetadataMessage], MetadataResponse]
            The generated id for this connection, a metadata message object deserialized from the message (if possible),
            and a metadata response object with deals on whether connect is successful.
        """
        connection_id = str(uuid.uuid4())
        # Process the incoming connection message
        metadata_obj, connect_success, response_txt = self._proc_connect_json(message, connection_id)
        # TODO: any other steps to initialize connection (e.g., need auth or session key)?
        # If things are valid, extract the (potentially implied) jobs of interest
        if connect_success:
            try:
                self.jobs_of_interest_by_connection[connection_id] = self._proc_metadata_jobs_of_interest(metadata_obj)
            # Consider an exception during this to override connection success
            except RuntimeError as re:
                connect_success = False
                response_txt = str(re) + ' while creating connection {} [{}]'.format(connection_id, message)

        # Send a response, along with success indicator and message
        response = MetadataResponse.factory_create(connect_success, response_txt, MetadataPurpose.CONNECT, False)
        response.data.connection_id = connection_id
        return connection_id, metadata_obj, response

    @property
    def jobs_of_interest_by_connection(self) -> Dict[str, Optional[Set[str]]]:
        """
        A mapping of how connected external entities have registered interest in receiving updates about monitored jobs.

        A mapping to maintain how websocket-connected parties have registered to receive updates to monitored jobs.
        Keys for the dictionary are a "conn_id" value generated within and unique to a particular invocation of
        ::method:`listener` and only used by that method.  The associate value represents the set of jobs for which
        the connected party would like to receive update, as monitored changes are observed.

        The mapped values will either be ``None`` or a set of the ids (cast as strings) for the jobs of interest.  A
        value of ``None`` implies that all active jobs are of interest.

        Returns
        -------
        Dict[str, Optional[Set[str]]]
            A mapping of how connected external entities have registered to receive updates about monitored jobs.

        See Also
        -------
        ::method:`listener`
        """
        return self._jobs_of_interest_by_connection

    def run_monitor_check(self):
        """
        Run a single check to monitor for jobs that have changed.

        Run a single check monitoring for jobs that have changed, and enqueue such changes for any interested
        connections.

        This is called from within each loop iteration of the async looping ::method:`exec_monitoring` function. It is
        separated from the async routine for easier testing.

        See Also
        ----------
        ::method:`exec_monitoring`
        """
        # The are all dicts keyed by the job id value
        jobs_with_changed_status, original_job_statuses, updated_job_statuses = self._monitor.monitor_jobs()

        for job_id in jobs_with_changed_status:
            interested_connections = self._get_interested_connections(job_id)
            # If there are any interested connection, then for each ...
            for connection_id in interested_connections:
                # Create a change object to cleanly encapsulate the monitored change
                change_obj = MonitoredChange(job=jobs_with_changed_status[job_id],
                                             original_status=original_job_statuses[job_id],
                                             connection_id=connection_id)
                self._enqueue_monitored_change(change_obj)


class WebSocketMonitorService(MonitorService, WebSocketInterface):
    """
    Implementation of ::class:`MonitorService` listening for connections over websocket.
    """

    def __init__(self, monitor: Monitor, *args, **kwargs):
        super().__init__(monitor=monitor)
        super().__init__(*args, **kwargs)
        self._websockets_by_connection = {}

    async def communicate_change(self, change: MonitoredChange):
        """
        Inform the client for this connection of a monitored change.

        Inform the client connected over the associated websocket of the change encapsulated by the
        ::class:`MonitoredChange` object, via serialized ::class:`UpdateMessage`.

        Checks whether a proper ::class:`UpdateMessageResponse` is sent back, including whether the digest matches and
        whether the object was found on the client side.  However, only logs warnings if for encountered unexpected
        conditions.

        Method will get stuck in an `await` until at least something comes back over the websocket.

        Parameters
        ----------
        change: MonitoredChange
            The change found in monitoring to communicate.
        """
        websocket = self.get_connection_object(connection_id=change.connection_id)
        update_msg = self._generate_update_msg(change)
        await websocket.send(str(update_msg))
        update_resp_txt = await websocket.recv()
        update_resp = UpdateMessageResponse.factory_init_from_deserialized_json(json.loads(update_resp_txt))
        if update_resp is None:
            logging.warning("Failed deserializing update response for job {}".format(change.job.job_id))
        elif update_resp.digest != update_msg.digest:
            logging.warning(
                "Digest mismatch in update response for job {} (expected {}; received: {})".format(
                    change.job.job_id, update_msg.digest, update_resp.digest))
        elif not update_resp.object_found:
            logging.warning("Client couldn't find job {} for update".format(change.job.job_id))

    def get_connection_object(self, connection_id: str) -> WebSocketServerProtocol:
        """
        Get the object encapsulating some identified connection.

        Parameters
        ----------
        connection_id
            The identifier for the connection.

        Returns
        -------
        The desired connection object.
        """
        return self._websockets_by_connection[connection_id]

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Handle a connection to a party that wants to receive updates about jobs as changes are monitored, sending update
        messages back over the maintained websocket as appropriate.

        Each invocation of the method creates a corresponding ``conn_id`` to uniquely identify this particular
        websocket connection and method instance.  This is used in multiple instance attributes to separate things
        applicable to this particular connection.  It is implemented as a string representation of a version 4 UUID.

        The instance also maintains a dictionary of per-connection queues that store data for monitored changes deemed
        to be of interest to the connection.  Again, as these queues are per connection, the containing dictionary is
        keyed by ``conn_id``.

        Parameters
        ----------
        websocket
        path
        """
        connection_id = None
        try:
            # Handle the initial incoming message, which should be a metadata CONNECT
            connection_id, metadata, response = self.handle_connection_begin(await websocket.recv())
            await websocket.send(str(response))
            if not response.success:
                raise RuntimeError("Closing listener connection after failure in protocol: " + response.reason)
            self._websockets_by_connection[connection_id] = websocket
            while True:
                # This will be None if there are no more queued changes for this connection to hear about
                change = self._dequeue_monitored_change(connection_id)
                if isinstance(change, MonitoredChange):
                    await self.communicate_change(change)
                elif self.process_connection_after_updates(connection_id):
                    await sleep(60)
                else:
                    break
        except ConnectionClosed as cce:
            logging.info("Connection Closed at Consumer", cce)
        except CancelledError as ce:
            logging.info("Cancelling listener task", ce)
        except RuntimeError as re:
            logging.info(str(re))
        finally:
            if connection_id:
                # Clean up registered websocket connection
                if connection_id in self._websockets_by_connection:
                    self._websockets_by_connection.pop(connection_id)
                # Clean up values from jobs_of_interest for this connection
                if connection_id in self.jobs_of_interest_by_connection:
                    self.jobs_of_interest_by_connection.pop(connection_id)
                # Clean up values from _mapped_change_queues_by_connection for this connection
                change_queue = self._mapped_change_queues_by_connection.pop(connection_id)
                if isinstance(change_queue, list) and len(change_queue) > 0:
                    msg = "There were {} monitored updates of interest but not communicated to connection {}."
                    logging.warning(msg.format(str(len(change_queue)), connection_id))

    async def process_connection_after_updates(self, connection_id: str) -> bool:
        """
        Handle metadata communication protocol that occurs after updates are sent through a connection, returning
        whether the connection should remain open.

        Parameters
        ----------
        connection_id : str
            The connection identifier, as a string.

        Returns
        -------
        bool
            `True` when this websocket connection should remain open for further update communication, or `False` when
            the connection should be closed.

        Raises
        -------
        RuntimeError
            Raised if the message protocol is not followed as expected.

        See Also
        -------
        ::method:`_apply_metadata_config_change`
        """
        websocket = self.get_connection_object(connection_id=connection_id)
        # Default to keeping the connection open
        keep_connection_open = True

        try:
            # Prompt metadata start if other party has metadata it needs to send
            prompt_msg = MetadataMessage(purpose=MetadataPurpose.PROMPT,
                                         description='Prompt for changes to jobs or disconnect')
            await websocket.send(str(prompt_msg))
            prompt_resp = await websocket.recv()
            prompt_resp_obj = MetadataResponse.factory_init_from_deserialized_json(json.loads(prompt_resp))
            # If this happens, it tried to send something else and is outside of protocol, so close connection
            if not prompt_resp_obj:
                prompt_resp_err_txt = 'Unexpected response to metadata prompt in connection {} [{}]'
                raise RuntimeError(prompt_resp_err_txt.format(connection_id, prompt_resp))
            expecting_metadata = True
            while expecting_metadata:
                metadata_msg = await websocket.recv()
                metadata_obj = MetadataMessage.factory_init_from_deserialized_json(json.loads(metadata_msg))
                if not metadata_obj:
                    metadata_msg_err_txt = 'Invalid metadata message JSON in connection {} [{}]'
                    raise RuntimeError(metadata_msg_err_txt.format(connection_id, metadata_msg))
                # Start by adjusting expecting_metadata if this indicated nothing follows it
                expecting_metadata = metadata_obj.metadata_follows
                # Process metadata message, depending on purpose
                if metadata_obj.purpose == MetadataPurpose.DISCONNECT:
                    success, reason, keep_connection_open = True, 'Disconnect Receive', False
                elif metadata_obj.purpose == MetadataPurpose.UNCHANGED:
                    success, reason = True, 'No Changes'
                elif metadata_obj.purpose == MetadataPurpose.CHANGE_CONFIG:
                    success, reason = self._apply_metadata_config_change(connection_id, metadata_obj)
                elif metadata_obj.purpose in {MetadataPurpose.PROMPT, MetadataPurpose.CONNECT}:
                    msg_txt = 'Unexpected purpose {} to prompted metadata message on connection {}'
                    raise RuntimeError(msg_txt.format(metadata_obj.purpose.name, connection_id))
                else:
                    success, reason = False, 'Unexpected Purpose'
                # Then build and send the response
                response = MetadataResponse.factory_create(success, reason, metadata_obj.purpose, expecting_metadata)
                await websocket.send(str(response))
        except RuntimeError as re:
            logging.error("Exception in post-update monitor connection protocol:" + str(re))
            keep_connection_open = False
        return keep_connection_open
