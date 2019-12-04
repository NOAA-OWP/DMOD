import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Type


class MessageEventType(Enum):
    SESSION_INIT = 1,
    NWM_MAAS_REQUEST = 2,
    INVALID = -1


class Message(ABC):
    """
    Class representing communication message of some kind between parts of the NWM MaaS system.
    """

    event_type: MessageEventType = None
    """ :class:`MessageEventType`: the event type for this message implementation """

    @classmethod
    def get_message_event_type(cls) -> MessageEventType:
        """
        Get the message event type for this response message.

        Returns
        -------
        MessageEventType
            The event type for this message type
        """
        return cls.event_type

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    def __str__(self):
        return str(self.to_json())

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Response(Message, ABC):
    """
    Class representing in particular the type for a response to some other :class:`Message` sub-type.

    Parameters
    ----------
    success : bool
        Was the purpose encapsulated by the corresponding Message fulfilled; e.g., to perform a task or transfer info
    reason : str
        A summary of what the response conveys; e.g., request action trigger or disallowed
    message : str
        A more detailed explanation of what the response conveys
    data : dict
        Subtype-specific serialized data that should be conveyed as a result of the initial message

    Attributes
    ----------
    success : bool
        Was the purpose encapsulated by the corresponding Message fulfilled; e.g., to perform a task or transfer info
    reason : str
        A summary of what the response conveys; e.g., request action trigger or disallowed
    message : str
        A more detailed explanation of what the response conveys
    data : dict
        Subtype-specific serialized data that should be conveyed as a result of the initial message

    """

    response_to_type = Message
    """ The type of :class:`Message` for which this type is the response"""

    @classmethod
    def get_message_event_type(cls) -> MessageEventType:
        """
        Get the message event type for this response message.

        For :class:`Response` classes, this will be dependent on the output of :method:`get_response_to_type`, since it
        should always have the same event type as the message type for which it is a response.

        Returns
        -------
        MessageEventType
            The event type for this message type
        """
        return cls.get_response_to_type().event_type

    @classmethod
    def get_response_to_type(cls) -> Type[Message]:
        """
        Get the specific :class:`Message` sub-type for which this type models the response.

        Returns
        -------
        Message :
            The corresponding :class:`Message` type to this response type.
        """
        return cls.response_to_type

    def __init__(self, success: bool, reason: str, message: str = '', data=None):
        self.success = success
        self.reason = reason
        self.message = message
        self.data = data

    def to_dict(self) -> dict:
        return {'success': self.success, 'reason': self.reason, 'message': self.message, 'data': self.data}


class InvalidMessage(Message):
    """
    An implementation of :class:`Message` to model deserialized request messages that are not some other valid message
    type.
    """

    event_type: MessageEventType = MessageEventType.INVALID
    """ :class:`Message`: the type of Message for which this type is the response"""

    def __init__(self, content: dict):
        self.content = content

    def to_dict(self) -> dict:
        return {'content': self.content}


class InvalidMessageResponse(Response):

    response_to_type = InvalidMessage
    """ The type of :class:`Message` for which this type is the response"""

    def __init__(self, data=None):
        super().__init__(success=False,
                         reason='Invalid Request Message',
                         message='Request message was not formatted as any known valid type',
                         data=data)
