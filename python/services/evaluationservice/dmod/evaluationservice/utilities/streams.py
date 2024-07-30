"""
Provides functions and structures used to streamline communication with a Key-Value Store's Data Stream
"""
from __future__ import annotations

import os
import typing
import dataclasses
import multiprocessing
from functools import partial

from datetime import timedelta
from time import sleep
from operator import iconcat as combine
from functools import reduce

import redis

import service
from .kvstore import KVStoreArguments


RawRedisMessage = typing.Tuple[bytes, typing.Dict[bytes, bytes]]
"""
How each individual message is represented - a tuple indicating the message id and a dictionary of each key and value
"""

RawRedisMessageStream = typing.List[typing.Union[bytes, typing.List[RawRedisMessage]]]
"""
How each collection of messages is represented when reading from a stream.
This is implemented via a list, but a tuple would be more appropriate. The first index is the stream name and the 
second index is the collection of messages read for it
"""

LATEST_MESSAGE: typing.Final[str] = ">"
"""
The `xreadgroup` function uses a dictionary of '{<stream name>: <previously read message id>}' to determine what next 
to read. Using '{<stream name>: ">"}' will tell it to get the next unread message for <stream name>
"""

BACKUP_CONSUMER_NAME: typing.Final[str] = "backup-consumer"
"""
The name of a stream group consumer that will take ownership of messages when a consumer closes before being able to 
acknowledge their work
"""


IDLE_TIMEOUT: typing.Final[int] = int(timedelta(hours=6, minutes=30).total_seconds()) * 1000
"""
The maximum amount of milliseconds a message is allowed to be idle in a consumer before it will be claimed by a 
backup consumer
"""


@dataclasses.dataclass
class StreamParameters:
    """
    Parameters used to connect to a key value store data stream
    """
    kvstore_parameters: typing.Optional[KVStoreArguments] = dataclasses.field(default=None)
    stream_name: typing.Optional[str] = dataclasses.field(default=None)
    group_name: typing.Optional[str] = dataclasses.field(default=None)

    @property
    def is_valid(self) -> bool:
        """
        Whether this is a valid set of details that may be used to connect to a key value store for a data stream
        """
        return self.stream_name is not None and self.group_name is not None

    def get_connection(self) -> redis.Redis:
        """
        Create a connection to a key value store that will be communicated with via stream

        Returns:
            A connection to the configured key value store
        """
        if not self.is_valid:
            raise ValueError(f"{self} is not valid - a connection for a stream cannot be established")

        if not self.kvstore_parameters:
            self.kvstore_parameters = KVStoreArguments()

        return self.kvstore_parameters.get_connection()

    def __str__(self):
        return (f"{self.group_name or 'No Group'} in the {self.stream_name or 'undefined'} stream at "
                f"{self.kvstore_parameters or 'a local Key Value Store'}")

    def __repr__(self):
        return self.__str__()


