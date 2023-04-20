"""
Defines websocket consumers used to consume data from a redis channel
"""
import typing
import json
import abc
import inspect
import os

import redis
from asgiref.sync import async_to_sync

import utilities

from maas_experiment import logging as common_logging
from maas_experiment import application_values

from .common import get_group_key
from .socket import SocketConsumer
from .socket import CONSUMER_HANDLER


class ChannelConsumer(SocketConsumer, abc.ABC):

    def get_group(self) -> str:
        name = self.get_channel_name()
        key = get_group_key(name)
        return key

    def get_channel_name(self) -> str:
        name = self.scope_data.get("channel_name", "default-channel")

        if name == "default-channel":
            common_logging.warn(
                f"The default channel name is being used for {str(self)}. A subclass is highly recommended."
            )
        return name

    async def add_to_group(self, *args, **kwargs):
        await self.add_consumer_to_group(self.get_group())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_connect_handler(self.add_to_group)

    async def add_consumer_to_group(self, group_name: str):
        """
        Function used to demystify how group addition to work.

        self.channel_layer.group_add(<group_name>, self.channel_name) should ALWAYS be called like that. The only
        variation should be the group name. This might only ever get called in one place, but the terminology is
        confusing and needs to be simplified

        Args:
            group_name: The name of the group that this instance of this consumer should belong to
        """
        # The group name is the name common to everything that's interested -
        # so we could have 99,000 connections interested in this consumer's information and they'd all have that
        # same group name
        # The channel_name, though, is a unique identifier for this instance. This identifier is kept within the
        # channels in a dict-like structure. As a result, this channel name HAS to be unique and it HAS to match
        # information assigned to this consumer when the connection is accepted. If we have 99,000 consumers
        # interested in this group, we should have 99,000 unique channel names since there will be a unique channel
        # per consumer
        # Failure to meet these requirements will result in there being no consumers being able to 'hear' sent messages
        await self.channel_layer.group_add(group_name, self.channel_name)

    def __str__(self):
        return f"[{self.__class__.__name__}] <=> {self.get_group()}"

    def __repr__(self):
        return json.dumps({
            "class": self.__class__.__name__,
            "group": self.get_group(),
            "host": self.scope_data.server_host,
            "attributes": self._attributes
        }, indent=4)


class Announcer(ChannelConsumer):
    def get_group(self) -> str:
        return get_group_key(application_values.NOTIFICATION_CHANNEL)

    def get_channel_name(self) -> str:
        return application_values.NOTIFICATION_CHANNEL

    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs):
        information_received: typing.Optional[str] = None

        if bytes_data:
            information_received = bytes_data.decode()
        elif text_data:
            information_received = text_data

        if not information_received:
            return

        # 'type' will be the function listeners will call on the 'message' parameter.
        # Only consumers with a function named `payload['type']` registered to this group will be able to
        # act on this message. If this class has an 'announcement' function, its 'announcement' function will be
        # called. Remove it and this class won't act on it. The function is found via `getattr` on matching
        # consumers within the group
        payload = {
            "type": "announcement",
            "message": information_received
        }

        await self.channel_layer.group_send(
            self.get_group(),
            payload
        )

    async def announcement(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))


class Notifier(ChannelConsumer):
    def get_group(self) -> str:
        return get_group_key(application_values.NOTIFICATION_CHANNEL)

    def get_channel_name(self) -> str:
        return application_values.NOTIFICATION_CHANNEL

    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs):
        await self.send(text_data=json.dumps({
            "message": "Don't send messages to the notifier"
        }))

    async def connect(self):
        await super().connect()

    async def announcement(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))




