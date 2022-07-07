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
    if not event:
        event = ""

    if not response_type:
        response_type = "send_message"

    return {
        "event": event,
        "type": response_type,
        "data": data
    }


def make_message_serializable(message):
    if isinstance(message, dict):
        for key, value in message.items():
            message[key] = make_message_serializable(value)
    elif isinstance(message, bytes):
        return message.decode()
    elif isinstance(message, datetime):
        return message.strftime("%Y-%m-%dT%H:%M:%S%z")

    return message


class TestConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        print("Creating consumer...")
        super().__init__(*args, **kwargs)
        self.redis_connection: redis.Redis = utilities.get_redis_connection()
        self.publisher_and_subscriber: typing.Optional[redis_client.PubSub] = None
        self.listener = None
        self.connection_group_id = None
        self.event_handlers = {
            "add": test_functions.async_add,
            "subtract": test_functions.async_subtract,
            "multiply": test_functions.async_multiply,
            "echo": test_functions.async_echo,
            "concat": test_functions.async_concat
        }

    def receive_subscribed_message(self, message):
        print("[TestConsumer.receive_subscribed_message] Entered function")
        pprint(message)
        print("[TestConsumer.receive_subscribed_message] Deserializing the message")
        if isinstance(message, (str, bytes)):
            deserialized_message = json.loads(message)
        else:
            deserialized_message = message

        # This needs to crawl through a dict and make sure that none of its children are bytes

        deserialized_message = make_message_serializable(deserialized_message)

        print("[TestConsumer.receive_subscribed_message] Calling send_message")
        response = make_websocket_response(event="subscribed_message_received", data=deserialized_message)
        async_to_sync(self.send_message)(response)
        print("[TestConsumer.receive_subscribed_message] send_message called")

    async def connect(self):
        print("[TestConsumer.connect] Entered function")
        kwargs = self.scope['url_route']['kwargs']
        pprint(kwargs)

        self.connection_group_id = kwargs.get('evaluation_id', "test_group_id")

        print("[TestConsumer.connect] creating the pubsub object")
        self.publisher_and_subscriber = self.redis_connection.pubsub()

        print(f"[TestConsumer.connect] Subscribing to the {self.connection_group_id} channel")
        self.publisher_and_subscriber.subscribe(
            **{
                self.connection_group_id: self.receive_subscribed_message
            }
        )

        print("[TestConsumer.connect] Handling the subscribed channel in its own thread")
        self.listener = self.publisher_and_subscriber.run_in_thread(sleep_time=0.001)

        print(f"[TestConsumer.connect] Adding {self.connection_group_id} to the channel layer")
        await self.channel_layer.group_add(
            self.connection_group_id,
            self.channel_name
        )

        print(f"[TestConsumer.connect] {self.connection_group_id} was added to the channel layer")

        await self.accept()

        connection_message = f"[TestConsumer.connect] Connection accepted"
        await self.tell_channel(event="Connect", data=connection_message, log_data=True)

        group_message = f"[TestConsumer.connect] Connection Group is: {self.connection_group_id}"
        await self.tell_channel(event="Connect", data=group_message, log_data=True)

    async def receive_json(self, data, **kwargs):
        """Receive messages over socket."""
        print(f"[TestConsumer.receive_json] Captured JSON")
        resp = data
        # I'm able to echo back the received message after some processing.
        await self.send(json.dumps(resp, default=str))
        print("[TestConsumer.receive_json] Message sent")

    async def receive(self, text_data=None, **kwargs):
        response = json.loads(text_data)
        entered_message = "[TestConsumer.receive] entered function"
        pprint(response)
        print()
        event = response.get("event", None)
        await self.tell_channel(event=event, data=entered_message, log_data=True)

        result = dict()
        try:
            if event in self.event_handlers:
                args = list()
                kwargs = dict()
                if isinstance(response['data'], typing.Sequence) and not isinstance(response['data'], str):
                    args = response['data']
                elif isinstance(response['data'], dict):
                    if 'args' in response['data']:
                        args.extend(response['data']['args'])
                    if 'kwargs' in response['data']:
                        kwargs = response['kwargs']
                    kwargs.update({
                        key: value
                        for key, value in response['data'].items()
                        if key not in ('args', 'kwargs')
                    })
                else:
                    args.append(response['data'])

                handler = self.event_handlers[event]

                arg_descriptions = ", ".join(args) if args else "_"
                kwarg_descriptions = ", " + ", ".join([f"{key}={value}" for key, value in kwargs.items()]) if kwargs else ""
                calling_message = f"[TestConsumer.receive] Calling {handler.__name__}({self.connection_group_id}, {arg_descriptions}{kwarg_descriptions})"
                await self.tell_channel(event=event, data=calling_message, log_data=True)

                response = await handler(self.connection_group_id, *args, **kwargs)
                result.update(json.loads(response))
            else:
                unregistered_message = f"[TestConsumer.receive] {event} is not a registered event"
                await self.tell_channel(event=event, data=unregistered_message, log_data=True)
                result = dict()
        except Exception as e:
            trace = traceback.format_exc()
            print(f"[TestConsumer.receive] {str(e)}")
            print(f"[TestConsumer.receive] {trace}")
            result.update({
                "error": str(e),
                "traceback": trace
            })
            event = "error"

        print("[TestConsumer.receive] Sending:")
        pprint(result)
        print()

        print("[TestConsumer.receive] Sending result through channel_layer.group_send")
        await self.tell_channel(event=event, data=result)
        print("[TestConsumer.receive] called channel_layer.group_send")

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
        print("[TestConsumer.forward_group_message] Captured forwarded message and calling send")
        await self.send(
            text_data=json.dumps(event) if not isinstance(event, (str,bytes)) else event
        )
        print("[TestConsumer.forward_group_message] Called send")

    async def send_message(self, result):
        print("[TestConsumer.send_message] Entered send_message")

        if isinstance(result, bytes):
            result = result.decode()

        await self.send(
            text_data=json.dumps(result) if not isinstance(result, (str, bytes)) else result
        )
        print("[TestConsumer.send_message] Called send")


    def send_in_sync(self, result):
        print("[TestConsumer.send_in_sync] Sending data asynchronously")
        sync_call = async_to_sync(self.channel_layer.group_send)
        sync_call(self.connection_group_id, result)
        print("[TestConsumer.send_in_sync] Data sent asynchronously")


    async def disconnect(self, close_code):
        disconnecting_message = f"[TestConsumer.disconnect] Disconnecting {self.connection_group_id}..."
        print(disconnecting_message)

        try:
            print("[TestConsumer.disconnect] Closing the listener")
            if self.listener and self.listener.is_alive():
                self.listener.stop()
            print("[TestConsumer.disconnect] listener closed")
        except Exception as e:
            print("[TestConsumer.disconnect] Listener thread could not be killed")
            print(f"[TestConsumer.disconnect] {str(e)}")

        try:
            print("[TestConsumer.disconnect] Unsubscribing to the redis channel")
            if self.publisher_and_subscriber:
                self.publisher_and_subscriber.unsubscribe()
            print("[TestConsumer.disconnect] Redis Channel disconnected")
        except Exception as e:
            print("[TestConsumer.disconnect] Could not unsubscribe from redis channel")
            print(f"[TestConsumer.disconnect] {str(e)}")

        try:
            print("[TestConsumer.disconnect] Closing redis connection")
            if self.redis_connection:
                self.redis_connection.close()
            print("[TestConsumer.disconnect] Redis connection closed")
        except Exception as e:
            print("[TestConsumer.disconnect] Could not disconnect from redis")
            print(f"[TestConsumer.disconnect] {str(e)}")

        print(f"[TestConsumer.disconnect] Discarding {self.connection_group_id} from the channel layer")
        await self.channel_layer.group_discard(
            self.connection_group_id,
            self.channel_name
        )
        print(f"[TestConsumer.disconnect] {self.connection_group_id} has been discarded from the channel layer")
