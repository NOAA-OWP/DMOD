from dmod.core.serializable import Serializable
from .message import AbstractInitRequest, MessageEventType, Response
from pydantic import Field
from typing import ClassVar, Type, Union
from typing_extensions import TypeAlias
from uuid import UUID


class DataTransmitUUID(Serializable):
    series_uuid: UUID = Field(description="A unique id for the collective series of transmission message this instance is a part of.")
    """
    The expectation is that a larger amount of data will be broken up into multiple messages in a series.
    """

    class Config:
        field_serializers = {"series_uuid": lambda s: str(s)}


class DataTransmitMessage(DataTransmitUUID, AbstractInitRequest):
    """
    Specialized message type for transmitting data.

    A specialized message type for data transmit.  All messages are associated with a (conceptual) "transmission series"
    for which instances have a ::attribute:`series_uuid` property as an identifier.  This allows for negotiation and
    integrity checking on both sides of the transmission, and to break transmissions up into multiple messages.

    Instances also have a ::attribute:`is_last` to indicate if they transmit the last of the data for their series.

    In order to serialize and deserialize effectively, data is stored in the ::attribute:`data` property as a decoded
    ::class:`str` object.  However, instances can be initialized using either ::class:`str` or ::class:`bytes` data.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.DATA_TRANSMISSION

    data: str = Field(description="The data carried by this message, in decoded string form.")
    is_last: bool = Field(False, description="Whether this is the last data transmission message in this series.")


DataTransmitResponseBody: TypeAlias = DataTransmitUUID


class DataTransmitResponse(Response):
    """
    A ::class:`Response` subtype corresponding to ::class:`DataTransmitMessage`.

    Like is sibling, it contains a ::attribute:`series_uuid` property as an identifier for the associated transmission
    series of which it is a part.
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = DataTransmitMessage

    data: DataTransmitResponseBody

    # `series_uuid` required in prior version of code
    def __init__(self, series_uuid: Union[str, UUID] = None, **kwargs):
        # assume no need for backwards compatibility
        if series_uuid is None:
            super().__init__(**kwargs)
            return

        if "data" not in kwargs:
            kwargs["data"] = dict()

        kwargs["data"]["series_uuid"] = series_uuid
        super().__init__(**kwargs)

    @property
    def series_uuid(self) -> UUID:
        return self.data.series_uuid