@dataclasses.dataclass
class StreamMessage:
    """
    Represents a message sent through a redis stream
    """
    stream_name: str
    """The name of the stream that this travelled through"""

    group_name: str
    """The name of the group that is readding the message"""

    consumer_name: str
    """The name of the consumer reading the message"""

    message_id: str
    """The ID of the message that was sent"""

    payload: typing.Dict[str, str]
    """The payload of the message that was sent"""

    @classmethod
    def listen(
        cls,
        connection: redis.Redis,
        group_name: str,
        consumer_name: str,
        stop_signal: multiprocessing.Event,
        stream: str
    ) -> typing.Generator[StreamMessage, None, None]:
        """
        Get the next message in the indicated stream

        Args:
            connection: A redis connection to read from
            group_name: The group that the reader belongs to
            consumer_name: The name of the reader
            stop_signal: The signal to stop listening for messages
            stream: The name of the stream to read from

        Returns:
            All new messages from the indicated streams
        """
        # Create a dict of {"name": ">"} to tell the redis client to read the latest message from the
        streams: typing.Dict[str, str] = {stream: LATEST_MESSAGE}

        while not stop_signal.is_set():
            try:
                # Read a single message from any of the possible streams and assign them to the given consumer name
                #   for the given group
                # This adds a single message from any of the given streams to the group's PEL, assigning it to the given
                #   consumer
                #       - Call `xack` to remove it from the consumer and announce that the given group won't look at it
                #       - Call `xclaim` to assign the message to another consumer within the group
                messages_per_stream: typing.List[RawRedisMessageStream] = connection.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams=streams,
                    count=1,
                    block=1000
                )
            except Exception as read_exception:
                message = (f"Could not read the latest unread messages from the '{', '.join(streams)}' stream(s) for the "
                           f"{consumer_name} consumer in the '{group_name}' group using a consumer named '{consumer_name}'")

                service.error(message, exception=read_exception)
                raise read_exception

            # Extract the contents of the difficultly formatted messages
            read_streams: typing.List[typing.List[StreamMessage]] = [
                cls.parse_stream(message_stream, group_name=group_name, consumer_name=consumer_name)
                for message_stream in messages_per_stream
            ]

            # Put all of the read messages into a single list
            messages: typing.List[StreamMessage] = reduce(combine, read_streams, [])

            if messages:
                service.info(
                    f"The following messages are now in the pending list for the consumer named {consumer_name}:"
                    f"{os.linesep}"
                    f"* {(os.linesep + '* ').join(message.message_id for message in messages)}"
                    f"{os.linesep}"
                )

                yield from messages
            else:
                sleep(1)

    @classmethod
    def parse_stream(
        cls,
        message_stream: RawRedisMessageStream,
        group_name: str,
        consumer_name: str,
    ) -> typing.List[StreamMessage]:
        """
        Convert all given collection of messages into a collection of concrete message objects

        Args:
            message_stream: The raw collection of messages. The first index is the stream name,
                the second is the collection of messages
            group_name: The name of the consumer group that will listen to for messages
            consumer_name: The name of the consumer reading the message

        Returns:
            A collection of concrete message objects
        """
        # Convert the name to the friendlier 'str' type
        stream_name: str = message_stream[0].decode()

        # Call the `parse` function on each received message to convert each collected message into the concrete type
        messages: typing.List[StreamMessage] = [
            cls.parse(stream_name=stream_name, raw_message=message, group_name=group_name, consumer_name=consumer_name)
            for message in message_stream[1]
        ]

        return messages

    @classmethod
    def parse(
        cls,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        raw_message: RawRedisMessage,
    ) -> StreamMessage:
        """
        Read the basic values from a message from a redis stream and form a concrete message object

        Args:
            stream_name: The name of the stream where this message originated
            group_name: The name of the consumer group that this message belongs to
            consumer_name: The name of the consumer reading the message
            raw_message: The raw message that was received

        Returns:
            A concrete message object
        """
        # The first index of the message is the ID in bytes, so convert that to a string
        message_id: str = raw_message[0].decode()
        return StreamMessage(
            stream_name=stream_name,
            message_id=message_id,
            group_name=group_name,
            consumer_name=consumer_name,
            payload={
                key.decode(): value.decode()
                for key, value in raw_message[1].items()
            }
        )


