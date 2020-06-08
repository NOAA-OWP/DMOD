from abc import ABC, abstractmethod
from datetime import datetime
from dmod.communication.scheduler_request import SchedulerRequestMessage
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from dmod.scheduler.rsa_key_pair import RsaKeyPair
from dmod.scheduler.resources.resource_allocation import ResourceAllocation


class JobAllocationParadigm(Enum):
    """
    Representation of the ways ::class`ResourceAllocation` may be combined to fulfill a total required asset amount
    needed for the allocation of a job.

    The values are as follows:
        FILL_NODES  - obtain allocations of assets by proceeding through resources in some order, getting either the max
                      possible allocation from the current resource or a allocation that fulfills the outstanding need,
                      until the sum of assets among all received allocations is sufficient
        ROUND_ROBIN - obtain allocations of assets from available resource nodes in a round-robin manner
        SINGLE_NODE - require all allocation of assets to be from a single resource/host
    """

    FILL_NODES = 0,
    ROUND_ROBIN = 1,
    SINGLE_NODE = 2

    @classmethod
    def get_default_selection(cls):
        """
        Get the default fallback value select to use in various situation, which is ``SINGLE_NODE``.

        Returns
        -------
        The ``SINGLE_NODE`` value.
        """

    @classmethod
    def get_from_name(cls, name: Optional[str]):
        """
        Get the appropriate value corresponding to the given string value name (trimming whitespace), falling back to
        the default from ::method:`get_default_selection` if an unrecognized or ``None`` value is received.

        Parameters
        ----------
        name: Optional[str]
            The expected string name corresponding to the desired value.

        Returns
        -------
        The desired enum value.
        """
        if name is None or not isinstance(name, str):
            return cls.get_default_selection()
        trimmed_name = name.strip()
        for enum_val in cls:
            if enum_val.name == trimmed_name:
                return enum_val
        return cls.get_default_selection()


class InnerJobStatus:
    """
    An "inner" class intended to only be used inside of ::class:`JobStatus` objects/values to encapsulate details about
    the status while making them a bit more explicit.
    """
    def __eq__(self, other):
        return self.uid == other.uid if isinstance(other, InnerJobStatus) else self.uid == other

    def __init__(self, uid: int, is_active: bool = True, is_error: bool = False, is_interrupted: bool = False):
        self.uid = uid
        self.is_active = is_active
        self.is_error = is_error
        self.is_interrupted = is_interrupted

    def __hash__(self):
        return self.uid


class JobExecStep(Enum):
    """
    A component of a JobStatus, representing the particular step within a "phase" encoded within the current status.
    """
    DEFAULT = (0, False, False),
    AWAITING_ALLOCATION = (1, False, False),
    ALLOCATED = (2, False, False),
    SCHEDULED = (3, False, False),
    RUNNING = (4, False, False),
    STOPPED = (5, True, False)
    COMPLETED = (6, False, False)
    FAILED = (-1, True, True)

    def __hash__(self):
        return self.uid

    def __init__(self, uid: int, is_interrupted: bool, is_error: bool):
        self._uid = uid
        self._is_interrupted = is_interrupted
        self._is_error = is_error

    @property
    def is_error(self) -> bool:
        return self._is_error

    @property
    def is_interrupted(self) -> bool:
        return self._is_interrupted

    @property
    def uid(self) -> int:
        return self._uid


class JobExecPhase(Enum):
    """
    A component of a JobStatus, representing the high level transition stage at which a status exists.
    """
    INIT = (1, True, JobExecStep.DEFAULT),
    MODEL_EXEC = (2, True, JobExecStep.AWAITING_ALLOCATION),
    OUTPUT_EXEC = (3, True, JobExecStep.AWAITING_ALLOCATION),
    CLOSED = (4, False, JobExecStep.COMPLETED),
    UNKNOWN = (-1, False, JobExecStep.DEFAULT)

    def __hash__(self):
        return self.uid

    def __init__(self, uid: int, is_active: bool, default_start: JobExecStep):
        self._uid = uid
        self._is_active = is_active
        self._default_start_step = default_start

    @property
    def default_start_step(self) -> JobExecStep:
        """
        The default first step for this job phase.

        Returns
        -------
        JobExecStep
            The default first step for this job phase.
        """
        return self._default_start_step

    @property
    def is_active(self) -> bool:
        """
        Whether or not this phase and associated JobStatuses are considered "ACTIVE".

        Returns
        -------
        bool
            Whether or not this phase and associated JobStatuses are considered "ACTIVE".
        """
        return self._is_active

    @property
    def uid(self) -> int:
        """
        The unique identifier for this enum value.

        Returns
        -------
        int
            The unique identifier for this enum value.
        """
        return self._uid


