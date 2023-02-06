from abc import ABC, abstractmethod
from datetime import datetime
from numbers import Number
from pydantic import Field, validator, root_validator
from pydantic.fields import ModelField
from warnings import warn

from dmod.core.execution import AllocationParadigm
from dmod.communication import ExternalRequest, ModelExecRequest, NGENRequest, SchedulerRequestMessage
from dmod.core.serializable import Serializable
from dmod.core.meta_data import DataRequirement
from dmod.core.enum import PydanticEnum
from dmod.modeldata.hydrofabric import PartitionConfig
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING, Union
from uuid import UUID
from uuid import uuid4 as uuid_func

from ..resources import ResourceAllocation

if TYPE_CHECKING:
    from .. import RsaKeyPair

import logging


class JobExecStep(PydanticEnum):
    """
    A component of a JobStatus, representing the particular step within a "phase" encoded within the current status.

    Attributes of assigned tuple correspond to the ::atribute:`uid`, ::attribute:`is_interrupted`, and
    ::attribute:`is_error` properties respectively.
    """
    # TODO: come back and add another property for workflow ordering, separate from uid
    DEFAULT = (0, False, False)
    """ The default starting step. """
    AWAITING_DATA_CHECK = (1, False, False)
    """ The step indicating a check is needed for availability of required data . """
    DATA_UNPROVIDEABLE = (-1, True, True, True)
    """ The error step that occurs if/when it is determined that required data is missing and cannot be obtained. """
    AWAITING_PARTITIONING = (2, False, False)
    """ The step indicating the job is waiting on a partitioning configuration to be created. """
    PARTITIONING_FAILED = (-2, True, True, True)
    """ The error step that occurs if/when generating a partitioning config for a job fails. """
    AWAITING_ALLOCATION = (3, False, False)
    """ The step after data is confirmed as available or obtainable, before resources have been allocated. """
    AWAITING_DATA = (4, False, False)
    """ The step after job is allocated, when any necessary acquiring/processing/preprocessing of data is performed. """
    DATA_FAILURE = (-3, True, True, True)
    """ The step after unexpected error in obtaining or deriving required data that earlier was deemed provideable. """
    AWAITING_SCHEDULING = (5, False, False)
    """ The step after a job has resources allocated and all required data is ready and available. """
    SCHEDULED = (6, False, False)
    """ The step after a job has been scheduled. """
    RUNNING = (7, False, False)
    """ The step after a scheduled job has started running. """
    STOPPED = (8, True, False)
    """ The step that occurs if a running job is stopped deliberately. """
    COMPLETED = (9, False, False, True)
    """ The step after a running job is finished. """
    FAILED = (-10, True, True, True)
    """ The step indicating failure happened that stopped a job after it entered the ``RUNNING`` step. """

    @classmethod
    def get_for_name(cls, name: str) -> Optional['JobExecStep']:
        """
        Parse the given name to its associated enum value, ignoring case and leading/trailing whitespace.

        Parameters
        ----------
        name : str
            The name of the desired enum value.

        Returns
        -------
        JobExecStep
            The associated enum value, or ``None`` if the name could not be parsed to one.
        """
        formatted_name = name.strip().upper()
        for value in cls:
            if formatted_name == value.name.upper():
                return value
        return None

    def __hash__(self):
        return self.uid

    def __init__(self, uid: int, is_interrupted: bool, is_error: bool, completes_phase: bool = False):
        self._uid = uid
        self._is_interrupted = is_interrupted
        self._is_error = is_error
        self._completes_phase = completes_phase

    @property
    def completes_phase(self) -> bool:
        """
        Whether this step is the last step in the process for this applicable job phase.

        This will be ``True`` for steps like ``COMPLETED``, ``FAILED``, ``PARTITIONING_FAILED``, etc., to indicate that
        the current job status phase has no further steps to proceed through.

        Returns
        -------
        bool
            Whether this step is the last step in the process for this applicable job phase.
        """
        return self._completes_phase

    @property
    def is_error(self) -> bool:
        """
        Whether this step reflects that some error has occurred.

        Returns
        -------
        bool
            Whether this step reflects that some error has occurred.
        """
        return self._is_error

    @property
    def is_interrupted(self) -> bool:
        """
        Whether this step reflects that the normal flow of execution was interrupted.

        Note that an interruption may be due to either a deliberate action or some error occurring, which is why this
        must be separated from ::attribute:`is_error`.

        Returns
        -------

        """
        return self._is_interrupted

    @property
    def uid(self) -> int:
        return self._uid


