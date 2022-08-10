from .message import AbstractInitRequest, MessageEventType, Response
from typing import Dict, Optional, Union
from numbers import Number
from uuid import UUID


class DataTransmitMessage(AbstractInitRequest):
    """
    Specialized message type for transmitting data.

    A specialized message type for data transmit.  All messages are associated with a (conceptual) "transmission series"
    for which instances have a ::attribute:`series_uuid` property as an identifier.  This allows for negotiation and
    integrity checking on both sides of the transmission, and to break transmissions up into multiple messages.

    Instances also have a ::attribute:`is_last` to indicate if they transmit the last of the data for their series.

    In order to serialize and deserialize effectively, data is stored in the ::attribute:`data` property as a decoded
    ::class:`str` object.  However, instances can be initialized using either ::class:`str` or ::class:`bytes` data.
    """

    _KEY_SERIES_UUID = 'series_uuid'

    event_type: MessageEventType = MessageEventType.DATA_TRANSMISSION

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['DataTransmitMessage']:
        try:
            return cls(data=json_obj['data'], series_uuid=UUID(json_obj[cls._KEY_SERIES_UUID]),
                       is_last=json_obj['is_last'])
        except Exception as e:
            return None

    def __init__(self, data: Union[str, bytes], series_uuid: UUID, is_last: bool = False, *args, **kwargs):
        super(DataTransmitMessage, self).__init__(*args, **kwargs)
        self._data: str = data if isinstance(data, str) else data.decode()
        self._series_uuid = series_uuid
        self._is_last: bool = is_last

    @property
    def data(self) -> str:
        """
        The data carried by this message, in decoded string form.

        Returns
        -------
        str
            The data carried by this message, in decoded string form.
        """
        return self._data

    @property
    def is_last(self) -> bool:
        """
        Whether this is the last data transmission message in this series.

        Returns
        -------
        bool
            Whether this is the last data transmission message in this series.
        """
        return self._is_last

    @property
    def series_uuid(self) -> UUID:
        """
        A unique id for the collective series of transmission message this instance is a part of.

        The expectation is that a larger amount of data will be broken up into multiple messages in a series.

        Returns
        -------
        UUID
            A unique id for the collective series of transmission message this instance is a part of.
        """
        return self._series_uuid

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        return {'data': self.data, self._KEY_SERIES_UUID: str(self.series_uuid), 'is_last': self.is_last}


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

