from abc import ABC, abstractmethod
from datetime import datetime
from dmod.communication import SchedulerRequestMessage
from dmod.communication.serializeable import Serializable
from enum import Enum
from typing import List, Optional, Tuple, TYPE_CHECKING, Union
from uuid import UUID

from ..resources import ResourceAllocation

if TYPE_CHECKING:
    from .. import RsaKeyPair


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

    FILL_NODES = 0
    ROUND_ROBIN = 1
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
    def get_from_name(cls, name: Optional[str], strict: bool = False):
        """
        Get the appropriate value corresponding to the given string value name (trimming whitespace), falling back to
        the default from ::method:`get_default_selection` if an unrecognized or ``None`` value is received.

        Parameters
        ----------
        name: Optional[str]
            The expected string name corresponding to the desired value.

        strict: bool
            Whether strict parsing should be done, in which case unrecognized or invalid ``name`` parameter values will
            return ``None`` instead of the default type.

        Returns
        -------
        The desired enum value, or ``None`` if in strict mode and the ``name`` param does not correspond to an expected
        value.
        """
        if name is None or not isinstance(name, str):
            return None if strict else cls.get_default_selection()

        # Adjust literal name string param value to generalize a little better
        adjusted_name = name.strip().replace('-', '_').upper()

        for enum_val in cls:
            # Do similar generalizing for enum name values
            if enum_val.name.replace('-', '_').upper() == adjusted_name:
                return enum_val

        return None if strict else cls.get_default_selection()


class JobExecStep(Enum):
    """
    A component of a JobStatus, representing the particular step within a "phase" encoded within the current status.
    """
    DEFAULT = (0, False, False)
    AWAITING_ALLOCATION = (1, False, False)
    ALLOCATED = (2, False, False)
    SCHEDULED = (3, False, False)
    RUNNING = (4, False, False)
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
    INIT = (1, True, JobExecStep.DEFAULT)
    MODEL_EXEC = (2, True, JobExecStep.AWAITING_ALLOCATION)
    OUTPUT_EXEC = (3, True, JobExecStep.AWAITING_ALLOCATION)
    CLOSED = (4, False, JobExecStep.COMPLETED)
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
    CREATED = (0, JobExecPhase.INIT, JobExecStep.DEFAULT)

    MODEL_EXEC_AWAITING_ALLOCATION = (1, JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION)
    MODEL_EXEC_ALLOCATED = (2, JobExecPhase.MODEL_EXEC, JobExecStep.ALLOCATED)
    MODEL_EXEC_SCHEDULED = (3, JobExecPhase.MODEL_EXEC, JobExecStep.SCHEDULED)
    MODEL_EXEC_RUNNING = (4, JobExecPhase.MODEL_EXEC, JobExecStep.RUNNING)
    # For now, set release_allocations to False for stopped jobs
    # TODO: confirm that allocations should be maintained for stopped model exec jobs
    MODEL_EXEC_STOPPED = (5, JobExecPhase.MODEL_EXEC, JobExecStep.STOPPED, False)
    # For now, set release_allocations to False when model exec is complete (keep allocation for output phase)
    # TODO: confirm that allocations should be carried over from model exec to output exec phase
    MODEL_EXEC_COMPLETED = (6, JobExecPhase.MODEL_EXEC, JobExecStep.COMPLETED, False)
    MODEL_EXEC_FAILED = (-1, JobExecPhase.MODEL_EXEC, JobExecStep.FAILED, True)

    OUTPUT_EXEC_AWAITING_ALLOCATION = (13, JobExecPhase.OUTPUT_EXEC, JobExecStep.AWAITING_ALLOCATION)
    OUTPUT_EXEC_ALLOCATED = (12, JobExecPhase.OUTPUT_EXEC, JobExecStep.ALLOCATED)
    OUTPUT_EXEC_SCHEDULED = (11, JobExecPhase.OUTPUT_EXEC, JobExecStep.SCHEDULED)
    OUTPUT_EXEC_RUNNING = (7, JobExecPhase.OUTPUT_EXEC, JobExecStep.RUNNING)
    # For now, set release_allocations to False for stopped jobs
    # TODO: confirm that allocations should be maintained for stopped output exec jobs
    OUTPUT_EXEC_STOPPED = (8, JobExecPhase.OUTPUT_EXEC, JobExecStep.STOPPED, False)
    OUTPUT_EXEC_COMPLETED = (9, JobExecPhase.OUTPUT_EXEC, JobExecStep.COMPLETED, True)
    OUTPUT_EXEC_FAILED = (-2, JobExecPhase.OUTPUT_EXEC, JobExecStep.FAILED, True)

    CLOSED = (10, JobExecPhase.CLOSED, JobExecStep.COMPLETED, True)
    CLOSED_FAILURE = (-3, JobExecPhase.CLOSED, JobExecStep.FAILED, True)

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
            The status enum value corresponding to the given name string, or ``UNKNOWN`` when not recognized.
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