class JobExecPhase(PydanticEnum):
    """
    A component of a JobStatus, representing the high level transition stage at which a status exists.
    """
    INIT = (1, True, JobExecStep.DEFAULT)
    MODEL_EXEC = (2, True, JobExecStep.AWAITING_DATA_CHECK)
    # TODO: this one may no longer be appropriate, depending on how we do output (may need to be an exec step instead)
    # TODO: alternatively for certain job categories, perhaps this is when, e.g., evaluation is done
        # TODO: in that alternative, perhaps jobs of certain categories return to the exec phase (e.g, calibration)
        # TODO: this may or may not also required a different initial step (i.e., not awaiting allocation) and adjusting
        #  logic for when resources are released
    OUTPUT_EXEC = (3, True, JobExecStep.AWAITING_ALLOCATION)
    CLOSED = (4, False, JobExecStep.COMPLETED)
    UNKNOWN = (-1, False, JobExecStep.DEFAULT)

    @classmethod
    def get_for_name(cls, name: str) -> Optional['JobExecPhase']:
        """
        Parse the given name to its associated enum value, ignoring case and leading/trailing whitespace.

        Parameters
        ----------
        name : str
            The name of the desired enum value.

        Returns
        -------
        JobExecPhase
            The associated enum value, or ``None`` if the name could not be parsed to one.
        """
        formatted_name = name.strip().upper()
        for value in cls:
            if formatted_name == value.name.upper():
                return value
        return None

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


class JobStatus(Serializable):
    """
    Representation of a ::class:`Job`'s status as a combination of phase and exec step.
    """
    _NAME_DELIMITER: ClassVar[str] = ':'

    # NOTE: `None` is valid input, default value for field will be used.
    phase: Optional[JobExecPhase] = Field(JobExecPhase.UNKNOWN)
    # NOTE: field value will be derived from `phase` field if field is unset or None.
    step: Optional[JobExecStep]

    @validator("phase", pre=True)
    def _set_default_phase_if_none(cls, value: Optional[JobExecPhase], field: ModelField) -> JobExecPhase:
        if value is None:
            return field.default

        return value

    @validator("step", always=True)
    def _set_default_or_derived_step_if_none(cls, value: Optional[JobExecStep], values: Dict[str, JobExecPhase]) -> JobExecStep:
        # implicit assertion that `phase` key has already been processed by it's validator
        phase: JobExecPhase = values["phase"]

        if value is None:
            return phase.default_start_step

        return value

    @classmethod
    def get_for_name(cls, name: str) -> 'JobStatus':
        """
        Init a status object from the given name, constructed by combining the names of a phase and exec step value.

        Method parses the provided ``name`` into two substrings, expected to be the name of the ::class:`JobExecPhase`
        and ::class:`JobExecStep` that compose the desired status object.  It then initializes the phase and step
        objects from those names, and in turn uses them to initialize and return a status object.

        The expected pattern for parsing is ``\w*<phase_name>::attribute:`_NAME_DELIMITER`<exec_step_name>\w*``.

        Any leading and/or trailing whitespace is trimmed from the provided ``name``.  Also, testing of names for phase
        and step is performed in a case-insensitive manner.

        Parameters
        ----------
        name : str
            A string expected to correspond to the name of a status value, potentially with capitalization differences.

        Returns
        -------
        JobStatus
            The status instance generated from the parsed phase and step, or ``UNKNOWN``.
        """
        if not isinstance(name, str) or len(name) == 0:
            return JobStatus(JobExecPhase.UNKNOWN, JobExecStep.DEFAULT)

        parsed_list = name.split(cls._NAME_DELIMITER)
        if len(parsed_list) != 2:
            return JobStatus(JobExecPhase.UNKNOWN, JobExecStep.DEFAULT)

        phase, step = parsed_list
        return JobStatus(phase=phase, step=step)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, JobStatus):
            return self.job_exec_phase == other.job_exec_phase and self.job_exec_step == other.job_exec_step
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.name)

    def __init__(self, phase: Optional[JobExecPhase], step: Optional[JobExecStep] = None, **data):
        super().__init__(phase=phase, step=step, **data)

    def get_for_new_step(self, step: JobExecStep) -> 'JobStatus':
        """
        Return a (typically) new status object representing a change to this step but the same phase.

        Return a status object representing the same phase of this instance but the provided step.  Typically, this will
        be a newly initialized object.  However, in the case when the given step is equal to this instance's step, the
        method will return this instance, rather than create a duplicate.

        Parameters
        ----------
        step : JobExecStep
            The step for which an updated status object is needed.

        Returns
        -------
        JobStatus
            Status object with this instance's phase and the provided step.
        """
        if self.job_exec_step == step:
            return self
        else:
            return JobStatus(phase=self.job_exec_phase, step=step)

    @property
    def is_active(self) -> bool:
        return self.job_exec_phase.is_active and not self.job_exec_step.completes_phase

    @property
    def is_error(self) -> bool:
        return self.job_exec_step.is_error

    @property
    def is_interrupted(self) -> bool:
        return self.job_exec_step.is_interrupted

    @property
    def job_exec_phase(self) -> JobExecPhase:
        return self.phase

    @property
    def job_exec_step(self) -> JobExecStep:
        return self.step

    @property
    def name(self) -> str:
        return self.job_exec_phase.name + self._NAME_DELIMITER + self.job_exec_step.name


