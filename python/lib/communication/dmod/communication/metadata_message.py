from .message import AbstractInitRequest, MessageEventType, Response
from dmod.core.serializable_dict import SerializableDict
from numbers import Number
from typing import ClassVar, Dict, Optional, Type, Union
from pydantic import Field, root_validator

from dmod.core.enum import PydanticEnum


class MetadataPurpose(PydanticEnum):
    CONNECT = 1,
    """ The metadata relates to the opening of a connection. """
    DISCONNECT = 2,
    """ The metadata relates to the closing of a connection. """
    PROMPT = 3,
    """ The metadata it a prompt to the other side that it should send any needed metadata messages. """
    UNCHANGED = 4,
    """ The metadata indicate nothing needs to be communicated in response to a ``PROMPT``. """
    CHANGE_CONFIG = 5
    """ The metadata indicate something regarding the config of how the other side behaves needs changing. """

    @classmethod
    def get_value_for_name(cls, name_str: str) -> Optional['MetadataPurpose']:
        cleaned_up_str = name_str.strip().lower()
        for value in cls:
            if value.name.lower() == cleaned_up_str:
                return value
        return None


class MetadataSignal(SerializableDict):
    purpose: MetadataPurpose
    metadata_follows: bool

    class Config:
        fields = {
            "metadata_follows": {
                "alias": "additional_metadata",
                "description": (
                    "An indication of whether there is more metadata the sender needs to communicate beyond what is contained in this"
                    "message, thus letting the receiver know whether it should continue receiving after sending the response to this."
                ),
            }
        }


class MetadataMessage(MetadataSignal, AbstractInitRequest):

    event_type: ClassVar[MessageEventType] = MessageEventType.INVALID

    description: Optional[str]

    config_changes: Optional[Dict[str, Union[None, str, bool, int, float, dict, list]]] = Field(description="A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.")
    """
    A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.

    This will mainly be applicable when the purpose property is ``CHANGE_CONFIG``, and frequently can otherwise be
    left to/expected to be ``None``.  However, it should not be ``None`` when the purpose is ``CHANGE_CONFIG``.

    Note that the main dictionary can contain nested dictionaries also.  These should essentially be the serialized
    representations of ::class:`Serializable` object.  While the type hinting does not explicitly note this due to
    the recursive nature of the definition, nested dictionaries at any depth should have string keys and values of
    one of the types allowed for values in the top-level dictionary.

    It is recommended that an additional value be added to such nested dictionaries, under the key returned by
    ::method:`get_config_change_dict_type_key`.  This should be the string representation of the class type of the
    nested, serialized object.
    """

    @root_validator()
    def validate_purpose(cls, values):
        if values["purpose"] == MetadataPurpose.CHANGE_CONFIG and not values["config_changes"]:
            raise RuntimeError('Invalid {} initialization, setting {} to {} but without any config changes.'.format(
                cls.__class__, values["purpose"].__class__, values["purpose"].name))
        return values

    _config_change_dict_type_key: ClassVar[str] = 'config_value_dict_type'

    @classmethod
    def get_config_change_dict_type_key(cls) -> str:
        """
        Get the extra key that should be added to a config change dictionary value to indicate the object type the
        dictionary represents, typically in situations when the value is the serialized form of some
        ::class:`Serializable` object.

        This should normally be used outside this type to prepare some dict before passing it as the ``config_changes``
        init param when creating an instance of this type.

        Returns
        -------

        """
        return cls._config_change_dict_type_key


class MetadataResponse(Response):
    """
    The subtype of ::class:`Response` appropriate for ::class:`MetadataMessage` objects.
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = MetadataMessage
    data: MetadataSignal

    @classmethod
    def factory_create(cls, success: bool, reason: str, purpose: MetadataPurpose, expect_more: bool, message: str = ''):
        """
        Helper factory method to initialize instances, in particular ``data`` param given how that is set up to conform
        to super class init signature.

        Parameters
        ----------
        success
        reason
        purpose
        expect_more
        message

        Returns
        -------

        """
        data = MetadataSignal(purpose=purpose, metadata_follows=expect_more)

        return cls(success=success, reason=reason, data=data, message=message)

    @property
    def metadata_follows(self) -> bool:
        return self.data.metadata_follows

    @property
    def purpose(self) -> MetadataPurpose:
        return self.data.purpose