def initialize_consumer(
    stream_parameters: StreamParameters,
    consumer_name: str,
    initial_id: typing.Union[typing.Literal[0], str] = 0
):
    """
    Create a consumer for a stream group

    Args:
        stream_parameters: Instructions for how to connect to a stream group
        consumer_name: The name for the new consumer
        initial_id: The id of the earliest message in the stream to read. 0 indicates the first,
            "$" indicates new messages, and message ids like "1721309186793-0" indicate all messages that come AFTER
            that id
    """
    connection = stream_parameters.get_connection()
    service.info(
        f"Initializing a consumer named '{consumer_name}' for stream group '{stream_parameters.group_name}' for the "
        f"'{stream_parameters.stream_name}' stream"
    )

    # First ensure that the group for the consumer exists
    try:
        service.info(
            f"Making sure that the '{stream_parameters.group_name}' group has been added to the"
            f"'{stream_parameters.stream_name}' stream"
        )
        connection.xgroup_create(
            name=stream_parameters.stream_name,
            groupname=stream_parameters.group_name,
            id=initial_id,
            mkstream=True
        )
    except Exception as group_exception:
        if 'consumer group name already exists' not in str(group_exception).lower():
            raise Exception(
                f"Could not create the '{stream_parameters.group_name}' group for the "
                f"'{stream_parameters.stream_name}' stream"
            ) from group_exception

    # Make sure that there is a backup consumer for the group. If the consumer being created needs to be removed
    # before it acknowledges its work all the messages that spawned its work should shift to the backup so that it
    # may be picked up later
    try:
        service.info(
            "Creating a backup consumer that will hold messages from consumers that could not acknowledge their work"
        )
        connection.xgroup_createconsumer(
            name=stream_parameters.stream_name,
            groupname=stream_parameters.group_name,
            consumername=BACKUP_CONSUMER_NAME,
        )
    except Exception as backup_creation_exception:
        raise Exception(
            f"The backup consumer for the '{stream_parameters.group_name}' group on the "
            f"'{stream_parameters.stream_name}' stream could not be created"
        ) from backup_creation_exception

    service.info(
        f"The '{stream_parameters.group_name}' group is active on the '{stream_parameters.stream_name}' stream"
    )

    # Finally, attempt to create the new consumer
    try:
        service.info(
            f"Creating the '{consumer_name}' consumer for the '{stream_parameters.stream_name}' stream "
            f"in the '{stream_parameters.group_name}' group"
        )

        connection.xgroup_createconsumer(
            name=stream_parameters.stream_name,
            groupname=stream_parameters.group_name,
            consumername=consumer_name
        )
    except Exception as consumer_creation_exception:
        raise Exception(
            f"Could not create the '{consumer_name}' consumer for the '{stream_parameters.stream_name}' stream in the "
            f"+'{stream_parameters.group_name}' group"
        ) from consumer_creation_exception

    service.info(
        f"The '{consumer_name}' consumer has been created on the '{stream_parameters.stream_name}' stream in the "
        f"'{stream_parameters.group_name}' group"
    )


def backup_messages(stream_parameters: StreamParameters):
    """
    Move idle messages to a backup consumer

    Args:
        stream_parameters: Instructions for how to connect to a stream group
    """
    connection = stream_parameters.get_connection()

    # Make into a partial function to make future calls more readable
    #   Note: `min_idle_time` is a really confusing variable here. Anything under `min_idle_time` is ignored,
    #   so instead of dictating "This is the longest something is allowed to say", you're saying
    #   "Ignore everything below this". Keep in mind here that the IDLE_TIMEOUT will instruct `xautoclaim` to claim
    #   all messages whose timeout is longer than that.
    claim_function: typing.Callable[[], typing.List[bytes]] = partial(
        connection.xautoclaim,
        name=stream_parameters.stream_name,
        groupname=stream_parameters.group_name,
        consumername=BACKUP_CONSUMER_NAME,
        min_idle_time=IDLE_TIMEOUT,
        justid=True
    )
    """Helper function used to claim up to 100 messages for the backup consumer and return the message IDs"""

    claimed_messages = claim_function()
    """All messages that have just been claimed by the backup consumer through xautoclaim"""

    # xautoclaim can only claim 100 messages at a time. While extremely unlikely that a consumer may have over 100
    # messages pending, loop through to ensure everything is copied over
    while claimed_messages:
        claimed_messages = claim_function()


def release_messages(stream_parameters: StreamParameters, consumer_name: str):
    """
    Move messages from a consumer to the backup consumer

    Args:
        stream_parameters: Instructions on how to access a stream
        consumer_name: The name of the consumer for a stream
    """
    backup_messages(stream_parameters)

    connection = stream_parameters.get_connection()

    message_retriever: typing.Callable[[], typing.List[typing.Dict[str, bytes]]] = partial(
        connection.xpending_range,
        name=stream_parameters.stream_name,
        groupname=stream_parameters.group_name,
        consumername=consumer_name,
        min="-",
        max="+",
        count=100,
    )

    messages_to_claim = [
        message['message_id'].decode()
        for message in message_retriever()
    ]

    # Loop through the list of messages to claim to ensure that things are moved over as needed
    while messages_to_claim:
        connection.xclaim(
            name=stream_parameters.stream_name,
            groupname=stream_parameters.group_name,
            consumername=BACKUP_CONSUMER_NAME,
            min_idle_time=0,
            message_ids=messages_to_claim
        )

        messages_to_claim = [
            message['message_id'].decode()
            for message in message_retriever()
        ]