class Job(Serializable, ABC):
    """
    An abstract interface for a job performed by the MaaS system.

    Instances of job objects are equal as long as they both have the same ::attribute:`job_id`.  Implementations that
    need different a separate domain of ids must create this by controlling job id values in some structural way.

    The hash value of a job is calculated as the hash of it's ::attribute:`job_id`.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of the correct subtype based on a JSON object dictionary deserialized from
        received JSON, where this includes a ``job_class`` property containing the name of the appropriate subtype.

        Parameters
        ----------
        json_obj

        Returns
        -------
        A new object of the correct subtype instantiated from the deserialize JSON object dictionary, or ``None`` if
        this cannot be done successfully.
        """
        job_type_key = 'job_class'
        recursive_loop_key = 'base_type_invoked_twice'

        if job_type_key not in json_obj:
            return None

        # Avoid accidental recursive infinite loop by adding an indicator key and bailing if we already see it
        if recursive_loop_key in json_obj:
            return None
        else:
            json_obj[recursive_loop_key] = True

        # Traverse class type tree and get all subtypes of Job
        subclasses = []
        subclasses.extend(cls.__subclasses__())
        traversed_subclasses = set()
        while len(subclasses) > len(traversed_subclasses):
            for s in subclasses:
                if s not in traversed_subclasses:
                    subclasses.extend(s.__subclasses__())
                    traversed_subclasses.add(s)

        for subclass in subclasses:
            subclass_name = subclass.__name__
            if subclass_name == json_obj[job_type_key]:
                json_obj.pop(job_type_key)
                return subclass.factory_init_from_deserialized_json(json_obj)
        return None

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

    def __lt__(self, other):
        return self.allocation_priority < other.allocation_priority

    @property
    @abstractmethod
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The ::class:`AllocationParadigm` type value that was used or should be used to make allocations.

        Returns
        -------
        AllocationParadigm
            The ::class:`AllocationParadigm` type value that was used or should be used to make allocations.
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
    def allocation_service_names(self) -> Optional[Tuple[str]]:
        """
        Return the service names for runtime services created to execute this job, corresponding to the allocations in
        the tuple returned by ::attribute:`allocations`, lazily generating when necessary.

        Implementations must ensure that the generated name values allow for the service name to be deterministically
        mapped back to the related job.

        Returns
        -------
        Optional[Tuple[str]]
            Corresponding service names for runtime services created to execute this job, if this job has received
            allocations.
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
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of ::class:`DataRequirement` objects representing all data needed for the job.

        Returns
        -------
        List[DataRequirement]
            List of ::class:`DataRequirement` objects representing all data needed for the job.
        """
        pass

    @data_requirements.setter
    @abstractmethod
    def data_requirements(self, data_requirements: List[DataRequirement]):
        pass

    @property
    @abstractmethod
    def is_partitionable(self) -> bool:
        """
        Whether this job can have partitioning applied to it.

        Returns
        -------
        bool
            Whether this job can have partitioning applied to it.
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

    # TODO: do we need to account for jobs for anything other than model exec?
    @property
    @abstractmethod
    def model_request(self) -> ExternalRequest:
        """
        Get the underlying configuration for the model execution that is being requested.

        Returns
        -------
        ExternalRequest
            The underlying configuration for the model execution that is being requested.
        """
        pass

    @property
    @abstractmethod
    def partition_config(self) -> Optional[PartitionConfig]:
        """
        Get this job's partitioning configuration.

        Returns
        -------
        PartitionConfig
            This job's partitioning configuration.
        """
        pass

    @partition_config.setter
    @abstractmethod
    def partition_config(self, part_config: PartitionConfig):
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
    def should_release_resources(self) -> bool:
        """
        Whether the job has entered a state where it is appropriate to release resources.

        Returns
        -------
        bool
            Whether the job has entered a state where it is appropriate to release resources.
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

    @property
    @abstractmethod
    def worker_data_requirements(self) -> List[List[DataRequirement]]:
        """
        List of lists of per-worker data requirements, indexed analogously to worker allocations.

        Returns
        -------
        List[List[DataRequirement]]
            List (indexed analogously to worker allocations) of lists of per-worker data requirements.
        """
        pass


