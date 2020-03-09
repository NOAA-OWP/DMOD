from abc import ABC, abstractmethod
from nwmaas.communication.scheduler_request import SchedulerRequestMessage
from typing import Optional

from nwmaas.scheduler.rsa_key_pair import RsaKeyPair


class Job(ABC):
    """
    An abstract interface for a job performed by the MaaS system.
    """

    @property
    @abstractmethod
    def allocation(self) -> Optional[dict]:
        """
        The scheduler allocation for this job.

        Returns
        -------
        Optional[dict]
            The scheduler allocation for this job, or ``None`` if it is queued or otherwise not yet allocated.
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
        self._allocation = None

    @property
    def allocation(self) -> Optional[dict]:
        return self._allocation

    @allocation.setter
    def allocation(self, allocation: dict):
        self._allocation = allocation

    @property
    def cpu_count(self) -> int:
        return self._originating_request.cpus

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


