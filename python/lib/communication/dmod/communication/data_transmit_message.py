from dmod.core.serializable import Serializable
from pydantic import Extra
from .message import AbstractInitRequest, MessageEventType, Response
from pydantic import Field
from typing import ClassVar, Dict, Optional, Type, Union
from numbers import Number
from uuid import UUID


class DataTransmitUUID(Serializable):
    series_uuid: UUID = Field(description="A unique id for the collective series of transmission message this instance is a part of.")
    """
    The expectation is that a larger amount of data will be broken up into multiple messages in a series.
    """

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Union[str, int]]:
        SERIES_UUID_KEY = "series_uuid"
        exclude = exclude or set()
        series_uuid_in_exclude = SERIES_UUID_KEY in exclude
        exclude.add(SERIES_UUID_KEY)

        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        if not series_uuid_in_exclude:
            serial[SERIES_UUID_KEY] = str(self.series_uuid)

        return serial

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


class DataTransmitResponseBody(DataTransmitUUID):

    class Config:
        extra = Extra.allow


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