class JobImpl(Job):
    """
    Basic implementation of ::class:`Job`

    Job ids are simply the string cast of generated UUID values, stored within the ::attribute:`job_uuid` property.
    """

    @classmethod
    def _parse_serialized_allocation_paradigm(cls, json_obj: dict, key: str):
        paradigm = AllocationParadigm.get_from_name(name=json_obj[key], strict=True) if key in json_obj else None
        if not isinstance(paradigm, AllocationParadigm):
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
    def _parse_serialized_data_requirements(cls, json_obj: dict, key: Optional[str] = None):
        if key is None:
            key = 'data_requirements'

        if key not in json_obj:
            return None

        serial_list = json_obj[key]
        if not isinstance(serial_list, list):
            raise RuntimeError("Invalid format for data requirements list value '{}'".format(str(serial_list)))
        data_req_list = []
        for serial_data_req in serial_list:
            if not isinstance(serial_data_req, dict):
                raise RuntimeError("Invalid format for data requirements value '{}'".format(str(serial_list)))
            data_req = DataRequirement.factory_init_from_deserialized_json(serial_data_req)
            if not isinstance(data_req, DataRequirement):
                msg = "Unable to deserialize `{}` to nested data requirements while deserializing {}"
                raise RuntimeError(msg.format(serial_data_req, cls.__name__))
            data_req_list.append(data_req)
        return data_req_list

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
    def _parse_serialized_partition_config(cls, json_obj: dict, key: Optional[str] = None):
        if key is None:
            key = 'partitioning'
        if key in json_obj:
            return PartitionConfig.factory_init_from_deserialized_json(json_obj[key])
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
                # TODO: log this better.  NJF changed print to logging.warning, anything else needed?
                msg = 'Warning: expected serialized RSA key at {} when deserializing {} object'
                logging.warning(msg.format(key, cls.__name__))
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
        The tuple with parse values of (cpus, memory, paradigm, priority, job_id, rsa_key_pair, status, allocations,
        updated, partitioning) from the provided dictionary.
        """
        int_converter = lambda x: int(x)
        cpus = cls.parse_simple_serialized(json_obj=json_obj, key='cpu_count', expected_type=int,
                                           converter=int_converter)
        memory = cls.parse_simple_serialized(json_obj=json_obj, key='memory_size', expected_type=int,
                                             converter=int_converter)
        paradigm = cls._parse_serialized_allocation_paradigm(json_obj=json_obj, key='allocation_paradigm')
        priority = cls.parse_simple_serialized(json_obj=json_obj, key='allocation_priority', expected_type=int,
                                               converter=int_converter)
        job_id = cls.parse_serialized_job_id(serialized_value=None, json_obj=json_obj, key='job_id')
        rsa_key_pair = cls._parse_serialized_rsa_key_pair(json_obj=json_obj)
        status = cls._parse_serialized_job_status(json_obj=json_obj)
        allocations = cls._parse_serialized_allocations(json_obj=json_obj)
        updated = cls._parse_serialized_last_updated(json_obj=json_obj)
        partitioning = cls._parse_serialized_partition_config(json_obj=json_obj, key='partitioning')
        return cpus, memory, paradigm, priority, job_id, rsa_key_pair, status, allocations, updated, partitioning

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
            cpus, memory, paradigm, priority, job_id, rsa_key_pair, status, allocations, updated, partitioning = \
                cls.deserialize_core_attributes(json_obj)

            if 'model_request' in json_obj:
                model_request = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(json_obj['model_request'])
            else:
                # TODO: add serialize/deserialize support for other situations/requests (also change 'model_request' property name)
                msg = "Type {} can only support deserializing JSON containing a {} under the 'model_request' key"
                raise RuntimeError(msg.format(cls.__name__, ModelExecRequest.__name__))

            obj = cls(cpu_count=cpus, memory_size=memory, model_request=model_request, allocation_paradigm=paradigm,
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
                obj.data_requirements = cls._parse_serialized_data_requirements(json_obj)
            if partitioning is not None:
                obj.partition_config = partitioning

            return obj

        except RuntimeError as e:
            logging.error(e)
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

    def __init__(self, cpu_count: int, memory_size: int, model_request: ExternalRequest,
                 allocation_paradigm: Union[str, AllocationParadigm], alloc_priority: int = 0):
        self._cpu_count = cpu_count
        self._memory_size = memory_size
        self._model_request = model_request
        if isinstance(allocation_paradigm, AllocationParadigm):
            self._allocation_paradigm = allocation_paradigm
        else:
            self._allocation_paradigm = AllocationParadigm.get_from_name(name=allocation_paradigm)
        self._allocation_priority = alloc_priority
        self._job_uuid = uuid_func()
        self._rsa_key_pair = None
        self._status = JobStatus(JobExecPhase.INIT)
        self._allocations = None
        self._data_requirements = None
        self._worker_data_requirements = None
        self._allocation_service_names = None
        self._partition_config = None
        self._reset_last_updated()

    def _process_per_worker_data_requirements(self) -> List[List[DataRequirement]]:
        """
        Process the "global" data requirements to per-worker requirements, in the context of allocated resources.

        Returns
        -------
        List[List[DataRequirement]]
            List (indexed analogously to worker allocations) of lists of per-worker data requirements.
        """
        # TODO: implement this properly/more efficiently
        return [list(self.data_requirements) for a in self.allocations]

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
        self._allocation_service_names = None
        self._reset_last_updated()

    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The ::class:`AllocationParadigm` type value that was used or should be used to make allocations.

        For this type, the value is set as a private attribute during initialization, based on the value of the
        ::attribute:`SchedulerRequestMessage.allocation_paradigm` string property present within the provided
        ::class:`SchedulerRequestMessage` init param.

        Returns
        -------
        AllocationParadigm
            The ::class:`AllocationParadigm` type value that was used or should be used to make allocations.
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
    def allocation_service_names(self) -> Optional[Tuple[str]]:
        """
        Return the service names for runtime services created to execute this job, corresponding to the allocations in
        the tuple returned by ::attribute:`allocations`, lazily generating when necessary.

        For this type, the format of the name values is:

            ``<model_name>-worker<allocation_index>_<job_id>``

        Implementations must ensure that the generated name values allow for the service name to be deterministically
        mapped back to the related job.  For this type, this is done by including the job id within the name.

        Returns
        -------
        Optional[Tuple[str]]
            Corresponding service names for runtime services created to execute this job, if this job has received
            allocations.
        """
        if self._allocation_service_names is None and self.allocations is not None and len(self.allocations) > 0:
            service_names = []
            # TODO: read this from request metadata
            base_name = "{}-worker".format(self.model_request.get_model_name())
            num_allocations = len(self.allocations)
            for alloc_index in range(num_allocations):
                service_names.append("{}{}_{}".format(base_name, str(alloc_index), str(self.job_id)))
            self._allocation_service_names = tuple(service_names)
        return self._allocation_service_names

    @property
    def allocations(self) -> Optional[Tuple[ResourceAllocation]]:
        return None if self._allocations is None else tuple(self._allocations)

    @allocations.setter
    def allocations(self, allocations: Union[List[ResourceAllocation], Tuple[ResourceAllocation]]):
        if isinstance(allocations, tuple):
            self._allocations = list(allocations)
        else:
            self._allocations = allocations
        self._allocation_service_names = None
        self._reset_last_updated()

    @property
    def cpu_count(self) -> int:
        return self._cpu_count

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of ::class:`DataRequirement` objects representing all data needed for the job.

        Returns
        -------
        List[DataRequirement]
            List of ::class:`DataRequirement` objects representing all data needed for the job.
        """
        if self._data_requirements is None:
            self._data_requirements = []
        return self._data_requirements

    @data_requirements.setter
    def data_requirements(self, data_requirements: List[DataRequirement]):
        # Make sure to reset worker data requirements if this is changed
        self._worker_data_requirements = None
        self._data_requirements = data_requirements
        self._reset_last_updated()

    @property
    def is_partitionable(self) -> bool:
        """
        Whether the requirements of the job support partitioning.

        At this time, only NextGen model jobs can be partitioned.

        Returns
        -------
        bool
            Whether the requirements of the job support partitioning.
        """
        return self.model_request is not None and isinstance(self.model_request, NGENRequest)

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
    def model_request(self) -> ExternalRequest:
        """
        Get the underlying configuration for the model execution that is being requested.

        Returns
        -------
        ExternalRequest
            The underlying configuration for the model execution that is being requested.
        """
        return self._model_request

    @property
    def partition_config(self) -> Optional[PartitionConfig]:
        return self._partition_config

    @partition_config.setter
    def partition_config(self, part_config: PartitionConfig):
        self._partition_config = part_config

    @property
    def rsa_key_pair(self) -> Optional['RsaKeyPair']:
        return self._rsa_key_pair

    @rsa_key_pair.setter
    def rsa_key_pair(self, key_pair: 'RsaKeyPair'):
        if key_pair != self._rsa_key_pair:
            self._rsa_key_pair = key_pair
            self._reset_last_updated()

    @property
    def should_release_resources(self) -> bool:
        """
        Whether the job has entered a state where it is appropriate to release resources.

        Returns
        -------
        bool
            Whether the job has entered a state where it is appropriate to release resources.
        """
        # TODO: update to account for JobCategory
        # TODO: confirm that allocations should be maintained for stopped model exec jobs while in output phase
        # TODO: confirm that allocations should be maintained for stopped output jobs while in eval or calibration phase
        return self.status_step == JobExecStep.FAILED or self.status_phase == JobExecPhase.CLOSED

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
        self.status = JobStatus(phase=phase, step=phase.default_start_step)

    @property
    def status_step(self) -> JobExecStep:
        return super().status_step

    @status_step.setter
    def status_step(self, new_step: JobExecStep):
        self.status = JobStatus(phase=self.status.job_exec_phase, step=new_step)

    @property
    def worker_data_requirements(self) -> List[List[DataRequirement]]:
        """
        List of lists of per-worker data requirements, indexed analogously to worker allocations.

        Returns
        -------
        List[List[DataRequirement]]
            List (indexed analogously to worker allocations) of lists of per-worker data requirements.
        """
        if self._worker_data_requirements is None and len(self.data_requirements) > 0 and self.allocations is not None:
            self._worker_data_requirements = self._process_per_worker_data_requirements()
        return self._worker_data_requirements

    def to_dict(self) -> dict:
        """
        Get the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).

        {
            "job_class" : "<class_name>",
            "cpu_count" : 4,
            "memory_size" : 1000,
            "model_request" : {<serialized_maas_request>},
            "allocation_paradigm" : "SINGLE_NODE",
            "allocation_priority" : 0,
            "job_id" : "12345678-1234-5678-1234-567812345678",
            "rsa_key_pair" : {<serialized_representation_of_RsaKeyPair_obj>},
            "status" : INIT:DEFAULT,
            "last_updated" : "2020-07-10 12:05:45",
            "allocations" : [...],
            'data_requirements" : [...],
            "partitioning" : { "partitions": [ ... ] }
        }

        Returns
        -------
        dict
            the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object)
        """
        serial = dict()

        serial['job_class'] = self.__class__.__name__
        serial['cpu_count'] = self.cpu_count
        serial['memory_size'] = self.memory_size

        # TODO: support other scenarios along with deserializing (maybe even eliminate RequestedJob subtype)
        if isinstance(self.model_request, ModelExecRequest):
            request_key = 'model_request'
        else:
            msg = "Type {} can only support serializing to JSON when fulfilled request is a {}"
            raise RuntimeError(msg.format(self.__class__.__name__, ModelExecRequest.__name__))
        serial[request_key] = self.model_request.to_dict()

        if self.allocation_paradigm:
            serial['allocation_paradigm'] = self.allocation_paradigm.name
        serial['allocation_priority'] = self.allocation_priority
        if self.job_id is not None:
            serial['job_id'] = str(self.job_id)
        if self.rsa_key_pair is not None:
            serial['rsa_key_pair'] = self.rsa_key_pair.to_dict()
        serial['status'] = self.status.name
        serial['last_updated'] = self._last_updated.strftime(self.get_datetime_str_format())
        serial['data_requirements'] = []
        for dr in self.data_requirements:
            serial['data_requirements'].append(dr.to_dict())
        if self.allocations is not None and len(self.allocations) > 0:
            serial['allocations'] = []
            for allocation in self.allocations:
                serial['allocations'].append(allocation.to_dict())
            if self.partition_config is not None:
                serial['partitioning'] = self.partition_config.to_dict()

        return serial


