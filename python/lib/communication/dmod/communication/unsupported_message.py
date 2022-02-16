from . import MessageEventType, Response, WebSocketInterface
from typing import Type


class UnsupportedMessageTypeResponse(Response):

    def __init__(self, actual_event_type: MessageEventType, listener_type: Type[WebSocketInterface],
                 message: str = None, data=None):
        if message is None:
            message = 'The {} event type is not supported by this {} listener'.format(
                actual_event_type, listener_type.__name__)
        super().__init__(success=False, reason='Message Event Type Unsupported', message=message, data=data)
        self.actual_event_type = actual_event_type
        self.listener_type = listener_type