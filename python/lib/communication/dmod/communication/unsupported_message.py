from .message import MessageEventType, Response
from .websocket_interface import WebSocketInterface
from typing import Type


class UnsupportedMessageTypeResponse(Response):
    actual_event_type: MessageEventType
    listener_type: Type[WebSocketInterface]
    message: str

    success = False
    reason = "Message Event Type Unsupported"

    def __init__(
        self,
        actual_event_type: MessageEventType,
        listener_type: Type[WebSocketInterface],
        message: str = None,
        data=None,
        **kwargs
    ):
        if message is None:
            message = "The {} event type is not supported by this {} listener".format(
                actual_event_type, listener_type.__name__
            )
        super().__init__(
            message=message,
            data=data,
            actual_event_type=actual_event_type,
            listener_type=listener_type,
        )
