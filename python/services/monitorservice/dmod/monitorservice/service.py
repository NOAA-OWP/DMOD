#!/usr/bin/env python3
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

    def __init__(self, job: Job, original_status: JobStatus, connection_id: str):
        self.job: Job = job
        self.original_status: JobStatus = original_status
        self.connection_id: str = connection_id


class MonitorService(WebSocketInterface):
    """
    Core class of the monitor service, handling communication and main logic.

    To use, ensure the ::method:`exec_monitoring` method is started within its own separate async task, then call the
    standard ::method:`run` method from ::class:`WebSocketInterface` to start the listener.

    Entities connecting to the service should send a ::class:`MetadataMessage` with the `CONNECT` purpose over the
    websocket to open the connection.  If desired, the a config change entry keyed by the string returned by
    ::method:`get_jobs_of_interest_config_key` can be added to explicitly set jobs of interest.  It must be a list of
    strings.  If the key is not present, all active jobs will be assumed.

    """

    _JOBS_OF_INTEREST_CONFIG_KEY = 'jobs_of_interest'
    """ The config key value for use in metadata messages to indicate the list of jobs of interest. """

    @staticmethod
    def _generate_update_msg(monitored_change: MonitoredChange) -> UpdateMessage:
        return UpdateMessage(object_id=str(monitored_change.job.job_id),
                             object_type=monitored_change.job.__class__,
                             updated_data={'status': str(monitored_change.job.status)})

    @classmethod
    async def _apply_metadata_config_change(cls, connection_id: str, metadata: MetadataMessage) -> Tuple[bool, str]:
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

    @classmethod
    async def process_connection_after_updates(cls, connection_id: str, websocket: WebSocketServerProtocol) -> bool:
        """
        Handle metadata communication protocol that occurs after updates are sent through a connection, returning
        whether the connection should remain open.

        Parameters
        ----------
        connection_id : str
            The connection identifier, as a string.
        websocket : WebSocketServerProtocol
            The websocket object for the connection.

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
                    success, reason = cls._apply_metadata_config_change(connection_id, metadata_obj)
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

    def __init__(self, monitor: Monitor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitor = monitor
        self._jobs_of_interest_by_connection = {}
        self._mapped_change_queues_by_connection: Dict[str, List[MonitoredChange]] = {}
        """ Lists of monitored job changes that should have updates sent out, keyed by connection id to send over."""

    async def _communicate_change(self, change: MonitoredChange, websocket: WebSocketServerProtocol):
        """
        Inform the client for this connection of a monitored change.

        Inform the client connected over the given websocket of the change encapsulated by the ::class:`MonitoredChange`
        object, via serialized ::class:`UpdateMessage`.

        Checks whether a proper ::class:`UpdateMessageResponse` is sent back, including whether the digest matches and
        whether the object was found on the client side.  However, only logs warnings if for encountered unexpected
        conditions.

        Method will get stuck in an `await` until at least something comes back over the websocket.

        Parameters
        ----------
        change: MonitoredChange
            The change found in monitoring to communicate.
        websocket: WebSocketServerProtocol
            The websocket object for the connection to use for communication
        """
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

    def _enqueue_monitored_change_update_for_connection(self, change_obj: MonitoredChange):
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

    async def _handle_connect(self, websocket: WebSocketServerProtocol, connection_id: str):
        """
        Handle processing the initial connection message for the listener.

        Handle processing the initial connection message for a newly-connected websocket, including initial receipt and
        parsing of the message contents, which should be a metadata `CONNECT` type.  Then send the appropriate response
        acknowledging.  If the incoming message was invalid, raise an exception (after sending the response).

        Note that the received message should indicate that the sender does not have any further metadata to send after
        this message. Method ensures the message is formatted correctly.

        Method will set the appropriate value in the ::attribute:`jobs_of_interest_by_connection` property for
        `connection_id`, in cases when the `CONNECT` message was valid.  This will be the default of `None` (inferred to
        mean `ALL`) if nothing is explicitly supplied.

        Parameters
        ----------
        websocket: WebSocketServerProtocol
            The incoming websocket object for the connection.
        connection_id: str
            The identifier for this particular connection.

        Returns
        -------
        tuple
            The deserialized metadata message object; whether the message was valid for a successful connection opening;
            some response text for the metadata response; and the optional, extracted collection of jobs of interest.
        """
        message = await websocket.recv()
        # TODO: any other steps to initialize connection (e.g., need auth or session key)?
        metadata_obj = MetadataMessage.factory_init_from_deserialized_json(json.loads(message))
        if not metadata_obj:
            connect_success = False
            response_txt = 'Invalid format of message JSON creating connection {} [{}]'.format(connection_id, message)
        elif metadata_obj.purpose != MetadataPurpose.CONNECT:
            connect_success = False
            response_txt = 'Invalid metadata with incorrect `purpose` when creating connection {} [{}]'.format(
                connection_id, message)
            # This should not be the case when originating the connection
        elif metadata_obj.metadata_follows:
            connect_success = False
            response_txt = 'Invalid metadata having following metadata creating connection {} [{}]'.format(
                connection_id, message)
        else:
            connect_success = True
            response_txt = 'Successfully opening connection with id: {}'.format(connection_id)

        # Also check that any list of jobs of interest is provided correctly
        jobs_of_interest_subset = None
        if metadata_obj.config_changes and self._JOBS_OF_INTEREST_CONFIG_KEY in metadata_obj.config_changes:
            jobs_of_interest_subset = metadata_obj.config_changes[self._JOBS_OF_INTEREST_CONFIG_KEY]
            if not (isinstance(jobs_of_interest_subset, list) or isinstance(jobs_of_interest_subset, set)):
                connect_success = False
                response_txt = 'Invalid metadata with non-list \'jobs-of-interest\' collection creating ' \
                               'connection {} [{}]'.format(connection_id, message)
            else:
                for i in jobs_of_interest_subset:
                    if not isinstance(i, str):
                        connect_success = False
                        response_txt = 'Invalid metadata with non-string id value in \'jobs-of-interest\' ' \
                                       'list when creating connection {} [{}]'.format(connection_id, message)
                        break

        # Send the response, along with success indicator and message
        response = MetadataResponse.factory_create(connect_success, response_txt, metadata_obj.purpose, False)
        await websocket.send(str(response))

        if not connect_success:
            raise RuntimeError("Closing listener connection after failure in connection protocol: " + response_txt)

        self.jobs_of_interest_by_connection[connection_id] = jobs_of_interest_subset

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

    async def exec_monitoring(self):
        """
        Async task performing repeating, regular monitoring tasks within service, and queuing monitored changes that
        are of interest to parties with current websocket connections to the service.
        """
        while True:
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
                    self._enqueue_monitored_change_update_for_connection(change_obj)

            await sleep(60)

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

    async def listener(self, websocket: WebSocketServerProtocol, path):
        """
        Handle a connection to a party that wants to receive updates about jobs as changes are monitored, sending update
        messages back over the maintained websocket as appropriate.

        Each invocation of the method creates a corresponding ``connection_id`` to uniquely identify this particular
        websocket connection and method instance.  This is used in multiple instance attributes to separate things
        applicable to this particular connection.  It is implemented as a string representation of a version 4 UUID.

        The instance also maintains a dictionary of per-connection queues that store data for monitored changes deemed
        to be of interest to the connection.  Again, as these queues are per connection, the containing dictionary is
        keyed by ``connection_id``.

        Parameters
        ----------
        websocket
        path
        """
        connection_id = str(uuid.uuid4())
        try:
            # Handle the initial incoming message, which should be a metadata CONNECT
            await self._handle_connect(websocket, connection_id)
            while True:
                # This will be None if there are no more queued changes for this connection to hear about
                change = self._dequeue_monitored_change(connection_id)
                if isinstance(change, MonitoredChange):
                    await self._communicate_change(change, websocket)
                elif self.process_connection_after_updates(connection_id, websocket):
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
            # Clean up values from jobs_of_interest for this connection
            if connection_id in self.jobs_of_interest_by_connection:
                self.jobs_of_interest_by_connection.pop(connection_id)
            # Clean up values from _mapped_change_queues_by_connection for this connection
            change_queue = self._mapped_change_queues_by_connection.pop(connection_id)
            if isinstance(change_queue, list) and len(change_queue) > 0:
                msg = "There were {} monitored updates of interest but not communicated to connection {}."
                logging.warning(msg.format(str(len(change_queue)), connection_id))
