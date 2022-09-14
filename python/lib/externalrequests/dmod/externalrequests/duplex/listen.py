import abc

from websockets import WebSocketServerProtocol

from dmod.core import decorators

from .handler import MessageHandlerMixin


class ListenerMixin(MessageHandlerMixin, abc.ABC):
    """
    Mixin for ConsumerProducers that listen for messages through the client and forward them back through the server
    """
    @decorators.client_message_handler
    async def listen(
        self,
        message: str,
        websocket: WebSocketServerProtocol,
        *args,
        **kwargs
    ) -> None:
        """
        Listen for messages from the evaluation service and send them back through the websocket

        Args:
            message: Data sent through a client
            websocket: The websocket that provided the initial request
            client:
            path: The path to the socket on the server

        Returns:
            A response detailing the result of the communication from the evaluation service
        """

        await websocket.send(message)
        return None
