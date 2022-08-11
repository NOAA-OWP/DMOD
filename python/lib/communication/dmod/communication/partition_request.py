from uuid import uuid4
from numbers import Number
from typing import Optional, Union, Dict
from .maas_request import AbstractInitRequest, MessageEventType, Response


# TODO: create separate "external" subtype if support for authenticated, session-based requests becomes necessary
class PartitionRequest(AbstractInitRequest):
    """
    Request for partitioning of the catchments in a hydrofabric, typically for distributed processing.
    """

    event_type = MessageEventType.PARTITION_REQUEST
    _KEY_NUM_PARTS = 'partition_count'
    _KEY_NUM_CATS = 'catchment_count'
    # TODO: move this to separate type in the future for external use
    #_KEY_SECRET = 'session_secret'
    _KEY_UUID = 'uuid'
    _KEY_HYDROFABRIC_UID = 'hydrofabric_uid'
    _KEY_HYDROFABRIC_DATA_ID = 'hydrofabric_data_id'
    _KEY_HYDROFABRIC_DESC = 'hydrofabric_description'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict, **kwargs):
        hy_data_id = json_obj[cls._KEY_HYDROFABRIC_DATA_ID] if cls._KEY_HYDROFABRIC_DATA_ID in json_obj else None

        try:
            return cls(hydrofabric_uid=json_obj[cls._KEY_HYDROFABRIC_UID],
                       hydrofabric_data_id=hy_data_id,
                       num_partitions=json_obj[cls._KEY_NUM_PARTS],
                       description=json_obj.get(cls._KEY_HYDROFABRIC_DESC),
                       uuid=json_obj[cls._KEY_UUID],
                       **kwargs)
        except:
            return None

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

    def __init__(self, num_partitions: int, hydrofabric_uid: str, hydrofabric_data_id: Optional[str] = None,
                 uuid: Optional[str] = None, description: Optional[str] = None, *args, **kwargs):
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
        super(PartitionRequest, self).__init__(*args, **kwargs)
        self._hydrofabric_uid = hydrofabric_uid
        self._hydrofabric_data_id = hydrofabric_data_id
        self._num_partitions = num_partitions
        self._uuid = uuid if uuid else str(uuid4())
        self._description = description

    def __eq__(self, other):
        return self.uuid == other.uuid and self.hydrofabric_uid == other.hydrofabric_uid and self.hydrofabric_data_id == other.hydrofabric_data_id

    def __hash__(self):
        return hash("{}{}{}".format(self.uuid, self.hydrofabric_uid, self.hydrofabric_data_id))

    @property
    def description(self) -> Optional[str]:
        """
        The optional description or name of the hydrofabric that is to be partitioned.

        Returns
        -------
        Optional[str]
            The optional description or name of the hydrofabric that is to be partitioned.
        """
        return self._description

    @property
    def hydrofabric_data_id(self) -> Optional[str]:
        """
        When known, the 'data_id' for the dataset containing the associated hydrofabric.

        Returns
        -------
        Optional[str]
            When known, the 'data_id' for the dataset containing the associated hydrofabric.
        """
        return self._hydrofabric_data_id

    @property
    def hydrofabric_uid(self) -> str:
        """
        The unique identifier for the hydrofabric that is to be partitioned.

        Returns
        -------
        str
            The unique identifier for the hydrofabric that is to be partitioned.
        """
        return self._hydrofabric_uid

    @property
    def num_partitions(self) -> int:
        return self._num_partitions

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serialized = {
            'class_name': self.__class__.__name__,
            self._KEY_HYDROFABRIC_UID: self.hydrofabric_uid,
            self._KEY_NUM_PARTS: self.num_partitions,
            #self._KEY_SECRET: self.session_secret,
            self._KEY_UUID: self.uuid,
        }
        if self.description is not None:
            serialized[self._KEY_HYDROFABRIC_DESC] = self.description
        if self.hydrofabric_data_id is not None:
            serialized[self._KEY_HYDROFABRIC_DATA_ID] = self.hydrofabric_data_id
        return serialized

    @property
    def uuid(self) -> str:
        """
        Get (as a string) the UUID for this instance.

        Returns
        -------
        str
            The UUID for this instance, as a string.
        """
        return self._uuid


class PartitionResponse(Response):
    """
    A response to a ::class:`PartitionRequest`.

    A successful response will contain the serialized partition representation within the ::attribute:`data` property.
    """
    _DATA_KEY_DATASET_DATA_ID = 'data_id'
    _DATA_KEY_DATASET_NAME = 'dataset_name'
    response_to_type = PartitionRequest

    @classmethod
    def factory_create(cls, dataset_name: Optional[str], dataset_data_id: Optional[str], reason: str, message: str = '',
                       data: Optional[dict] = None):
        data_dict = {cls._DATA_KEY_DATASET_DATA_ID: dataset_data_id, cls._DATA_KEY_DATASET_NAME: dataset_name}
        if data is not None:
            data_dict.update(data)
        return cls(success=(dataset_data_id is not None), reason=reason, message=message, data=data_dict)

    def __init__(self, success: bool, reason: str, message: str = '', data: Optional[dict] = None):
        if data is None:
            data = {}
        if not success:
            data[self._DATA_KEY_DATASET_DATA_ID] = None
            data[self._DATA_KEY_DATASET_NAME] = None
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
        return self.data[self._DATA_KEY_DATASET_DATA_ID]

    @property
    def dataset_name(self) -> Optional[str]:
        """
        The name of the dataset where the partitioning config is saved when requests are successful.

        Returns
        -------
        Optional[str]
            The name of the dataset where the partitioning config is saved when requests are successful.
        """
        return self.data[self._DATA_KEY_DATASET_NAME]

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = super(PartitionResponse, self).to_dict()
        serial['class_name'] = self.__class__.__name__
        return serial
