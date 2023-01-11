from abc import ABC
from typing import ClassVar, Type

from dmod.core.serializable import Serializable, ResultIndicator
from dmod.core.enum import PydanticEnum


#FIXME make an independent enum of model request types???
class MessageEventType(PydanticEnum):
    SESSION_INIT = 1

    MODEL_EXEC_REQUEST = 2
    """ Represents when a request occurs for model execution. """

    SCHEDULER_REQUEST = 3
    """ Represents when a request occurs for an allocated, model execution ***job*** to be scheduled and run. """

    INFORMATION_UPDATE = 4

    METADATA = 5

    PARTITION_REQUEST = 6
    """ Represents when a request occurs for generating a Nextgen partition configuration. """

    EVALUATION_REQUEST = 7
    """ Represents when a request occurs for a model evaluation job to be performed. """

    CALIBRATION_REQUEST = 8
    """ Represents when a request occurs for a model calibration job to be performed. """

    DATASET_MANAGEMENT = 9
    """ Event relating to management of datasets and contained data (e.g., creation, upload, delete, etc.). """

    DATA_TRANSMISSION = 10

    INVALID = -1


class InitRequestResponseReason(PydanticEnum):
    """
    Values for the ``reason`` attribute in responses to ``AbstractInitRequest`` messages.
    """

    UNRECOGNIZED_SESSION_SECRET = 1
    """The containing session for the init request could not be identified from the session secret in the message."""
    EXPIRED_SESSION = 2
    """The containing session for the init request is considered expired, and thus can no longer make requests."""
    UNAUTHORIZED = 3
    """The containing session for the init request does not authorize the user to make such a request."""
    ACCEPTED = 4
    """The request was deemed authorized, and it was accepted by the receiver."""
    REJECTED = 5
    """The request was deemed authorized, but the receive rejected the request for other reasons."""
    UNKNOWN = 6
    """The reason for the particular response is unknown or not well defined in the enum type."""
    UNNECESSARY = 7
    """The request does not utilize session data"""


class Message(Serializable, ABC):
    """
    Class representing communication message of some kind between parts of the NWM MaaS system.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.INVALID
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


class AbstractInitRequest(Message, ABC):
    """
    Abstract type representing a :class:`Message` that is an initiating message in some conversation, used when some
    kind of response is expected back.

    Typically, implementations of this type will be for modeling requests for something from a listening service: e.g.,
    for information or for some action to be performed.  This is not absolutely necessary, though; what matters is the
    serial send-reply nature of the particular interaction involved, and that instances of this type start such
    interactions.
    """


class Response(ResultIndicator, Message, ABC):
    """
    Class representing a response to some ::class:`Message`, typically a ::class:`AbstractInitRequest` sub-type.

    Parameters
    ----------
    success : bool
        Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
    reason : str
        A summary of what the response conveys; e.g., request action trigger or disallowed
    message : str
        A more detailed explanation of what the response conveys
    data : Union[dict, Serializeable, None]
        Subtype-specific serialized data that should be conveyed as a result of the initial message

    Attributes
    ----------
    success : bool
        Was the purpose encapsulated by the corresponding message fulfilled; e.g., to perform a task or transfer info
    reason : str
        A summary of what the response conveys; e.g., request action trigger or disallowed
    message : str
        A more detailed explanation of what the response conveys
    data : Union[dict, Serializeable, None]
        Subtype-specific serialized data that should be conveyed as a result of the initial message

    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = AbstractInitRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    @classmethod
    def _factory_init_data_attribute(cls, json_obj: dict):
        """
        Initialize the argument value for a constructor param used to set the :attr:`data` attribute appropriate for
        this type, given the parent JSON object, which may mean simply returning the value or may mean deserializing the
        value to some object type, depending on the implementation.

        The intent is for this to be used by :meth:`factory_init_from_deserialized_json`, where initialization logic for
        the value to be set as :attr:`data` from the provided param may vary depending on the particular class.

        In the default implementation, the value found at the 'data' key is simply directly returned, or None is
        returned if the 'data' key is not found.

        Parameters
        ----------
        json_obj : dict
            the parent JSON object containing the desired data value under the 'data' key

        Returns
        -------
        data : dict
            the resulting data value object

        See Also
        -------
        factory_init_from_deserialized_json
        """
        try:
            return json_obj['data']
        except Exception as e:
            return None

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
    def get_response_to_type(cls) -> Type[AbstractInitRequest]:
        """
        Get the specific :class:`AbstractInitRequest` sub-type for which this type models the response.

        Returns
        -------
        Message :
            The corresponding :class:`Message` type to this response type.
        """
        return cls.response_to_type


class InvalidMessage(AbstractInitRequest):
    """
    An implementation of :class:`Message` to model deserialized request messages that are not some other valid message
    type.
    """

    event_type: MessageEventType = MessageEventType.INVALID
    """ :class:`MessageEventType`: the type of ``MessageEventType`` for which this message is applicable. """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
        parameter could not be used to instantiated a new object.
        """
        try:
            return cls(content=json_obj['content'])
        except:
            return None

    def __init__(self, content: dict):
        self.content = content

    def to_dict(self) -> dict:
        return {'content': self.content}


class InvalidMessageResponse(Response):

    response_to_type = InvalidMessage
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    def __init__(self, data=None):
        super().__init__(success=False,
                         reason='Invalid Request Message',
                         message='Request message was not formatted as any known valid type',
                         data=data)


class ErrorResponse(Response):
    """
    A response to inform a client of an error that has occured within a request
    """
    def __init__(self, message: str, http_code: int = None):
        if not http_code:
            http_code = 500

        if not isinstance(http_code, int):
            try:
                http_code = int(float(http_code))
            except:
                http_code = str(http_code)
        super().__init__(success=False, reason="Error", message=message, data={"http_code": http_code})