class Job(Serializable, ABC):
    """
    An abstract interface for a job performed by the MaaS system.

    Instances of job objects are equal as long as they both have the same ::attribute:`job_id`.  Implementations that
    need different a separate domain of ids must create this by controlling job id values in some structural way.

    The hash value of a job is calculated as the hash of it's ::attribute:`job_id`.
    """

    def __eq__(self, other):
        if other is None:
            return False
        elif isinstance(other, Job):
            return self.job_id == other.job_id
        else:
            # TODO: wanted to do this below, but it isn't safe (if same thing is done in other type, infinite loop)
            #return other.__eq__(self)

            # TODO: for now, treat as false, but look for a way to safely pass to a check on the other without risking
            #  infinite loop (perhaps via some shared interface where that's appropriate)
            return False

    def __hash__(self):
        return hash(self.job_id)

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
    def allocation_priority(self) -> int:
        """
        Get a score for how this job should be prioritized with respect to allocation, with high scores being more
        likely to received allocation.

        Returns
        -------
        int
            A score for how this job should be prioritized with respect to allocation.
        """
        pass

    @property
    @abstractmethod
    def allocations(self) -> Optional[Tuple[ResourceAllocation]]:
        """
        The resource allocations that have been allocated for this job.

        Returns
        -------
        Optional[List[ResourceAllocation]]
            The scheduler resource allocations for this job, or ``None`` if it is queued or otherwise not yet allocated.
        """
        pass

    @allocations.setter
    @abstractmethod
    def allocations(self, allocations: List[ResourceAllocation]):
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
    def rsa_key_pair(self) -> Optional['RsaKeyPair']:
        """
        The ::class:`'RsaKeyPair'` for this job's shared SSH RSA keys.

        Returns
        -------
        Optional['RsaKeyPair']
            The ::class:`'RsaKeyPair'` for this job's shared SSH RSA keys, or ``None`` if not has been set.
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

    @status.setter
    @abstractmethod
    def status(self, status: JobStatus):
        pass

    @property
    def status_phase(self) -> JobExecPhase:
        """
        The ::class:`JobExecPhase` for the ::class:`JobStatus` ::attribute:`status` property of this object.

        Returns
        -------
        JobExecPhase
            The ::class:`JobExecPhase` for the ::class:`JobStatus` ::attribute:`status` property of this object.
        """
        return self.status.job_exec_phase

    @status_phase.setter
    @abstractmethod
    def status_phase(self, phase: JobExecPhase):
        pass

    @property
    def status_step(self) -> JobExecStep:
        """
        The ::class:`JobStageStep` for the ::class:`JobStatus` ::attribute:`status` property of this object.

        Returns
        -------
        JobExecPhase
            The ::class:`JobStageStep` for the ::class:`JobStatus` ::attribute:`status` property of this object.
        """
        return self.status.job_exec_step

    @status_step.setter
    @abstractmethod
    def status_step(self, step: JobExecStep):
        pass


class JobImpl(Job):
    """
    Basic implementation of ::class:`Job`

    Job ids are simply the string cast of generated UUID values, stored within the ::attribute:`job_uuid` property.
    """

    @classmethod
    def _parse_serialized_allocation_paradigm(cls, json_obj: dict, key: str):
        paradigm = JobAllocationParadigm.get_from_name(name=json_obj[key], strict=True) if key in json_obj else None
        if not isinstance(paradigm, JobAllocationParadigm):
            if paradigm is None:
                type_name = 'None'
            else:
                type_name = paradigm.__class__.__name__
            raise RuntimeError(cls._get_invalid_type_message().format(key, str.__name__, type_name))
        return paradigm

    @classmethod
    def _parse_serialized_allocations(cls, json_obj: dict, key: Optional[str] = None):
        if key is None:
            key = 'allocations'

        if key not in json_obj:
            return None

        serial_alloc_list = json_obj[key]
        if not isinstance(serial_alloc_list, list):
            raise RuntimeError("Invalid format for allocations list value '{}'".format(str(serial_alloc_list)))
        allocations = []
        for serial_alloc in serial_alloc_list:
            if not isinstance(serial_alloc, dict):
                raise RuntimeError("Invalid format for allocation value '{}'".format(str(serial_alloc_list)))
            allocation = ResourceAllocation.factory_init_from_dict(serial_alloc)
            if not isinstance(allocation, ResourceAllocation):
                raise RuntimeError(
                    "Unable to deserialize `{}` to resource allocation while deserializing {}".format(
                        str(allocation), cls.__name__))
            allocations.append(allocation)
        return allocations

    @classmethod
    def _parse_serialized_job_status(cls, json_obj: dict, key: Optional[str] = None):
        # Set this to the default value if it is initially None
        if key is None:
            key = 'status'
        status_str = cls.parse_simple_serialized(json_obj=json_obj, key=key, expected_type=str, required_present=False)
        if status_str is None:
            return None
        return JobStatus.get_for_name(name=status_str)

    @classmethod
    def _parse_serialized_last_updated(cls, json_obj: dict, key: Optional[str] = None):
        date_str_converter = lambda date_str: datetime.strptime(date_str, cls.get_datetime_str_format())
        if key is None:
            key = 'last_updated'
        if key in json_obj:
            return cls.parse_simple_serialized(json_obj=json_obj, key=key, expected_type=datetime,
                                               converter=date_str_converter, required_present=False)
        else:
            return None

    @classmethod
    def _parse_serialized_rsa_key_pair(cls, json_obj: dict, key: Optional[str] = None, warn_if_missing: bool = False):
        # Doing this here for now to avoid import errors
        # TODO: find a better way for this
        from .. import RsaKeyPair

        # Set this to the default value if it is initially None
        if key is None:
            # TODO: set somewhere globally
            key = 'rsa_key_pair'
        if key not in json_obj:
            if warn_if_missing:
                # TODO: log this better
                msg = 'Warning: expected serialized RSA key at {} when deserializing {} object'
                print(msg.format(key, cls.__name__))
            return None
        if key not in json_obj or json_obj[key] is None:
            return None
        rsa_key_pair = RsaKeyPair.factory_init_from_deserialized_json(json_obj=json_obj[key])
        if rsa_key_pair is None:
            raise RuntimeError('Could not deserialized child RsaKeyPair when deserializing ' + cls.__name__)
        else:
            return rsa_key_pair

    # TODO: unit test
    # TODO: consider moving this up to Job or even Serializable

    @classmethod
    def deserialize_core_attributes(cls, json_obj: dict):
        """
        Deserialize the core attributes of the basic ::class:`JobImpl` implementation from the provided dictionary and
        return as a tuple.

        Parameters
        ----------
        json_obj

        Returns
        -------
        The tuple with parse values of (cpus, memory, parameters, paradigm, priority, job_id, rsa_key_pair, status,
        allocations, updated) from the provided dictionary.
        """
        int_converter = lambda x: int(x)
        cpus = cls.parse_simple_serialized(json_obj=json_obj, key='cpu_count', expected_type=int,
                                           converter=int_converter)
        memory = cls.parse_simple_serialized(json_obj=json_obj, key='memory_size', expected_type=int,
                                             converter=int_converter)
        parameters = cls.parse_simple_serialized(json_obj=json_obj, key='parameters', expected_type=dict)
        paradigm = cls._parse_serialized_allocation_paradigm(json_obj=json_obj, key='allocation_paradigm')
        priority = cls.parse_simple_serialized(json_obj=json_obj, key='allocation_priority', expected_type=int,
                                               converter=int_converter)
        job_id = cls.parse_serialized_job_id(serialized_value=None, json_obj=json_obj, key='job_id')
        rsa_key_pair = cls._parse_serialized_rsa_key_pair(json_obj=json_obj)
        status = cls._parse_serialized_job_status(json_obj=json_obj)
        allocations = cls._parse_serialized_allocations(json_obj=json_obj)
        updated = cls._parse_serialized_last_updated(json_obj=json_obj)
        return cpus, memory, parameters, paradigm, priority, job_id, rsa_key_pair, status, allocations, updated

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of this type instantiated from the deserialize JSON object dictionary
        """

        try:
            cpus, memory, parameters, paradigm, priority, job_id, rsa_key_pair, status, allocations, updated = \
                cls.deserialize_core_attributes(json_obj)

            obj = cls(cpu_count=cpus, memory_size=memory, parameters=parameters, allocation_paradigm=paradigm,
                      alloc_priority=priority)

            if job_id is not None:
                obj.job_id = job_id
            if rsa_key_pair is not None:
                obj.rsa_key_pair = rsa_key_pair
            if status is not None:
                obj.status = status
            if updated is not None:
                obj._last_updated = updated
            if allocations is not None:
                obj.allocations = allocations
                
            return obj

        except RuntimeError as e:
            # TODO: log the error for e
            return None

    @classmethod
    def parse_serialized_job_id(cls, serialized_value: Optional[str], **kwargs):
        """
        Parse a serialized value for a ``job_id`` property according to the particulars of this types implementation as
        it relates to ``job_id``, either after receiving the value as a parameter or by parsing it from a provided
        dictionary.

        The intent is to provided a means for different implementations to easily inject custom logic for parsing the
        ``job_id`` appropriately when deserializing via ::method:`factory_init_from_deserialized_json`, but supporting
        overriding logic for deserializing the ``job_id``, without having to also override logic for deserializing an
        entire object.

        Implementations should all ensure that if ``None`` is received for the serialized value (and any logic using the
        keyword args cannot obtain a serialize value), that the method returns ``None``.

        In the default implementation, keyword args are examined if the serialized value passed is `None`.  The
        expectation is an optional JSON object/dictionary may be pass, along with the necessary key, from which a serial
        value for the job id can be retrieved.  If the keyword args also cannot be used to obtain a serialized value
        other than ``None``, then the method returns ``None``.

        The default implementation also ensures the serialized value can be used to create a ::class:`UUID` object.  If
        so, that object is returned.  If not, and a non-``None`` serialized value was obtained, a ::class:`RuntimeError`
        is raised.  Note that it also will attempt to cast the serialized value to a string before attempting to use it
        to create a ::class:`UUID` object.

        Parameters
        ----------
        serialized_value : Optional[str]
            Either a job id in serialized string format, or ``None``.
        kwargs
            Optional other keyword args.

        Other Parameters
        ----------
        json_obj : Optional[dict]
            Either a dictionary containing the serialized job id, or ``None``.
        key : Optional[str]
            Either a key value for use with ``json_obj`` to parse the serialized job id value, or ``None``.

        Returns
        -------
        The object for backing job id for the implementation (which in the default is a ::class:`UUID`), or ``None`` if
        the provided parameter was ``None``.

        Raises
        -------
        RuntimeError
            Raised if the parameter does not parse to a UUID.
        """
        key_key = 'key'
        json_obj_key = 'json_obj'

        # First, try to obtain a serialized value, if one was not already set
        if serialized_value is None and kwargs is not None and json_obj_key in kwargs and key_key in kwargs:
            if isinstance(kwargs[json_obj_key], dict) and kwargs[key_key] in kwargs[json_obj_key]:
                try:
                    serialized_value = cls.parse_simple_serialized(json_obj=kwargs[json_obj_key], key=kwargs[key_key],
                                                                   expected_type=str, converter=lambda x: str(x),
                                                                   required_present=False)
                except:
                    # TODO: consider logging this
                    return None
        # Bail here if we don't have a serialized_value to work with
        if serialized_value is None:
            return None
        try:
            return UUID(str(serialized_value))
        except ValueError as e:
            msg = "Failed parsing parameter value `{}` to UUID object: {}".format(str(serialized_value), str(e))
            raise RuntimeError(msg)

    def __init__(self, cpu_count: int, memory_size: int, parameters: dict,
                 allocation_paradigm: Union[str, JobAllocationParadigm], alloc_priority: int = 0):
        self._cpu_count = cpu_count
        self._memory_size = memory_size
        self._parameters = parameters
        if isinstance(allocation_paradigm, JobAllocationParadigm):
            self._allocation_paradigm = allocation_paradigm
        else:
            self._allocation_paradigm = JobAllocationParadigm.get_from_name(name=allocation_paradigm)
        self._allocation_priority = alloc_priority
        self._job_uuid = None
        self._rsa_key_pair = None
        self._status = JobStatus.CREATED
        self._allocations = None
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
            self._allocations = list()
        self._allocations.append(allocation)
        self._reset_last_updated()

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
    def allocation_priority(self) -> int:
        """
        A score for how this job should be prioritized with respect to allocation, with high scores being more likely to
        received allocation.

        Returns
        -------
        int
            A score for how this job should be prioritized with respect to allocation.
        """
        return self._allocation_priority

    @allocation_priority.setter
    def allocation_priority(self, priority: int):
        self._allocation_priority = priority
        self._reset_last_updated()

    @property
    def allocations(self) -> Optional[Tuple[ResourceAllocation]]:
        return None if self._allocations is None else tuple(self._allocations)

    @allocations.setter
    def allocations(self, allocations: Union[List[ResourceAllocation], Tuple[ResourceAllocation]]):
        if isinstance(allocations, tuple):
            self._allocations = list(allocations)
        else:
            self._allocations = allocations
        self._reset_last_updated()

    @property
    def cpu_count(self) -> int:
        return self._cpu_count

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
        return str(self._job_uuid) if isinstance(self._job_uuid, UUID) else None

    @job_id.setter
    def job_id(self, job_id: Union[str, UUID]):
        job_uuid = job_id if isinstance(job_id, UUID) else UUID(str(job_id))
        if job_uuid != self._job_uuid:
            self._job_uuid = job_uuid
            self._reset_last_updated()

    @property
    def memory_size(self) -> int:
        return self._memory_size

    @property
    def last_updated(self) -> datetime:
        return self._last_updated

    @property
    def parameters(self) -> dict:
        return self._parameters

    @property
    def rsa_key_pair(self) -> Optional['RsaKeyPair']:
        return self._rsa_key_pair

    @rsa_key_pair.setter
    def rsa_key_pair(self, key_pair: 'RsaKeyPair'):
        if key_pair != self._rsa_key_pair:
            self._rsa_key_pair = key_pair
            self._reset_last_updated()

    @property
    def status(self) -> JobStatus:
        return self._status

    @status.setter
    def status(self, new_status: JobStatus):
        if new_status != self._status:
            self._status = new_status
            self._reset_last_updated()

    @property
    def status_phase(self) -> JobExecPhase:
        return super().status_phase

    @status_phase.setter
    def status_phase(self, phase: JobExecPhase):
        self.status = JobStatus.get_for_phase_and_step(phase=phase, step=phase.default_start_step)

    @property
    def status_step(self) -> JobExecStep:
        return super().status_step

    @status_step.setter
    def status_step(self, step: JobExecStep):
        self.status = JobStatus.get_for_phase_and_step(phase=self.status.job_exec_phase, step=step)

    def to_dict(self) -> dict:
        """
        Get the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).

        {
            "cpu_count" : 4,
            "memory_size" : 1000,
            "parameters" : {...},
            "allocation_paradigm" : "SINGLE_NODE",
            "allocation_priority" : 0,
            "job_id" : "12345678-1234-5678-1234-567812345678",
            "rsa_key_pair" : {<serialized_representation_of_RsaKeyPair_obj>},
            "status" : CREATED,
            "last_updated" : "2020-07-10 12:05:45",
            "allocations" : [...]
        }

        Returns
        -------
        dict
            the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object)
        """
        serial = dict()

        serial['cpu_count'] = self.cpu_count
        serial['memory_size'] = self.memory_size
        serial['parameters'] = self.parameters
        if self.allocation_paradigm:
            serial['allocation_paradigm'] = self.allocation_paradigm.name
        serial['allocation_priority'] = self.allocation_priority
        if self.job_id is not None:
            serial['job_id'] = str(self.job_id)
        if self.rsa_key_pair is not None:
            serial['rsa_key_pair'] = self.rsa_key_pair.to_dict()
        serial['status'] = self.status.name
        serial['last_updated'] = self._last_updated.strftime(self.get_datetime_str_format())
        if self.allocations is not None and len(self.allocations) > 0:
            serial['allocations'] = []
            for allocation in self.allocations:
                serial['allocations'].append(ResourceAllocation.to_dict(allocation))

        return serial


class RequestedJob(JobImpl):
    """
    An implementation of ::class:`Job` for jobs that were created due to the received of a client request via a
    ::class:`SchedulerRequestMessage` object.
    """

    def __init__(self, job_request: SchedulerRequestMessage):
        self._originating_request = job_request
        super().__init__(cpu_count=job_request.cpus, memory_size=job_request.memory,
                         parameters=job_request.model_request.parameters,
                         allocation_paradigm=job_request.allocation_paradigm)

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
