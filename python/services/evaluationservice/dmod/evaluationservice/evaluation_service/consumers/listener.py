#!/usr/bin/env python3
import typing
import json
import os
import traceback
from asgiref.sync import async_to_sync

from pprint import pprint
from datetime import datetime

import channels
import redis
import redis.client as redis_client

from channels.generic.websocket import AsyncJsonWebsocketConsumer
import channels.layers

import utilities

import test_functions


def make_websocket_response(event: str = None, response_type: str = None, data: dict = None) -> dict:
    print(f"Making websocket response for: {str(data)}")

    if data and isinstance(data, bytes):
        data = data.decode()

    if data and isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            print("The data was a non-json string")

    message_time = utilities.now().strftime(utilities.datetime_format())

    if isinstance(data, dict):
        use_inner_data = False
        data = utilities.make_message_serializable(data)

        if 'data' in data and 'data' in data['data']:
            if isinstance(data['data'], str):
                try:
                    print(f"Trying to parse {str(data['data'])} as json data")
                    contained_data = json.loads(data['data'])
                except:
                    print(f"'{str(data)}' didn't parse into a dict so we're using it raw")
                    contained_data = data['data']
            else:
                print(f"Since '{data}' is not a string, it will just be operated on")
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

        # Try to convert data to json one last time
        if isinstance(data, str) and (data.startswith("{") or data.startswith("[")):
            try:
                data = json.loads(data)
            except:
                pass

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
    print(f"Sending {str(message)}")
    return message


class ChannelConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis_connection: redis.Redis = utilities.get_redis_connection()
        self.publisher_and_subscriber: typing.Optional[redis_client.PubSub] = None
        self.listener = None
        self.connection_group_id = None

    def receive_subscribed_message(self, message):
        print("[ChannelConsumer.receive_subscribed_message] Entered function")
        pprint(message)
        print("[ChannelConsumer.receive_subscribed_message] Deserializing the message")
        if isinstance(message, (str, bytes)):
            deserialized_message = json.loads(message)
        else:
            deserialized_message = message

        # This needs to crawl through a dict and make sure that none of its children are bytes

        deserialized_message = utilities.make_message_serializable(deserialized_message)

        print(f"Readying '{str(deserialized_message)}' for forwarding")

        print("[ChannelConsumer.receive_subscribed_message] Calling send_message")
        response = make_websocket_response(event="subscribed_message_received", data=deserialized_message)
        async_to_sync(self.send_message)(response)
        print("[ChannelConsumer.receive_subscribed_message] send_message called")

    async def connect(self):
        print("[ChannelConsumer.connect] Entered function")
        kwargs = self.scope['url_route']['kwargs']
        pprint(kwargs)

        self.connection_group_id = utilities.get_channel_key(kwargs.get('channel_name'))

        if not self.connection_group_id:
            raise ValueError("No channel name was passed; no channel may be subscribed to")

        print("[ChannelConsumer.connect] creating the pubsub object")
        self.publisher_and_subscriber = self.redis_connection.pubsub()

        print(f"[ChannelConsumer.connect] Subscribing to the {self.connection_group_id} channel")
        self.publisher_and_subscriber.subscribe(
            **{
                self.connection_group_id: self.receive_subscribed_message
            }
        )

        print("[ChannelConsumer.connect] Handling the subscribed channel in its own thread")
        self.listener = self.publisher_and_subscriber.run_in_thread(sleep_time=0.001)

        print(f"[ChannelConsumer.connect] Adding {self.connection_group_id} to the channel layer")
        await self.channel_layer.group_add(
            self.connection_group_id,
            self.channel_name
        )

        print(f"[ChannelConsumer.connect] {self.connection_group_id} was added to the channel layer")

        await self.accept()

        connection_message = f"[ChannelConsumer.connect] Connection accepted"
        await self.tell_channel(event="Connect", data=connection_message, log_data=True)

        group_message = f"[ChannelConsumer.connect] Connection Group is: {self.connection_group_id}"
        await self.tell_channel(event="Connect", data=group_message, log_data=True)

    async def receive_json(self, data, **kwargs):
        """Receive messages over socket."""
        print(f"[ChannelConsumer.receive_json] Captured JSON")
        resp = data
        # I'm able to echo back the received message after some processing.
        await self.send(json.dumps(resp, default=str))
        print("[ChannelConsumer.receive_json] Message sent")

    async def receive(self, text_data=None, **kwargs):
        if text_data:
            response = json.loads(text_data)
            print("[ChannelConsumer.receive] JSON data was received for some reason")
            print(json.dumps(response, indent=4))

        await self.tell_channel(event="error", data="This connection only forwards messages from a redis channel")

    async def tell_channel(self, event: str = None, data=None, log_data: bool = False):
        if log_data:
            pprint(data)
        message = make_websocket_response(event=event, data=data)
        await self.channel_layer.group_send(
            self.connection_group_id,
            message
        )

    # catches group messages from channel layer and forwards downstream to client
    async def forward_group_message(self, event):
        print("[ChannelConsumer.forward_group_message] Captured forwarded message and calling send")
        await self.send(
            text_data=json.dumps(event) if not isinstance(event, (str,bytes)) else event
        )
        print("[ChannelConsumer.forward_group_message] Called send")

    async def send_message(self, result):
        print("[ChannelConsumer.send_message] Entered send_message")

        if isinstance(result, bytes):
            result = result.decode()

        await self.send(
            text_data=json.dumps(result) if not isinstance(result, (str, bytes)) else result
        )
        print("[ChannelConsumer.send_message] Called send")


    def send_in_sync(self, result):
        print("[ChannelConsumer.send_in_sync] Sending data asynchronously")
        sync_call = async_to_sync(self.channel_layer.group_send)
        sync_call(self.connection_group_id, result)
        print("[ChannelConsumer.send_in_sync] Data sent asynchronously")


    async def disconnect(self, close_code):
        disconnecting_message = f"[ChannelConsumer.disconnect] Disconnecting {self.connection_group_id}..."
        print(disconnecting_message)

        try:
            print("[ChannelConsumer.disconnect] Closing the listener")
            if self.listener and self.listener.is_alive():
                self.listener.stop()
            print("[ChannelConsumer.disconnect] listener closed")
        except Exception as e:
            print("[ChannelConsumer.disconnect] Listener thread could not be killed")
            print(f"[ChannelConsumer.disconnect] {str(e)}")

        try:
            print("[ChannelConsumer.disconnect] Unsubscribing to the redis channel")
            if self.publisher_and_subscriber:
                self.publisher_and_subscriber.unsubscribe()
            print("[ChannelConsumer.disconnect] Redis Channel disconnected")
        except Exception as e:
            print("[ChannelConsumer.disconnect] Could not unsubscribe from redis channel")
            print(f"[ChannelConsumer.disconnect] {str(e)}")

        try:
            print("[ChannelConsumer.disconnect] Closing redis connection")
            if self.redis_connection:
                self.redis_connection.close()
            print("[ChannelConsumer.disconnect] Redis connection closed")
        except Exception as e:
            print("[ChannelConsumer.disconnect] Could not disconnect from redis")
            print(f"[ChannelConsumer.disconnect] {str(e)}")

        print(f"[ChannelConsumer.disconnect] Discarding {self.connection_group_id} from the channel layer")
        await self.channel_layer.group_discard(
            self.connection_group_id,
            self.channel_name
        )
        print(f"[ChannelConsumer.disconnect] {self.connection_group_id} has been discarded from the channel layer")
