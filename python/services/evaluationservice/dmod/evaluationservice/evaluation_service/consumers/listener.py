#!/usr/bin/env python3
import inspect
import os
import typing
import json
from asgiref.sync import async_to_sync

import redis
import redis.client as redis_client

from channels.generic.websocket import AsyncJsonWebsocketConsumer

import utilities

from service.application_values import COMMON_DATETIME_FORMAT
from service import logging as common_logging


LOGGER = common_logging.get_logger()
SOCKET_LOGGER = common_logging.get_logger(common_logging.DEFAULT_SOCKET_LOGGER_NAME)


def make_websocket_response(
    event: str = None,
    response_type: str = None,
    data: dict = None,
    logger: common_logging.ConfiguredLogger = None
) -> dict:
    if logger is None:
        logger = LOGGER

    logger.debug(f"Making websocket response for: {str(data)}")

    if data and isinstance(data, bytes):
        data = data.decode()

    data_might_be_json = data and isinstance(data, str)
    data_might_be_json = data_might_be_json and (data[0] == "[" and data[-1] == "]" or data[0] == "{" and data[-1] == "}")

    if data_might_be_json:
        try:
            data = json.loads(data)
        except Exception as load_exception:
            logger.error(
                f"[{inspect.currentframe().f_code.co_name}] The passed data was a non-json string; "
                f"it can't be converted to JSON for further decomposition for a websocket response",
                load_exception
            )

    message_time = utilities.now().strftime(COMMON_DATETIME_FORMAT)

    if isinstance(data, dict):
        use_inner_data = False
        data = utilities.make_message_serializable(data)

        if 'data' in data and 'data' in data['data']:
            if isinstance(data['data'], str):
                try:
                    logger.debug(f"Trying to parse {str(data['data'])} as json data")
                    contained_data = json.loads(data['data'])
                except Exception as loads_exception:
                    logger.error(f"'{str(data)}' didn't parse into a dict so we're using it raw", loads_exception)
                    contained_data = data['data']
            else:
                logger.debug(f"Since '{data}' is not a string, it will just be operated on")
                contained_data = data['data']

            use_inner_data = True
        else:
            contained_data = data

        if 'event' in contained_data and contained_data['event']:
            event = contained_data['event']
        elif 'event' in data and data['event']:
            event = data['event']

        if 'type' in contained_data and contained_data['type']:
            response_type = contained_data['type']
        elif 'type' in data and data['type']:
            response_type = data['type']

        if 'response_type' in contained_data and contained_data['response_type']:
            response_type = contained_data['response_type']
        elif 'response_type' in data and data['response_type']:
            response_type = data['response_type']

        if 'time' in contained_data and contained_data['time']:
            message_time = contained_data['time']
        elif 'time' in data and data['time']:
            message_time = data['time']

        data = contained_data['data'] if use_inner_data else contained_data

        might_be_json = isinstance(data, str)
        might_be_json &= data.startswith("{") and data.endswith("}") or data.startswith("[") and data.endswith("]")

        # Try to convert data to json one last time
        if might_be_json:
            try:
                data = json.loads(data)
            except Exception as loads_exception:
                logger.warn(f"Could not deserialize data:{os.linesep}{str(loads_exception)}")

    if event is None:
        event = ""

    if not response_type:
        response_type = "send_message"

    message = {
        "event": event,
        "type": response_type,
        'time': message_time,
        "data": data
    }

    message = utilities.make_message_serializable(message)
    logger.debug(f"Sending {str(message)}")
    return message


