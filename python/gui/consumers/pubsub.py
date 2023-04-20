"""
Defines websocket consumers used to communicate information through redis pubsub instances
"""
import typing
import json
import inspect
import abc

import redis.client
from asgiref.sync import async_to_sync
from redis.client import PubSub
from redis.client import PubSubWorkerThread

from maas_experiment import application_values
from maas_experiment import logging as common_logging

import utilities

from .common import make_websocket_message
from .common import get_group_key
from .socket import SocketConsumer

INCOMING_MESSAGE_HANDLER = typing.Callable[
    [typing.Union[str, bytes, dict]],
    typing.Optional[typing.Coroutine]
]


class RedisConsumer(SocketConsumer, abc.ABC):
    def __init__(
        self,
        host: str = None,
        db: str = None,
        port: typing.Union[str, int] = None,
        password: str = None,
        username: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._channel_name = None

        host = host or application_values.CHANNEL_HOST
        port = port or application_values.CHANNEL_PORT
        db = db or application_values.CHANNEL_DB
        password = password or application_values.CHANNEL_PASSWORD
        username = username or application_values.CHANNEL_USERNAME

        # Connect to Redis
        self.__redis_connection: redis.Redis = utilities.get_redis_connection(
            host=host,
            port=port,
            db=db,
            password=password,
            username=username
        )

    @property
    def redis_connection(self) -> redis.Redis:
        return self.__redis_connection

    def get_connection_string(self) -> typing.Optional[str]:
        connection_parameters: typing.Dict[str, typing.Any] = dict()

        if self.__redis_connection is not None:
            connection_parameters = self.__redis_connection.get_connection_kwargs()

        redis_connection_details = ""

        if connection_parameters:
            username = connection_parameters.get("username")

            if username:
                redis_connection_details += f"{username}@"

            host = connection_parameters.get("host")

            if host:
                redis_connection_details += host

            port = connection_parameters.get('port')

            if port:
                redis_connection_details += f":{port}"

            redis_connection_details = f"redis://{redis_connection_details}"
        else:
            redis_connection_details = "Unknown Redis Instance"

        return redis_connection_details

    def __str__(self):
        return f"[{self.__class__.__name__}] <=> {self.get_connection_string()}"

    def __repr__(self):
        return json.dumps({
            "class": self.__class__.__name__,
            "connection": self.get_connection_string(),
            "host": self.scope_data.server_host,
            "attributes": self._attributes
        }, indent=4)


class PubSubConsumer(RedisConsumer):
    def process_incoming_message(self, message: typing.Union[str, bytes, dict]):
        for handler in self._incoming_message_handlers:
            try:
                result: typing.Optional[typing.Coroutine, typing.Any] = handler(message)

                while inspect.isawaitable(result):
                    synchronous_result_handler = async_to_sync(result)
                    result = synchronous_result_handler()
            except Exception as processing_exception:
                common_logging.error(f"Failed to process an incoming message", exception=processing_exception)

    def get_group(self) -> str:
        return get_group_key(self.__channel_name)

    def get_incoming_message_handlers(self) -> typing.Iterable[INCOMING_MESSAGE_HANDLER]:
        return self._incoming_message_handlers

    def subscribe(self):
        self.__publisher_and_subscriber = self.__redis_connection.pubsub()

        group_handlers: typing.Dict[str, typing.Callable] = {
            self.get_group(): self.process_incoming_message
        }

        additional_channels = self.scope_data.keyword_arguments.get("additional_channels")

        if additional_channels:
            if isinstance(additional_channels, str):
                group_handlers[additional_channels] = self.process_incoming_message
            elif isinstance(additional_channels, typing.Iterable):
                group_handlers.update({
                    str(channel): self.process_incoming_message
                    for channel in additional_channels
                })
            else:
                common_logging.warn(
                    f"Cannot add additional channels ({str(additional_channels)}) "
                    f"to a newly connected {self.__class__.__name__}"
                )

        self.__publisher_and_subscriber.subscribe(**group_handlers)
        self.__listener = self.__publisher_and_subscriber.run_in_thread(sleep_time=0.001)

    def unsubscribe(self):
        try:
            self.__listener.stop()
        except Exception as e:
            common_logging.error(
                f"Could not formally stop the execution of the listener for {str(self)}",
                exception=e
            )

    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs):
        if bytes_data:
            text_data = bytes_data.decode()

        self.redis_connection.publish(self.get_group(), text_data)

        for channel in self.__additional_channels:
            self.redis_connection.publish(channel, text_data)

    def record_additional_channels(self):
        additional_channels = self.scope_data.keyword_arguments.get("additional_channels")

        if additional_channels:
            if isinstance(additional_channels, str):
                self.__additional_channels.append(additional_channels)
            elif isinstance(additional_channels, typing.Iterable):
                self.__additional_channels.append(additional_channels)
            else:
                common_logging.warn(
                    f"Could not add additional channels ({str(additional_channels)}) "
                    f"to a newly connected {self.__class__.__name__}"
                )

    def __init__(
        self,
        response_type: str = None,
        channel: str = None,
        incoming_message_handlers: typing.Iterable[INCOMING_MESSAGE_HANDLER] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.__response_type = response_type
        self.__channel_name = channel
        self.__listener: typing.Optional[PubSubWorkerThread] = None
        self.__publisher_and_subscriber: typing.Optional[PubSub] = None
        self.set("response_type", response_type)
        self.set("channel_name", channel)
        self._incoming_message_handlers: typing.List[INCOMING_MESSAGE_HANDLER] = incoming_message_handlers or list()
        self.__additional_channels = []

        self.add_connect_handler(self.record_additional_channels)
        self.add_connect_handler(self.subscribe)
        self.add_disconnect_handler(self.unsubscribe)

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.channel_name} <=> " \
               f"{':'.join([str(entry) for entry in self.scope_data.client])}"


class EchoSubscriptionConsumer(PubSubConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._incoming_message_handlers.append(self.unwrap_and_echo)

    def unwrap_and_echo(self, message: typing.Union[str, bytes, dict]):
        """
        Interprets and transforms messages sent along the redis channel.

        Args:
            message: A message that was published from redis
        """

        def is_message_wrapper(possible_wrapper) -> bool:
            return isinstance(possible_wrapper, dict) \
                and not possible_wrapper.get("event") \
                and "data" in possible_wrapper

        # The passed message may be a wrapper if it doesn't bear an event, but DOES have a 'data' member.
        # If that's the case, use its data member instead
        while is_message_wrapper(message):
            message = message['data']

        if isinstance(message, bytes):
            message = message.decode()

        # If it looks like the passed message might be a string or bytes representation of a dict, attempt to
        # convert it to a dict
        if isinstance(message, str) and utilities.string_might_be_json(message):
            try:
                deserialized_message = json.loads(message)
            except:
                # It couldn't be converted, so go ahead use the passed in value
                deserialized_message = message
        else:
            deserialized_message = message

        while is_message_wrapper(deserialized_message):
            # This is only considered a message wrapper if it is a dict; linters may think this could be a string,
            # but it will always be a dict here
            deserialized_message = deserialized_message['data']

        message_to_forward = make_websocket_message(
            data=deserialized_message,
            event="unwrap_and_echo"
        )

        # The caller requires this function to be synchronous, whereas `send_message` is async;
        # we're stuck using async_to_sync here as a result
        self._tell_client(message_to_forward, event="subscribed_message_received")