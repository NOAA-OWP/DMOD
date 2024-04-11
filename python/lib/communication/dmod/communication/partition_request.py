from uuid import uuid4
from pydantic import Field
from typing import ClassVar, Dict, Optional, Type, Union
from dmod.core.serializable import Serializable
from .message import AbstractInitRequest, MessageEventType, Response
from .maas_request import ExternalRequest


# TODO: create separate "external" subtype if support for authenticated, session-based requests becomes necessary
class PartitionRequest(AbstractInitRequest):
    """
    Request for partitioning of the catchments in a hydrofabric, typically for distributed processing.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.PARTITION_REQUEST

    num_partitions: int
    uuid: Optional[str] = Field(default_factory=lambda: str(uuid4()), description="Get (as a string) the UUID for this instance.")
    hydrofabric_uid: str = Field(description="The unique identifier for the hydrofabric that is to be partitioned.")
    hydrofabric_data_id: Optional[str] = Field(description="When known, the 'data_id' for the dataset containing the associated hydrofabric.")
    description: Optional[str] = Field(description="The optional description or name of the hydrofabric that is to be partitioned.")

    class Config:
        fields = {
            "num_partitions": {"alias": "partition_count"},
            "description": {"alias": "hydrofabric_description"}
            }

    # QUESTION: is this unused?
    # catchment_count: str
    # _KEY_NUM_CATS = 'catchment_count'

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict):
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return PartitionResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    def __init__(
        self,
        *,
        hydrofabric_uid: str,
        # NOTE: default is None for backwards compatibility. could be specified using alias.
        num_partitions: int = None,
        hydrofabric_data_id: Optional[str] = None,
        uuid: Optional[str] = None,
        description: Optional[str] = None,
        **data
    ):
        """
        Initialize the request.

        Parameters
        ----------
        num_partitions : int
            The desired number of partitions.
        hydrofabric_uid : str
            The unique id of the hydrofabric associated with the partitioning request.
        hydrofabric_data_id : Optional[str]
            Optionally, the 'data_id' for the dataset containing the associated hydrofabric, when known.
        uuid : Optional[str]
            A unique identifier string for this request.
        description : Optional[str]
            An optional description or name for the hydrofabric.
        """

        super().__init__(
            num_partitions=num_partitions or data.pop("partition_count", None),
            hydrofabric_uid=hydrofabric_uid,
            hydrofabric_data_id=hydrofabric_data_id,
            uuid=uuid,
            description=description or data.pop("hydrofabric_description", None),
            **data
        )

    def __eq__(self, other):
        return self.uuid == other.uuid and self.hydrofabric_uid == other.hydrofabric_uid and self.hydrofabric_data_id == other.hydrofabric_data_id

    def __hash__(self):
        return hash("{}{}{}".format(self.uuid, self.hydrofabric_uid, self.hydrofabric_data_id))

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
        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        # include "class_name" if not in excludes
        if exclude is not None and "class_name" not in exclude:
            serial["class_name"] = self.__class__.__name__

        return serial


class PartitionResponseBody(Serializable):
    data_id: Optional[str]
    dataset_name: Optional[str]

class PartitionResponse(Response):
    """
    A response to a ::class:`PartitionRequest`.

    A successful response will contain the serialized partition representation within the ::attribute:`data` property.
    """
    data: PartitionResponseBody

    response_to_type: ClassVar[Type[AbstractInitRequest]] = PartitionRequest

    @classmethod
    def factory_create(cls, dataset_name: Optional[str], dataset_data_id: Optional[str], reason: str, message: str = '',
                       data: Optional[dict] = None):
        data_dict = {"data_id": dataset_data_id, "dataset_name": dataset_name}
        if data is not None:
            data_dict.update(data)
        return cls(success=(dataset_data_id is not None), reason=reason, message=message, data=data_dict)

    def __init__(self, success: bool, reason: str, message: str = '', data: Optional[Union[dict, PartitionResponseBody]] = None):
        data = data if isinstance(data, PartitionResponseBody) else PartitionResponseBody(**data or {})

        if not success:
            data.data_id =  None
            data.dataset_name =  None
        super().__init__(success=success, reason=reason, message=message, data=data)

    @property
    def dataset_data_id(self) -> Optional[str]:
        """
        The 'data_id' of the dataset where the partition config is saved when requests are successful.

        Returns
        -------
        Optional[str]
            The 'data_id' of the dataset where the partition config is saved when requests are successful.
        """
        return self.data.data_id

    @property
    def dataset_name(self) -> Optional[str]:
        """
        The name of the dataset where the partitioning config is saved when requests are successful.

        Returns
        -------
        Optional[str]
            The name of the dataset where the partitioning config is saved when requests are successful.
        """
        return self.data.dataset_name

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
        class_name_in_exclude = exclude is not None and "class_name" in exclude

        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        if not class_name_in_exclude:
            serial["class_name"] = self.__class__.__name__

        return serial


class PartitionExternalRequest(PartitionRequest, ExternalRequest):

    class Config:
        # NOTE: in parent class, `ExternalRequest`, `session_secret` is aliased using `session-secret`
        fields = {"session_secret": {"alias": "session_secret"}}


class PartitionExternalResponse(PartitionResponse):

    response_to_type: ClassVar[Type[AbstractInitRequest]] = PartitionExternalRequest
