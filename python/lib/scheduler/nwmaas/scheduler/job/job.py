from abc import ABC, abstractmethod
from nwmaas.communication.scheduler_request import SchedulerRequestMessage
from typing import List, Optional, Union
from uuid import UUID

from nwmaas.scheduler.rsa_key_pair import RsaKeyPair
from nwmaas.scheduler.resources.resource_allocation import ResourceAllocation


class Job(ABC):
    """
    An abstract interface for a job performed by the MaaS system.
    """

    @property
    @abstractmethod
    def allocations(self) -> Optional[List[ResourceAllocation]]:
        """
        The scheduler allocation for this job.

        Returns
        -------
        Optional[List[ResourceAllocation]]
            The scheduler resource allocations for this job, or ``None`` if it is queued or otherwise not yet allocated.
        """
        pass

    @property
    @abstractmethod
    def cpu_count(self) -> int:
        """
        The number of CPUs for this job.

        Returns
        -------
        int
            The number of CPUs for this job.
        """
        pass

    @property
    @abstractmethod
    def job_id(self):
        """
        The unique identifier for this particular job.

        Returns
        -------
        The unique identifier for this particular job.
        """
        pass

    @property
    @abstractmethod
    def memory_size(self) -> int:
        """
        The amount of the memory needed for this job.

        Returns
        -------
        int
            The amount of the memory needed for this job.
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """
        The configured parameters for this job.

        Returns
        -------
        dict
            The configured parameters for this job.
        """
        pass

    @property
    @abstractmethod
    def rsa_key_pair(self) -> Optional[RsaKeyPair]:
        """
        The ::class:`RsaKeyPair` for this job's shared SSH RSA keys.

        Returns
        -------
        Optional[RsaKeyPair]
            The ::class:`RsaKeyPair` for this job's shared SSH RSA keys, or ``None`` if not has been set.
        """
        pass


class RequestedJob(Job):
    """
    An implementation of ::class:`Job` for jobs that were created due to the received of a client request via a
    ::class:`SchedulerRequestMessage` object.
    """

    def __init__(self, job_request: SchedulerRequestMessage):
        self._originating_request = job_request
        self._allocations = None
        self.job_uuid = None
        self._rsa_key_pair = None

    def add_allocation(self, allocation: ResourceAllocation):
        """
        Add a resource allocation to this object's list of allocations in ::attribute:`allocations`, initializing it if
        previously set to ``None``.

        Parameters
        ----------
        allocation : ResourceAllocation
            A resource allocation object to add.
        """
        if self._allocations is None:
            self.allocations = list()
        self.allocations.append(allocation)

    @property
    def allocations(self) -> Optional[List[ResourceAllocation]]:
        return self._allocations

    @allocations.setter
    def allocations(self, allocations: List[ResourceAllocation]):
        self._allocations = allocations

    @property
    def cpu_count(self) -> int:
        return self._originating_request.cpus

    @property
    def job_id(self) -> Optional[str]:
        """
        The unique job id for this job in the manager, if one has been set for it, or ``None``.

        The getter for the property returns the ::attribute:`UUID.bytes` field of the ::attribute:`job_uuid` property,
        if it is set, or ``None`` if it is not set.

        The setter for the property will actually set the ::attribute:`job_uuid` attribute, via a call to the setter for
        the ::attribute:`job_uuid` property.  ::attribute:`job_id`'s setter can accept either a ::class:`UUID` or a
        string, with the latter case being used to initialize a ::class:`UUID` object.

        Returns
        -------
        Optional[str]
            The unique job id for this job in the manager, if one has been set for it, or ``None``.
        """
        return self.job_uuid.bytes if isinstance(self.job_uuid, UUID) else None

    @job_id.setter
    def job_id(self, job_id: Union[str, UUID]):
        if isinstance(job_id, UUID):
            self.job_uuid = job_id
        else:
            self.job_uuid = UUID(str(job_id))

    @property
    def memory_size(self) -> int:
        return self._originating_request.memory

    @property
    def originating_request(self) -> SchedulerRequestMessage:
        """
        The original request that resulted in the creation of this job.

        Returns
        -------
        SchedulerRequestMessage
            The original request that resulted in the creation of this job.
        """
        return self._originating_request

    @property
    def parameters(self) -> dict:
        return self._originating_request.model_request.parameters

    @property
    def rsa_key_pair(self) -> Optional[RsaKeyPair]:
        return self._rsa_key_pair

    @rsa_key_pair.setter
    def rsa_key_pair(self, key_pair: RsaKeyPair):
        self._rsa_key_pair = key_pair


