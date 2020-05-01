from datetime import datetime
from typing import Dict, Optional, Union
from .resource import SingleHostProcessingAssetPool


class ResourceAllocation(SingleHostProcessingAssetPool):
    """
    Implementation of ::class:`SingleHostProcessingAssetPool` representing a sub-collection of processing assets on a
    resource that have been allocated for a job.
    """

    @classmethod
    def factory_init_from_dict(cls, alloc_dict: dict, ignore_extra_keys: bool = False) -> 'ResourceAllocation':
        """
        parent:
        """
        node_id = None
        hostname = None
        cpus_allocated = None
        mem = None
        created = None

        for param_key in alloc_dict:
            # We don't care about non-string keys directly, but they are implicitly extra ...
            if not isinstance(param_key, str):
                if not ignore_extra_keys:
                    raise ValueError("Unexpected non-string allocation key")
                else:
                    continue
            lower_case_key = param_key.lower()
            if lower_case_key == 'node_id' and node_id is None:
                node_id = alloc_dict[param_key]
            elif lower_case_key == 'hostname' and hostname is None:
                hostname = alloc_dict[param_key]
            elif lower_case_key == 'cpus_allocated' and cpus_allocated is None:
                cpus_allocated = int(alloc_dict[param_key])
            elif lower_case_key == 'mem' and mem is None:
                mem = int(alloc_dict[param_key])
            elif lower_case_key == 'created' and created is None:
                created = alloc_dict[param_key]
            elif not ignore_extra_keys:
                raise ValueError("Unexpected allocation key (or case-insensitive duplicate) {}".format(param_key))

        # Make sure we have everything required set
        if node_id is None or hostname is None or cpus_allocated is None or mem is None:
            raise ValueError("Insufficient valid values keyed within allocation dictionary")

        return cls(resource_id=node_id, hostname=hostname, cpus_allocated=cpus_allocated, requested_memory=mem)

    def __init__(self, resource_id: str, hostname: str, cpus_allocated: int, requested_memory: int,
                 created: Optional[Union[str, float, datetime]] = None):
        super().__init__(pool_id=resource_id, hostname=hostname, cpu_count=cpus_allocated, memory=requested_memory)
        self._set_created(created)

    def _set_created(self, created: Optional[Union[str, float, datetime]] = None):
        """
        A "private" method for setting the ::attribute:`created` property, potentially converting to value to set.

        A ``None`` argument is interpreted as ``now``.  Other non-datetime args are interpreted as string or numeric
        epoch timestamp representations.

        Parameters
        ----------
        created
            The value to set.
        """
        if created is None:
            self._created = datetime.now()
        elif isinstance(created, datetime):
            self._created = created
        elif isinstance(created, float):
            self._created = datetime.fromtimestamp(created/1000)
        else:
            self._created = datetime.fromtimestamp(float(created)/1000)

    @property
    def created(self) -> datetime:
        return self._created

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

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {'node_id': self.resource_id, 'Hostname': self.hostname, 'cpus_allocated': self.cpu_count,
                'mem': self.memory, 'Created': self.created.timestamp()}

    @property
    def unique_id(self) -> str:
        return self.__class__.__name__ + self.unique_id_separator + self.resource_id + self.unique_id_separator \
               + str(self.created.timestamp())
