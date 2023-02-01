from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import root_validator, validator
from .resource import SingleHostProcessingAssetPool


class ResourceAllocation(SingleHostProcessingAssetPool):
    """
    Implementation of ::class:`SingleHostProcessingAssetPool` representing a sub-collection of processing assets on a
    resource that have been allocated for a job.
    """
    created: datetime

    class Config:
        fields = {
            "pool_id": {"alias": "node_id"},
            "hostname": {"alias": "Hostname"},
            "cpu_count": {"alias": "cpus_allocated"},
            "memory": {"alias": "mem"},
            "created": {"alias": "Created"},
            "unique_id_separator": {"alias": "separator"},
        }
        field_serializers = {
            "created": lambda v: v.timestamp()
        }

    @validator("created", pre=True)
    def _validate_datetime(cls, value) -> datetime:
        if value is None:
            return datetime.now()
        elif isinstance(value, datetime):
            return value
        elif isinstance(value, float):
            return datetime.fromtimestamp(value)
        return datetime.fromtimestamp(float(value))

    @root_validator(pre=True)
    def _lowercase_all_keys(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        return {k.lower(): v for k, v in values.items()}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceAllocation):
            return False
        else:
            return self.resource_id == other.resource_id \
                   and self.hostname == other.hostname \
                   and self.cpu_count == other.cpu_count \
                   and self.memory == other.memory \
                   and self.created == other.created

    def __init__(
        self,
        resource_id: str = None,
        hostname: str = None,
        cpus_allocated: int = None,
        requested_memory: int = None,
        created: Optional[Union[str, float, datetime]] = None,
        **data
        ):
        if data:
            super().__init__(cpus_allocated=cpus_allocated, **data)
            return
        super().__init__(pool_id=resource_id, hostname=hostname, cpu_count=cpus_allocated, memory=requested_memory, created=created)

    def get_unique_id(self, separator: str) -> str:
        return f"{self.__class__.__name__}{separator}{self.resource_id}{separator}{str(self.created.timestamp())}"

    @property
    def node_id(self) -> str:
        """
        Convenience property for getting the resource id for the parent resource of this allocation, since it is
        referred to as 'node id' in some situations.

        Returns
        -------
        str
            The ::attribute:`resource_id` for this allocation.

        See Also
        -------
        ::attribute:`resource_id`
        """
        return self.resource_id

    @property
    def resource_id(self) -> str:
        """
        Get the resource id of the ::class:`Resource` of which this is a subset of assets, which is the same as that
        resource's ``pool_id``.

        Returns
        -------
        str
            The ``resource_id`` or ``pool_id`` of the ::class:`Resource` of which this is a subset of assets.
        """
        return self.pool_id

    @property
    def unique_id(self) -> str:
        return self.get_unique_id(self.unique_id_separator)
