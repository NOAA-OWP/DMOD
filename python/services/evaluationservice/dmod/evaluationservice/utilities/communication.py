"""
Defines a custom communicator for sending evaluation updates through redis
"""
import typing
import os
import json
import traceback

from time import sleep
from datetime import timedelta

import redis

from dmod.metrics import communication
from dmod.core.common import to_json
from dmod.core.context import DMODObjectManager

from service import application_values

from . import common
from .message import make_message_serializable


MessageHandlers = typing.Union[communication.MessageHandler, typing.Sequence[communication.MessageHandler]]


def make_key(*args) -> str:
    """
    Forms a key based on all passed in items

    Given `key_separator()` => '--', `make_key('one', 'two-five', 'three--four')` becomes 'one--two-five--three--four'

    Args:
        *args: Elements with that make up unique sections of a key

    Returns:

    """
    parts = []

    for arg in args:
        if arg:
            parts.extend(
                [
                    str(part).strip()
                    for part in str(arg).strip().strip(common.key_separator()).split(common.key_separator())
                    if part and str(part).strip()
                ]
            )

    return common.key_separator().join(parts)


def redis_prefix() -> str:
    """
    Returns:
        The prefix to use when interacting with REDIS
    """
    return os.environ.get("EVALUATION_PREFIX", common.application_prefix())


def get_channel_key(evaluation_id: str) -> str:
    """
    Gets the name of a channel to publish to for an evaluation

    Args:
        evaluation_id: The ID for the evaluation

    Returns:
        The name of the channel to publish to for this evaluation
    """
    evaluation_id = get_evaluation_key(evaluation_id)

    if not evaluation_id.endswith(common.key_separator() + "COMMUNICATION"):
        evaluation_id = make_key(evaluation_id, "COMMUNICATION")

    return evaluation_id


def get_evaluation_key(evaluation_id: str) -> str:
    """
    Quantifies the key in redis for the given evaluation within the context of the application

    This ensures that the key for the core evaluation record is properly prepended by all necessary qualifiers

    Args:
        evaluation_id: The ID of the evaluation to determine the key for

    Returns:
        The expected key for an evaluation
    """
    args = evaluation_id.split(common.key_separator())

    if args[0] != redis_prefix():
        args.insert(0, redis_prefix())

    return make_key(*args)


def default_sunset() -> int:
    """
    Returns:
        The default lifespan of active records if they are told to be removed.
    """
    seconds = os.environ.get("EVALUATION_SUNSET")

    if seconds:
        return int(float(seconds))

    return int(timedelta(minutes=15).total_seconds())


def unchecked_lifespan() -> int:
    """
    Returns:
        The number of seconds that an evaluation's records should remain
    """
    seconds = os.environ.get("UNCHECKED_EVALUATION_LIFESPAN")

    if seconds:
        return int(float(seconds))

    return int(timedelta(hours=18).total_seconds())


def get_redis_connection(
    host: str = None,
    port: int = None,
    username: str = None,
    password: str = None,
    db: int = None
) -> redis.Redis:
    """
    Forms a connection to a redis instance. If fields are not supplied, values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        username: The optional username to connect to
        password: The optional password to use when connecting to the instance
        db: The optional database to connect to

    Returns:
        A connection to a redis instance
    """
    return redis.Redis(
        host=host or application_values.REDIS_HOST,
        port=port or application_values.REDIS_PORT,
        username=username or application_values.REDIS_USERNAME,
        password=password or application_values.REDIS_PASSWORD,
        db=db or application_values.REDIS_DB,
    )


def get_runner_connection(
    host: str = None,
    port: int = None,
    db: str = None,
    password: str = None,
    username: str = None
) -> redis.Redis:
    """
    Forms a connection to a redis instance to the runner. If fields are not supplied,
    values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        username: The optional username to connect to
        password: The optional password to use when connecting to the instance
        db: The optional database to connect to

    Returns:
        A connection to a redis instance
    """
    return redis.Redis(
        host=host or application_values.RUNNER_HOST,
        port=port or application_values.RUNNER_PORT,
        username=username or application_values.RUNNER_USERNAME,
        password=password or application_values.RUNNER_PASSWORD,
        db=db or application_values.RUNNER_DB,
    )


def get_channel_connection(
    host: str = None,
    port: int = None,
    db: str = None,
    password: str = None,
    username: str = None
) -> redis.Redis:
    """
    Forms a connection to a redis instance that serves channel information. If fields are not supplied,
    values fall back to environment configuration

    Args:
        host: The optional host to connect to
        port: The optional port to connect to
        username: The optional username to connect to
        password: The optional password to use when connecting to the instance
        db: The optional database to connect to

    Returns:
        A connection to a redis instance
    """
    return redis.Redis(
        host=host or application_values.CHANNEL_HOST,
        port=port or application_values.CHANNEL_PORT,
        username=username or application_values.CHANNEL_USERNAME,
        password=password or application_values.CHANNEL_PASSWORD,
        db=db or application_values.CHANNEL_DB,
    )


