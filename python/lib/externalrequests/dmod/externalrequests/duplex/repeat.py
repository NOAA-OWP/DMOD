"""
Provides a handler that will send a message to the target service
"""
import typing
import json

from websockets import WebSocketCommonProtocol


class RepeatMixin:
    """
    Mixin that adds a function to send a message from the source to the target
    """

    async def repeat(
        self,
        message: typing.Union[str, bytes, dict],
        source: WebSocketCommonProtocol,
        target: WebSocketCommonProtocol,
        path: str,
        *args,
        **kwargs
    ) -> None:
        """
        Send messages received from the websocket to the evaluation service

        Args:
            message: A message sent through the server
            source: The websocket connection that produced the message
            target: The websocket connection that should receive the message
            path: The path to the source socket on the server

        Returns:
            A response detailing the result of sending messages to the evaluation service
        """
        if isinstance(message, dict):
            message = json.dumps(message, indent=4)
        await target.send(message)
        return None
