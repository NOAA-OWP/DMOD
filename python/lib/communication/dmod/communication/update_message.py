from .message import AbstractInitRequest, MessageEventType, Response
from pydoc import locate
from typing import Dict, Optional, Type
import uuid


class UpdateMessage(AbstractInitRequest):
    """
    A serializable and deserializable message object for communicating that some modeled entity has been updated.

    The entity actually being updated is identified by two properties: ::attribute:`object_type` and
    ::attribute:`object_id`.

    First, the ::attribute:`object_type` property indicates the particular type of thing that was updated, via a
    reference to the analogous class type used for modeling such entities.  This is internally represented as the actual
    class type, but note that when messages are serialized, it is converted to the fully-qualified class name.  The
    ::attribute:`object_type_string` property exists for accessing this derived string form directly.

    Second, the ::attribute:`object_id` provides a unique identifier for the updated object in the context of all
    objects of the type indicated by ::attribute:`object_type`.  Because since the typing may vary for actual updated
    types, this is always internally maintained in this type as a string.

    The actual information being updated is maintained in a nested dictionary within the ::attribute:`updated_data`
    property.  The modified properties of the updated object are keyed by property name, with the updated values again
    being represented in string form internally.

    Additionally, an object has a ::attribute:`digest` property for uniquely identifying itself and the particular
    update it conveys.
    """

    event_type: MessageEventType = MessageEventType.INFORMATION_UPDATE

    _DIGEST_KEY = 'digest'
    _OBJECT_ID_KEY = 'object_id'
    _OBJECT_TYPE_KEY = 'object_type'
    _UPDATED_DATA_KEY = 'updated_data'

    @classmethod
    def get_digest_key(cls) -> str:
        return cls._DIGEST_KEY

    @classmethod
    def get_object_id_key(cls) -> str:
        return cls._OBJECT_ID_KEY

    @classmethod
    def get_object_type_key(cls) -> str:
        return cls._OBJECT_TYPE_KEY

    @classmethod
    def get_updated_data_key(cls) -> str:
        return cls._UPDATED_DATA_KEY

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        The method expects the ::attribute:`object_type` to be represented as the fully-qualified name string for the
        particular class type.  If the method cannot located the actual class type by this string, the JSON is
        considered invalid.

        Additionally, if the representation of the ::attribute:`updated_data` property is not a (serialized) nested
        dictionary, or is an empty dictionary, this is also considered invalid.

        Both ::attribute:`digest` and ::attribute:`object_id` representations are valid if they can be cast to strings.

        The JSON is not considered invalid if it has other keys/values at the root level beyond those for the standard
        properties.

        For invalid JSON representations, ``None`` is returned.

        Parameters
        ----------
        json_obj

        Returns
        -------
        Optional[UpdateMessage]
            A new object of this type instantiated from the deserialize JSON object dictionary, or ``None`` if the JSON
            is not a valid serialized representation of this type.
        """
        try:
            obj_type = locate(json_obj[cls.get_object_type_key()])
            if obj_type is None:
                return None
            obj_id = str(json_obj[cls.get_object_id_key()])
            updated_data = json_obj[cls.get_updated_data_key()]
            if not isinstance(updated_data, dict) or len(updated_data.keys()) == 0:
                return None
            message = cls(object_id=obj_id, object_type=obj_type, updated_data=updated_data)
            message._digest = str(json_obj[cls.get_digest_key()])
        except:
            return None

    def __init__(self, object_id: str, object_type: Type, updated_data: Dict[str, str]):
        """
        Initialize a new object.

        Parameters
        ----------
        object_type : str
            The type of object being updated, as a
        object_id
        updated_data
        """
        self._digest = None
        self._object_type = object_type
        self._object_id = object_id
        self._updated_data = updated_data

    @property
    def digest(self) -> str:
        if self._digest is None:
            self._digest = uuid.uuid4().hex
        return self._digest

    @property
    def object_id(self) -> str:
        return self._object_id

    @property
    def object_type(self) -> Type:
        return self._object_type

    @property
    def object_type_string(self) -> str:
        return '{}.{}'.format(self.object_type.__module__, self.object_type.__name__)

    def to_dict(self) -> dict:
        """
        Get the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).

        Returns
        -------
        dict
            The representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).
        """
        return {self.get_object_id_key(): self.object_id, self.get_digest_key(): self.digest,
                self.get_object_type_key(): self.object_type_string, self.get_updated_data_key(): self.updated_data}

    @property
    def updated_data(self) -> Dict[str, str]:
        return self._updated_data


class UpdateMessageResponse(Response):
    """
    The subtype of ::class:`Response` appropriate for ::class:`UpdateMessage` objects.
    """

    _DIGEST_SUBKEY = 'digest'
    _OBJECT_FOUND_SUBKEY = 'object_found'

    response_to_type = UpdateMessage

    @classmethod
    def get_digest_subkey(cls) -> str:
        """
        Get the "subkey" (i.e., the key for the value within the nested ``data`` dictionary) for the ``digest`` property
        value in serialized representations.

        Returns
        -------
        str
            The "subkey" (i.e., the key for the value within the nested ``data`` dictionary) for the ``digest`` in
            serialized representations.
        """
        return cls._DIGEST_SUBKEY

    @classmethod
    def get_object_found_subkey(cls) -> str:
        """
        Get the "subkey" (i.e., the key for the value within the nested ``data`` dictionary) for the ``object_found``
        property value serialized representations.

        Returns
        -------
        str
            The "subkey" (i.e., the key for the value within the nested ``data`` dictionary) for the ``digest`` in
            serialized representations.
        """
        return cls._OBJECT_FOUND_SUBKEY

    def __init__(self, digest: str, object_found: bool, success: bool, reason: str, response_text: str = ''):
        super().__init__(success=success, reason=reason, message=response_text,
                         data={self.get_digest_subkey(): digest, self.get_object_found_subkey(): object_found})

        self._digest = digest
        self._object_found = object_found
        self._successful = success
        self._response_text = response_text

    @property
    def digest(self) -> str:
        return self.data[self.get_digest_subkey()]

    @property
    def object_found(self) -> bool:
        return self.data[self.get_object_found_subkey()]
