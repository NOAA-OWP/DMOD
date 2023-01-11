from .message import AbstractInitRequest, MessageEventType, Response
from numbers import Number
from typing import Dict, Optional, Union

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


class MetadataMessage(AbstractInitRequest):

    event_type: MessageEventType = MessageEventType.METADATA

    _purpose_serial_key = 'purpose'
    _description_serial_key = 'description'
    _metadata_follows_serial_key = 'additional_metadata'
    _config_changes_serial_key = 'config_changes'
    _config_change_dict_type_key = 'config_value_dict_type'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['MetadataMessage']:
        if cls._purpose_serial_key not in json_obj:
            return None
        purpose = MetadataPurpose.get_value_for_name(json_obj[cls._purpose_serial_key])
        if purpose is None:
            return None
        if cls._metadata_follows_serial_key in json_obj:
            metadata_follows = json_obj[cls._metadata_follows_serial_key]
        else:
            # default to False for this, as this is pretty safe assumption if we don't see it explicit
            metadata_follows = False
        description = json_obj[cls._description_serial_key] if cls._description_serial_key in json_obj else None
        cfg_changes = json_obj[cls._config_changes_serial_key] if cls._config_changes_serial_key in json_obj else None
        return cls(purpose=purpose, description=description, metadata_follows=metadata_follows,
                   config_changes=cfg_changes)

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

    def __init__(self, purpose: MetadataPurpose, description: Optional[str] = None, metadata_follows: bool = False,
                 config_changes: Optional[Dict[str, Union[None, str, bool, Number, dict, list]]] = None):
        self._purpose = purpose
        self._description = description
        self._metadata_follows = metadata_follows
        self._config_changes = config_changes
        if self._purpose == MetadataPurpose.CHANGE_CONFIG and not self._config_changes:
            raise RuntimeError('Invalid {} initialization, setting {} to {} but without any config changes.'.format(
                self.__class__, self._purpose.__class__, self._purpose.name))

    @property
    def config_changes(self) -> Optional[Dict[str, Union[None, str, bool, Number, dict, list]]]:
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

        Returns
        -------
        Optional[Dict[str, Union[None, str, bool, Number, dict]]]
            A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.
        """
        # This should get handled in __init__ but put here anyway
        if self._purpose == MetadataPurpose.CHANGE_CONFIG and not self._config_changes:
            raise RuntimeError('Invalid {} initialization, setting {} to {} but without any config changes.'.format(
                self.__class__, self._purpose.__class__, self._purpose.name))
        return self._config_changes

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def metadata_follows(self) -> bool:
        """
        An indication of whether there is more metadata the sender needs to communicate beyond what is contained in this
        message, thus letting the receiver know whether it should continue receiving after sending the response to this.

        Returns
        -------
        bool
            An indication of whether there is more metadata the sender needs to communicate beyond what is contained in
            this message, thus letting the receiver know whether it should continue receiving after sending the response
            to this.
        """
        return self._metadata_follows

    @property
    def purpose(self) -> MetadataPurpose:
        return self._purpose

    def to_dict(self) -> dict:
        result = {self._purpose_serial_key: self.purpose.name, self._metadata_follows_serial_key: self.metadata_follows}
        if self.description:
            result[self._description_serial_key] = self.description
        if self.config_changes:
            result[self._config_changes_serial_key] = self.config_changes
        return result


class MetadataResponse(Response):
    """
    The subtype of ::class:`Response` appropriate for ::class:`MetadataMessage` objects.
    """

    _metadata_follows_serial_key = MetadataMessage._metadata_follows_serial_key
    _purpose_serial_key = MetadataMessage._purpose_serial_key
    response_to_type = MetadataMessage

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
        data = {cls._purpose_serial_key: purpose.name, cls._metadata_follows_serial_key: expect_more}
        return cls(success=success, reason=reason, data=data, message=message)

    def __init__(self, success: bool, reason: str, data: dict, message: str = ''):
        super().__init__(success=success, reason=reason, message=message, data=data)

    @property
    def metadata_follows(self) -> bool:
        return self.data[self._metadata_follows_serial_key]

    @property
    def purpose(self) -> MetadataPurpose:
        return MetadataPurpose.get_value_for_name(self.data[self._purpose_serial_key])
