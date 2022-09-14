import abc
import typing

from websockets import WebSocketClientProtocol
from websockets import WebSocketServerProtocol

import dmod.communication as communication

from dmod.core import decorators
from dmod.communication.message import InitRequestResponseReason

from .handler import MessageHandlerMixin


class RepeatMixin(MessageHandlerMixin, abc.ABC):
    """
    Mixin for ConsumerProducers that listen to a server connection and forward the message to 
    """
    @decorators.server_message_handler
    async def repeat(
        self,
        message: typing.Union[str, bytes],
        websocket: WebSocketServerProtocol = None,
        client: WebSocketClientProtocol = None,
        *args,
        **kwargs
    ) -> None:
        """
        Send messages received from the websocket to the evaluation service

        Args:
            message: A message sent through the server
            websocket: The websocket that provided the initial request
            client: The connection to forward the received message through
            path: The path to the socket on the server

        Returns:
            A response detailing the result of sending messages to the evaluation service
        """
        return await client.send(message)