class JobStatus(Enum):
    """
    Enumerated values for representing possible ::class:`Job` status states.
    """
    CREATED = (0, JobExecPhase.INIT, JobExecStep.DEFAULT),

    MODEL_EXEC_AWAITING_ALLOCATION = (1, JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION),
    MODEL_EXEC_ALLOCATED = (2, JobExecPhase.MODEL_EXEC, JobExecStep.ALLOCATED),
    MODEL_EXEC_SCHEDULED = (3, JobExecPhase.MODEL_EXEC, JobExecStep.SCHEDULED),
    MODEL_EXEC_RUNNING = (4, JobExecPhase.MODEL_EXEC, JobExecStep.RUNNING),
    # For now, set release_allocations to False for stopped jobs
    # TODO: confirm that allocations should be maintained for stopped model exec jobs
    MODEL_EXEC_STOPPED = (5, JobExecPhase.MODEL_EXEC, JobExecStep.STOPPED, False),
    # For now, set release_allocations to False when model exec is complete (keep allocation for output phase)
    # TODO: confirm that allocations should be carried over from model exec to output exec phase
    MODEL_EXEC_COMPLETED = (6, JobExecPhase.MODEL_EXEC, JobExecStep.COMPLETED, False),
    MODEL_EXEC_FAILED = (-1, JobExecPhase.MODEL_EXEC, JobExecStep.FAILED, True),

    OUTPUT_EXEC_AWAITING_ALLOCATION = (13, JobExecPhase.OUTPUT_EXEC, JobExecStep.AWAITING_ALLOCATION),
    OUTPUT_EXEC_ALLOCATED = (12, JobExecPhase.OUTPUT_EXEC, JobExecStep.ALLOCATED),
    OUTPUT_EXEC_SCHEDULED = (11, JobExecPhase.OUTPUT_EXEC, JobExecStep.SCHEDULED),
    OUTPUT_EXEC_RUNNING = (7, JobExecPhase.OUTPUT_EXEC, JobExecStep.RUNNING),
    # For now, set release_allocations to False for stopped jobs
    # TODO: confirm that allocations should be maintained for stopped output exec jobs
    OUTPUT_EXEC_STOPPED = (8, JobExecPhase.OUTPUT_EXEC, JobExecStep.STOPPED, False),
    OUTPUT_EXEC_COMPLETED = (9, JobExecPhase.OUTPUT_EXEC, JobExecStep.COMPLETED, True),
    OUTPUT_EXEC_FAILED = (-2, JobExecPhase.OUTPUT_EXEC, JobExecStep.FAILED, True),

    CLOSED = (10, JobExecPhase.CLOSED, JobExecStep.COMPLETED, True),
    CLOSED_FAILURE = (-3, JobExecPhase.CLOSED, JobExecStep.FAILED, True),

    # TODO: think through whether it is more appropriate to mark allocations to be release from jobs in unknown status
    UNKNOWN = (-10, JobExecPhase.UNKNOWN, JobExecStep.DEFAULT)

    @staticmethod
    def get_active_statuses() -> List['JobStatus']:
        """
        Return a list of the "active" job status values that indicate a job still needs some action taken or completed.

        Returns
        -------
        List[JobStatus]
            A list of the "active" job status values that indicate a job still needs some action taken or completed.
        """
        actives = []
        for value in JobStatus:
            if value.is_active:
                actives.append(value)
        return actives

    @staticmethod
    def get_for_name(name: str) -> 'JobStatus':
        """
        Get the status enum value corresponding to the given name string, or ``UNKNOWN`` if the name string is not
        recognized.

        Note that any leading and/or trailing whitespace is trimmed before testing against enum values.  Also, testing
        is performed in a case-insensitive manner.

        Parameters
        ----------
        name : str
            A string expected to correspond to the name of a status value, potentially with capitalization differences.

        Returns
        -------
        JobStatus
            The status enum value corresponding to the given name string, or ``UKNOWN`` when not recognized.
        """
        if name is None or not isinstance(name, str) or len(name) == 0:
            return JobStatus.UNKNOWN
        formatted_name = name.lower().strip()
        for value in JobStatus:
            if formatted_name == value.name.lower().strip():
                return value
        return JobStatus.UNKNOWN

    @staticmethod
    def get_for_phase_and_step(phase: JobExecPhase, step: JobExecStep) -> 'JobStatus':
        try:
            for value in JobStatus:
                if value.job_exec_phase == phase and value.job_exec_step == step:
                    return value
        except:
            pass
        return JobStatus.UNKNOWN

    def __eq__(self, other):
        if isinstance(other, JobStatus):
            return self.uid == other.uid
        elif isinstance(other, int):
            return self.uid == other
        elif isinstance(other, float) and other.is_integer():
            return self.uid == int(other)
        elif isinstance(other, str):
            return self == self.get_for_name(other)
        else:
            return False

    def __hash__(self):
        return self.uid

    def __init__(self, uid: int, phase: JobExecPhase, step: JobExecStep, should_release_allocations: bool = False):
        self._uid = uid
        self._phase = phase
        self._step = step
        self._release_allocations = should_release_allocations

    @property
    def is_active(self) -> bool:
        return self.job_exec_phase.is_active

    @property
    def is_error(self) -> bool:
        return self.job_exec_step.is_error

    @property
    def is_interrupted(self) -> bool:
        return self.job_exec_step.is_interrupted

    @property
    def job_exec_phase(self) -> JobExecPhase:
        return self._phase

    @property
    def job_exec_step(self) -> JobExecStep:
        return self._step

    @property
    def should_release_allocations(self) -> bool:
        """
        Whether this status is one at which any held resource allocations should be released.

        Returns
        -------
        bool
            Whether this status is one at which any held resource allocations should be released.
        """
        return self._release_allocations

    @property
    def uid(self) -> int:
        return self._uid