def get_retry_delay() -> int:
    """
    Returns:
        The amount of seconds to wait before retrying a command
    """
    seconds = 1
    return seconds


def get_maximum_retries() -> int:
    """
    Returns:
        The maximum number of times that one or more commands should be sent to redis
    """
    return 5


def get_evaluation_pointers(evaluation_id: str) -> typing.Dict[str, str]:
    """
    Gets the keys for an evaluation's record that point to other Redis objects, such as a list of messages

    Args:
        evaluation_id: The id of the evaluation to build pointers for

    Returns:
        A dictionary mapping the key in the evaluation record to the expected value of said key
    """
    if common.key_separator() in evaluation_id:
        args = evaluation_id.split(common.key_separator())
    else:
        args = [evaluation_id]

    if args[0] != redis_prefix():
        args.insert(0, redis_prefix())

    return {
        "error_key": make_key(*(args + ["ERROR"])),
        "info_key": make_key(*(args + ["INFO"]))
    }


class RedisCommunicator(communication.Communicator):
    """
    A communicator where all state and message information passes through a redis instance
    """
    def update(self, **kwargs):
        """
        Updates state information for the communicator

        Args:
            **kwargs: Fairly arbitrary state values to update for the communicator
        """
        if len(kwargs) == 0:
            message = f"The data for {self.communicator_id} could not be updated - no values to update were passed"
            self.error(message)
            return

        try_count = 0
        data_updated = False
        latest_error = None

        while not data_updated and try_count < get_maximum_retries():
            pipeline = self.__connection.pipeline()
            try:
                kwargs['last_updated'] = common.now().strftime(application_values.COMMON_DATETIME_FORMAT)
                for key, value in kwargs.items():
                    if isinstance(value, bool):
                        safe_value = int(value)
                    elif not isinstance(value, (str, int, bytes, float)):
                        safe_value = str(value)
                    else:
                        safe_value = value
                    pipeline.hset(self.__core_key, key, safe_value)

                pipeline.execute()
                data_updated = True
                self.write(reason="update", data=kwargs)
                break
            except Exception as e:
                latest_error = e
                try_count += 1
                sleep(get_retry_delay())
            finally:
                if pipeline:
                    pipeline.reset()

        if not data_updated:
            message = f"Data for the {self.communicator_id} communicator could not be updated"
            exception = latest_error or Exception(message)
            self.error(message, exception, publish=True)
            raise exception

        # Reset the possible sunset for communicator state
        self.sunset(unchecked_lifespan())

    def sunset(self, seconds: float = None):
        """
        Sets all resources in the redis instance for this communicators' state for expiration.

        Args:
            seconds: The number of seconds left for this communicator's state to live
        """
        retry_count = 0
        latest_error = None
        remaining_lifespan = int(seconds or default_sunset())
        while not self.__has_sunset and retry_count < get_maximum_retries():
            pipeline = self.__connection.pipeline()
            try:
                pipeline.expire(self.__core_key, remaining_lifespan)
                pipeline.expire(self.__error_key, remaining_lifespan)
                pipeline.expire(self.__info_key, remaining_lifespan)
                pipeline.execute()
                self.__has_sunset = True
                self.info(f"Resources associated with {self.__core_key} have been sunset for {remaining_lifespan}")
            except Exception as e:
                latest_error = e
                retry_count += 1
                sleep(get_retry_delay())
            finally:
                if pipeline:
                    pipeline.reset()

        if not self.__has_sunset:
            message = f"Data for the {self.__channel_name} communicator could not be sunset."
            exception = latest_error or Exception(message)
            self.error(message, exception)
            raise exception

    def error(
        self,
        message: str,
        exception: Exception = None,
        verbosity: communication.Verbosity = None,
        publish: bool = None
    ):
        """
        Publishes an error to the communicator's set of error messages

        Args:
            message: The error message
            exception: An exception that caused the error
            verbosity: The significance of the message. If given, the message will only be recorded if the
                        vebosity matches or exceeds the communicator's verbosity
            publish: Whether to write the message to the channel
        """
        if exception:
            formatted_exception = os.linesep.join(
                traceback.format_exception(
                    type(exception),
                    exception,
                    exception.__traceback__
                )
            )
            message += f"{os.linesep}{formatted_exception}"

        if verbosity and self._verbosity < verbosity:
            return

        if self.__include_timestamp:
            timestamp = common.now()
            message = f"[{timestamp}] {message}"

        self.__connection.rpush(self.__error_key, message)

        if publish:
            self.write(reason="error", data={"error": message})

        # Call every event handler for the 'error' event
        for handler in self._handlers.get("error", []):
            handler(message)

    def info(self, message: str, verbosity: communication.Verbosity = None, publish: bool = None):
        """
        Publishes a message to the communicator's set of basic information.

        Data will look like the following when published to the channel:

            {
                "event": "info",

                "time": YYYY-mm-dd HH:MM z,

                "data": {
                    "info": message
                }
            }

        Args:
            message: The message to record
            verbosity: The significance of the message. If given, the message will only be recorded if the
                        vebosity matches or exceeds the communicator's verbosity
            publish: Whether the message should be published to the channel
        """
        if verbosity and self._verbosity < verbosity:
            return

        if self.__include_timestamp:
            timestamp = common.now()
            message = f"[{timestamp}] {message}"

        self.__connection.rpush(self.__info_key, message)

        if publish:
            self.write(reason="info", data={"info": message})

        # Call every event handler for the 'info' event
        for handler in self._handlers.get("info", []):
            handler(message)

    def read_errors(self) -> typing.Iterable[str]:
        """
        Returns:
            All recorded error messages for this evaluation so far
        """
        return self.__connection.lrange(self.__error_key, 0, -1)

    def read_info(self) -> typing.Iterable[str]:
        """
        Returns:
            All basic notifications for this evaluation so far
        """
        return self.__connection.lrange(self.__info_key, 0, -1)

    def _validate(self) -> typing.Sequence[str]:
        """
        Returns:
            A list of issues with this communicator as constructed
        """
        messages = []

        return messages

    def write(self, reason: communication.ReasonToWrite, data: dict):
        """
        Writes data to the communicator's channel

        Takes the form of:

        {
            "event": reason,
            "time": YYYY-mm-dd HH:MMz,
            "data": json string
        }

        Args:
            reason: The reason for data being written to the channel
            data: The data to write to the channel; will be converted to a string
        """
        # First convert all submitted values into a form that can safely be converted to a string
        data = make_message_serializable(data)

        message = {
            "event": reason,
            "time": common.now().strftime(application_values.COMMON_DATETIME_FORMAT),
            "data": to_json(data, indent=4)
        }

        # Publish and indent by 4 for later readability
        self.__connection.publish(self.__channel_name, to_json(message, indent=4))

        try:
            for handler in self._handlers.get('write', []):
                handler(message)
        except:
            # Leave room for a breakpoint
            raise

    def read(self) -> typing.Any:
        """
        Wait the communicator's set timeout for message to the channel

        Returns:
            A deserialized message if one was received, Nothing otherwise
        """
        message = self.__publisher_and_subscriber.get_message(ignore_subscribe_messages=True, timeout=self.__timeout)
        if message:
            if message.get('type') == 'message' and message.get('data'):
                return json.loads(message.get('data', b"{}"))
        return None

    def _process_received_message(self, message: communication.MESSAGE, *args, **kwargs):
        """
        Call all handlers for when a message is received via the channel

        Args:
            message: The received message
            *args:
            **kwargs:
        """
        for handler in self._handlers.get('receive', []):
            handler(message)

    @property
    def channel(self) -> str:
        """
        Returns:
            The name of the channel to publish and listen to
        """
        return self.__channel_name

    def __init__(
        self,
        communicator_id: str,
        verbosity: communication.Verbosity = None,
        host: str = None,
        port: int = None,
        password: str = None,
        timeout: float = None,
        on_receive: MessageHandlers = None,
        handlers: typing.Dict[str, MessageHandlers] = None,
        include_timestamp: bool = None,
        timestamp_format: str = None,
        **kwargs
    ):
        super().__init__(
            communicator_id=communicator_id,
            verbosity=verbosity,
            on_receive=on_receive,
            handlers=handlers, **kwargs
        )
        self.__core_key = make_key(redis_prefix(), communicator_id)
        self.__channel_name = get_channel_key(communicator_id)
        self.__info_key = get_evaluation_pointers(communicator_id)['info_key']
        self.__error_key = get_evaluation_pointers(communicator_id)['error_key']
        self.__host = host
        self.__port = port
        self.__password = password
        self.__connection = get_redis_connection(host=host, port=port, password=password, **kwargs)
        self.__publisher_and_subscriber = None
        self.__listener = None
        self.__timeout = timeout or 0
        self.__has_sunset = False
        self.__include_timestamp = include_timestamp if include_timestamp is not None else False
        self.__timestamp_format = timestamp_format or application_values.COMMON_DATETIME_FORMAT

        if 'receive' in self._handlers:
            self.__publisher_and_subscriber = self.__connection.pubsub()
            self.__publisher_and_subscriber.subscribe(**{self.__channel_name: self._process_received_message})
            self.__listener = self.__publisher_and_subscriber.run_in_thread(sleep_time=1)

        pipeline = self.__connection.pipeline()

        try:
            for key, pointer in get_evaluation_pointers(communicator_id).items():
                pipeline.hset(self.__core_key, key, pointer)

            pipeline.hset(self.__core_key, "channel_name", self.__channel_name)
            pipeline.execute()
        finally:
            if pipeline:
                pipeline.reset()

        self.info(
            f"A new communicator has been registered and is ready to communicate through {self.__channel_name}"
        )

    def __del__(self):
        try:
            if self.__publisher_and_subscriber:
                self.__publisher_and_subscriber.close()
        except Exception as e:
            self.error(f"A subscriber for {self.__core_key} could not be closed", e)

        if not self.__has_sunset:
            try:
                self.sunset()
            except Exception as e:
                self.error(f"Data for {self.__core_key} could not be scheduled for deletion", e)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.channel}"


DMODObjectManager.register_class(RedisCommunicator)
