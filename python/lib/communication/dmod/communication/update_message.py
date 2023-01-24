from .message import AbstractInitRequest, MessageEventType, Response
from pydoc import locate
from typing import ClassVar, Dict, Optional, Type, Union
from pydantic import Field, validator
import uuid

from dmod.core.serializable import Serializable


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

    event_type: ClassVar[MessageEventType] = MessageEventType.INFORMATION_UPDATE

    object_id: str = Field(description="The identifier for the object being updated, as a string.")
    object_type: Type[object] = Field(description="The type of object being updated.")
    # NOTE: updated_data must container at least one key
    updated_data: Dict[str, str] = Field(description="A serialized dictionary of properties to new values.")
    digest: str = Field(default_factory=lambda: uuid.uuid4().hex)

    @validator("object_type", pre=True)
    def _coerce_object_type(cls, value):
        obj_type = locate(value)
        if obj_type is None:
            raise ValueError("could not resolve `object_type`")
        return obj_type

    @validator("updated_data")
    def _validate_updated_data_has_keys(cls, value: Dict[str, str]):
        if not value.keys():
            raise ValueError("`updated_data` must have at least one key.")
        return value

    class Config:
        field_serializers = {"object_type": lambda self, _: self.object_type_string}

    @classmethod
    def get_digest_key(cls) -> str:
        return cls.__fields__["digest"].alias

    @classmethod
    def get_object_id_key(cls) -> str:
        return cls.__fields__["object_id"].alias

    @classmethod
    def get_object_type_key(cls) -> str:
        return cls.__fields__["object_type"].alias

    @classmethod
    def get_updated_data_key(cls) -> str:
        return cls.__fields__["updated_data"].alias

    @property
    def object_type_string(self) -> str:
        return '{}.{}'.format(self.object_type.__module__, self.object_type.__name__)


class UpdateMessageData(Serializable):
    digest: Optional[str]
    object_found: Optional[bool]


class UpdateMessageResponse(Response):
    """
    The subtype of ::class:`Response` appropriate for ::class:`UpdateMessage` objects.
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = UpdateMessage

    data: UpdateMessageData = Field(default_factory=UpdateMessageData)

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
        return UpdateMessageData.__fields__["digest"].alias

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
        return UpdateMessageData.__fields__["object_found"].alias

    def __init__(self, success: bool, reason: str, response_text: str = '',
                 data: Optional[Dict[str, Union[str, bool]]] = None, digest: Optional[str] = None,
                 object_found: Optional[bool] = None, **kwargs):
        # Work with digest/found either as params or contained within data param
        # However, move explicit params into the data dict param, allowing non-None params to overwrite
        data = dict() if data is None else data

        if digest is None and self.get_digest_subkey() in data:
            digest = data[self.get_digest_subkey()]

        if object_found is None and self.get_object_found_subkey() in data:
            object_found = data[self.get_object_found_subkey()]

        super().__init__(
            success=success,
            reason=reason,
            message=response_text,
            data=UpdateMessageData(digest=digest, object_found=object_found),
            **kwargs
            )

    @property
    def digest(self) -> Optional[str]:
        return self.data.digest

    @property
    def object_found(self) -> Optional[bool]:
        return self.data.object_found