class ChannelConsumer(AsyncJsonWebsocketConsumer):
    """
    Web Socket consumer that forwards messages to and from redis PubSub
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_connection: redis.Redis = utilities.get_redis_connection()
        self.publisher_and_subscriber: typing.Optional[redis_client.PubSub] = None
        self.listener = None
        self.connection_group_id = None
        self.channel_name = None

    def receive_subscribed_message(self, message):
        if isinstance(message, (str, bytes)):
            deserialized_message = json.loads(message)
        else:
            deserialized_message = message

        # This needs to crawl through a dict and make sure that none of its children are bytes
        deserialized_message = utilities.make_message_serializable(deserialized_message)

        response = make_websocket_response(
            event="subscribed_message_received",
            data=deserialized_message,
            logger=SOCKET_LOGGER
        )

        # The caller requires this function to be synchronous, whereas `send_message` is async;
        # we're stuck using async_to_sync here as a result
        async_to_sync(self.send_message)(response)

    async def connect(self):
        kwargs = self.scope['url_route']['kwargs']

        self.channel_name = kwargs.get("channel_name")
        self.connection_group_id = utilities.get_channel_key(self.channel_name)

        if not self.connection_group_id:
            raise ValueError("No channel name was passed; no channel may be subscribed to")

        self.publisher_and_subscriber = self.redis_connection.pubsub()

        SOCKET_LOGGER.debug(f"[{str(self)}] Subscribing to the {self.connection_group_id} channel")
        self.publisher_and_subscriber.subscribe(
            **{
                self.connection_group_id: self.receive_subscribed_message
            }
        )

        self.listener = self.publisher_and_subscriber.run_in_thread(sleep_time=0.001)

        await self.channel_layer.group_add(
            self.connection_group_id,
            self.channel_name
        )

        SOCKET_LOGGER.debug(f"[{str(self)}] {self.connection_group_id} was added to the channel layer")

        await self.accept()

        connection_message = f"[{str(self)}] Connection accepted. Connection Group is: {self.connection_group_id}"
        await self.tell_channel(event="Connect", data=connection_message, log_data=True)

    async def receive_json(self, data, **kwargs):
        """Receive JSON messages over socket."""
        SOCKET_LOGGER.debug(f"[{str(self)}] JSON was received.")
        resp = data

        await self.send(json.dumps(resp, default=str))
        SOCKET_LOGGER.debug(f"[{str(self)}] JSON Message forwarded")

    async def receive(self, text_data=None, **kwargs):
        message = f"[{str(self)}] This connection only forwards messages from a redis channel"
        await self.tell_channel(
            event="error",
            data=message
        )

        # We don't necessarily want to stop processing if the receive function is encountered since that's
        # more of a client issue, not a listener issue.
        exception = NotImplementedError(message)
        SOCKET_LOGGER.error(exception)
        SOCKET_LOGGER.debug(
            f"[{str(str)}] Error encountered; the listener does not accept general websocket messages. "
            f"Data received: {str(text_data)}"
        )
        try:
            scope_string = f"Scope:{os.linesep}{json.dumps(self.scope, indent=4)}"
        except:
            scope_string = f"Scope: {str(self.scope)}"
        SOCKET_LOGGER.debug(f"[{str(self)}] {scope_string}")

    async def tell_channel(self, event: str = None, data=None, log_data: bool = False):
        """
        Send data to the redis channel

        Args:
            event: The event that necessitated the communication
            data: The data to send to the redis channel
            log_data: Whether data received should be logged for later reference
        """
        if log_data:
            SOCKET_LOGGER.debug(
                data or f"[{str(self)}] No Data was given to publish to {self.connection_group_id}"
            )

        message = make_websocket_response(event=event, data=data)
        await self.channel_layer.group_send(
            self.connection_group_id,
            message
        )

    # catches group messages from channel layer and forwards downstream to client
    async def forward_group_message(self, event):
        SOCKET_LOGGER.debug(
            f"[{str(self)}] Captured forwarded message and sending to {self.connection_group_id}"
        )
        await self.send(
            text_data=json.dumps(event) if not isinstance(event, (str,bytes)) else event
        )
        SOCKET_LOGGER.debug(f"[{str(self)}] Sent data to {self.connection_group_id}")

    async def send_message(self, result):
        if isinstance(result, bytes):
            result = result.decode()

        await self.send(
            text_data=json.dumps(result) if not isinstance(result, (str, bytes)) else result
        )
        SOCKET_LOGGER.debug(f"[{str(self)}] Data sent through the web socket")

    async def disconnect(self, close_code):
        disconnecting_message = f"[{str(self)}]  Disconnecting from {self.connection_group_id}..."
        SOCKET_LOGGER.debug(disconnecting_message)

        try:
            SOCKET_LOGGER.debug(f"[{str(self)}]  Closing the listener")
            if self.listener and self.listener.is_alive():
                self.listener.stop()
            SOCKET_LOGGER.debug(f"[{str(self)}]  listener closed")
        except Exception as disconnection_error:
            message = f"[{str(self)}]  Listener thread could not be killed"
            SOCKET_LOGGER.error(
                message,
                disconnection_error
            )
            LOGGER.error(message, disconnection_error)

        try:
            SOCKET_LOGGER.debug(f"[{str(self)}] Unsubscribing to the redis channel")
            if self.publisher_and_subscriber:
                self.publisher_and_subscriber.unsubscribe()
            SOCKET_LOGGER.debug(f"[{str(self)}] Redis Channel disconnected")
        except Exception as e:
            print(f"[{str(self)}] Could not unsubscribe from redis channel")
            print(f"[{str(self)}] {str(e)}")

        try:
            print(f"[{str(self)}] Closing redis connection")
            if self.redis_connection:
                self.redis_connection.close()
            print(f"[{str(self)}] Redis connection closed")
        except Exception as e:
            print(f"[{str(self)}] Could not disconnect from redis")
            print(f"[{str(self)}] {str(e)}")

        print(f"[{str(self)}] Discarding {self.connection_group_id} from the channel layer")
        await self.channel_layer.group_discard(
            self.connection_group_id,
            self.channel_name
        )
        print(f"[{str(self)}] {self.connection_group_id} has been discarded from the channel layer")

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.channel_name} <=> {':'.join([str(entry) for entry in self.scope['client']])}"

    def __repr__(self):
        redis_connection_details = f"{self.redis_connection.connection.username}" \
                                   f"@{self.redis_connection.connection.host}" \
                                   f":{str(self.redis_connection.connection.port)}"
        return json.dumps({
            "class": self.__class__.__name__,
            "channel_name": self.channel_name,
            "connection_group_id": self.connection_group_id,
            "redis_connection": redis_connection_details,
            "host": ":".join([str(entry) for entry in self.scope['host']])
        }, indent=4)
