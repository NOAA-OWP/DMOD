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
    _KEY_HYDROFABRIC_HASH = 'hydrofabric_hash'
    _KEY_HYDROFABRIC_DESC = 'hydrofabric_description'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return PartitionRequest(hydrofabric_hash=json_obj[cls._KEY_HYDROFABRIC_HASH],
                                    num_partitions=json_obj[cls._KEY_NUM_PARTS],
                                    #session_secret=json_obj[cls._KEY_SECRET],
                                    description=json_obj[cls._KEY_HYDROFABRIC_DESC] if cls._KEY_HYDROFABRIC_DESC in json_obj else None,
                                    uuid=json_obj[cls._KEY_UUID])
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

    def __init__(self, hydrofabric_hash: int, num_partitions: int, uuid: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize the request.

        Parameters
        ----------
        hydrofabric_hash : int
            The hash/checksum to identify the hydrofabric associated with the partitioning request.
        num_partitions : int
            The desired number of partitions.
        uuid : Optional[str]
            A unique identifier string for this request.
        description : Optional[str]
            An optional description or name for the hydrofabric.
        """
        super(PartitionRequest, self).__init__()
        self._hydrofabric_hash = hydrofabric_hash
        self._num_partitions = num_partitions
        self._uuid = uuid if uuid else str(uuid4())
        self._description = description

    def __eq__(self, other):
        return self.uuid == other.uuid and self.hydrofabric_hash == other.hydrofabric_hash

    def __hash__(self):
        return hash("{}{}".format(self.uuid, self.hydrofabric_hash))

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
    def hydrofabric_hash(self) -> int:
        """
        The hash/checksum/identifier for the hydrofabric that is to be partitioned.

        Returns
        -------
        int
            The hash/checksum/identifier for the hydrofabric that is to be partitioned.
        """
        return self._hydrofabric_hash

    @property
    def num_partitions(self) -> int:
        return self._num_partitions

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serialized = {
            self._KEY_HYDROFABRIC_HASH: self.hydrofabric_hash,
            self._KEY_NUM_PARTS: self.num_partitions,
            #self._KEY_SECRET: self.session_secret,
            self._KEY_UUID: self.uuid,
        }
        if self.description is not None:
            serialized[self._KEY_HYDROFABRIC_DESC] = self.description
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
    response_to_type = PartitionRequest