class Job(ABC):
    """
    An abstract interface for a job performed by the MaaS system.
    """

    def __eq__(self, other):
        if isinstance(other, Job):
            return self.job_id == other.job_id
        else:
            return other.__eq__(self)

    @property
    @abstractmethod
    def allocation_paradigm(self) -> JobAllocationParadigm:
        """
        The ::class:`JobAllocationParadigm` type value that was used or should be used to make allocations.

        Returns
        -------
        JobAllocationParadigm
            The ::class:`JobAllocationParadigm` type value that was used or should be used to make allocations.
        """
        pass

    @property
    @abstractmethod
    def allocations(self) -> Optional[List[ResourceAllocation]]:
        """
        The resource allocations that have been allocated for this job.

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
    def last_updated(self) -> datetime:
        """
        The last time this objects state was updated.

        Returns
        -------
        datetime
            The last time this objects state was updated.
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

    @property
    @abstractmethod
    def status(self) -> JobStatus:
        """
        The ::class:`JobStatus` of this object.

        Returns
        -------
        JobStatus
            The ::class:`JobStatus` of this object.
        """
        pass


class RequestedJob(Job):
    """
    An implementation of ::class:`Job` for jobs that were created due to the received of a client request via a
    ::class:`SchedulerRequestMessage` object.
    """

    def __init__(self, job_request: SchedulerRequestMessage):
        self._originating_request = job_request
        self._allocation_paradigm = JobAllocationParadigm.get_from_name(name=job_request.allocation_paradigm)
        self._allocations = None
        self.job_uuid = None
        self._rsa_key_pair = None
        self._status = JobStatus.CREATED
        self._reset_last_updated()

    def _reset_last_updated(self):
        self._last_updated = datetime.now()

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
    def allocation_paradigm(self) -> JobAllocationParadigm:
        """
        The ::class:`JobAllocationParadigm` type value that was used or should be used to make allocations.

        For this type, the value is set as a private attribute during initialization, based on the value of the
        ::attribute:`SchedulerRequestMessage.allocation_paradigm` string property present within the provided
        ::class:`SchedulerRequestMessage` init param.

        Returns
        -------
        JobAllocationParadigm
            The ::class:`JobAllocationParadigm` type value that was used or should be used to make allocations.
        """
        return self._allocation_paradigm

    @property
    def allocations(self) -> Optional[List[ResourceAllocation]]:
        return self._allocations

    @allocations.setter
    def allocations(self, allocations: List[ResourceAllocation]):
        self._allocations = allocations
        self._reset_last_updated()

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
        self._reset_last_updated()

    @property
    def memory_size(self) -> int:
        return self._originating_request.memory

    @property
    def last_updated(self) -> datetime:
        return self._last_updated

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
        self._reset_last_updated()

    @property
    def status(self) -> JobStatus:
        return self._status

    @status.setter
    def status(self, new_status: JobStatus):
        self._status = new_status
        self._reset_last_updated()