class RequestedJob(JobImpl):
    """
    An implementation of ::class:`Job` for jobs that were created due to the receipt of a client-side scheduling request
    in the form of a ::class:`SchedulerRequestMessage` object.
    """

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

        originating_request_key = 'originating_request'

        try:
            cpus, memory, paradigm, priority, job_id, rsa_key_pair, status, allocations, updated, partitioning = \
                cls.deserialize_core_attributes(json_obj)

            if originating_request_key not in json_obj:
                msg = 'Key for originating request ({}) not present when deserialize {} object'
                raise RuntimeError(msg.format(originating_request_key, cls.__name__))
            request = SchedulerRequestMessage.factory_init_from_deserialized_json(json_obj[originating_request_key])
            if request is None:
                msg = 'Invalid serialized scheduler request when deserialize {} object'
                raise RuntimeError(msg.format(cls.__name__))
        except Exception as e:
            logging.error(e)
            return None

        # Create the object initially from the request
        new_obj = cls(job_request=request)

        # Then update its properties based on the deserialized values, as those are considered most correct

        # Use property setter for job id to handle string or UUID
        new_obj.job_id = job_id

        new_obj._cpu_count = cpus
        new_obj._memory_size = memory
        new_obj._allocation_paradigm = paradigm
        new_obj._allocation_priority = priority
        new_obj._rsa_key_pair = rsa_key_pair
        new_obj._status = status
        new_obj._allocations = allocations
        new_obj.data_requirements = cls._parse_serialized_data_requirements(json_obj)
        new_obj._partition_config = partitioning

        # Do last_updated last, as any usage of setters above might cause the value to be maladjusted
        new_obj._last_updated = updated

        return new_obj

    def __init__(self, job_request: SchedulerRequestMessage):
        self._originating_request = job_request
        super().__init__(cpu_count=job_request.cpus, memory_size=job_request.memory,
                         model_request=job_request.model_request,
                         allocation_paradigm=job_request.allocation_paradigm)
        self.data_requirements = self.model_request.data_requirements

    @property
    def model_request(self) -> ExternalRequest:
        """
        Get the underlying configuration for the model execution that is being requested.

        Returns
        -------
        ExternalRequest
            The underlying configuration for the model execution that is being requested.
        """
        return self.originating_request.model_request

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

    def to_dict(self) -> dict:
        """
        Get the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object).

        {
            "job_class" : "<class_name>",
            "cpu_count" : 4,
            "memory_size" : 1000,
            "allocation_paradigm" : "SINGLE_NODE",
            "allocation_priority" : 0,
            "job_id" : "12345678-1234-5678-1234-567812345678",
            "rsa_key_pair" : {<serialized_representation_of_RsaKeyPair_obj>},
            "status" : INIT:DEFAULT,
            "last_updated" : "2020-07-10 12:05:45",
            "allocations" : [...],
            'data_requirements" : [...],
            "partitioning" : { "partitions": [ ... ] },
            "originating_request" : {<serialized_representation_of_originating_message>}
        }

        Returns
        -------
        dict
            the representation of this instance as a dictionary or dictionary-like object (e.g., a JSON object)
        """
        dictionary = super().to_dict()
        # To avoid this being messy, rely on the superclass's implementation and the returned dict, but remove the
        # 'model_request' key/value, since this is contained within the originating serialized scheduler request
        dictionary.pop('model_request')
        dictionary['originating_request'] = self.originating_request.to_dict()
        return dictionary
