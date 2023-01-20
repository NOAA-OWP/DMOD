from dmod.core.serializable import Serializable
from .message import AbstractInitRequest, MessageEventType, Response
from pydantic import Field
from typing import ClassVar, Dict, Optional, Union
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
    series_uuid: UUID = Field(description="A unique id for the collective series of transmission message this instance is a part of.")
    """
    The expectation is that a larger amount of data will be broken up into multiple messages in a series.
    """
    is_last: bool = Field(False, description="Whether this is the last data transmission message in this series.")

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


class DataTransmitResponse(Response):
    """
    A ::class:`Response` subtype corresponding to ::class:`DataTransmitMessage`.

    Like is sibling, it contains a ::attribute:`series_uuid` property as an identifier for the associated transmission
    series of which it is a part.
    """

    response_to_type = DataTransmitMessage

    _KEY_SERIES_UUID = response_to_type._KEY_SERIES_UUID

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> 'DataTransmitResponse':
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        response_obj : Response
            A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
            parameter could not be used to instantiated a new object.
        """
        try:
            return cls(success=json_obj['success'], reason=json_obj['reason'], message=json_obj['message'],
                       series_uuid=json_obj['data'][cls._KEY_SERIES_UUID], data=json_obj['data'])
        except Exception as e:
            return None

    def __init__(self, series_uuid: Union[str, UUID], *args, **kwargs):
        if 'data' not in kwargs:
            kwargs['data'] = dict()
        kwargs['data'][self._KEY_SERIES_UUID] = str(series_uuid)
        super(DataTransmitResponse, self).__init__(*args, **kwargs)

    @property
    def series_uuid(self) -> UUID:
        return UUID(self.data[self._KEY_SERIES_UUID])

