from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import Field, PrivateAttr, validator, root_validator
from pydantic.fields import ModelField
from warnings import warn

from dmod.core.execution import AllocationParadigm
from dmod.communication import ExternalRequest, ModelExecRequest, NGENRequest, SchedulerRequestMessage
from dmod.core.serializable import Serializable
from dmod.core.meta_data import DataRequirement
from dmod.core.enum import PydanticEnum
from dmod.modeldata.hydrofabric import PartitionConfig
from typing import Any, Callable, ClassVar, Dict, List, Optional, Set, Tuple, Type, TYPE_CHECKING, Union
from typing_extensions import Self
from uuid import UUID
from uuid import uuid4 as uuid_func

from ..resources import ResourceAllocation
from .. import RsaKeyPair

import logging

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny, DictStrAny

# SAFETY: tuple can be used in this context because this sentinel is being used to verify if the data is being
# deserialized from json. Tuple's are not datatypes in json or deserialized json.
JOB_CLASS_SENTINEL = tuple()

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
    STOPPING = (8, True, False)
    """ The step that occurs for a running job after a successful request to be stopped, but before it has stopped. """
    STOPPED = (9, True, False)
    """ The step for a previously running job for which a stopping was request, once the job has actually stopped. """
    COMPLETED = (10, False, False, True)
    """ The step after a running job is finished executing and its resources have been released. """
    CANCELED = (11, True, False, True)
    """ The step occurring after ``STOPPED`` if allocated resources are release, indicated it will not be resumed. """
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
    phase: JobExecPhase = Field(JobExecPhase.UNKNOWN)
    # NOTE: field value will be derived from `phase` field if field is unset or None.
    step: JobExecStep

    @validator("phase", pre=True)
    def _set_default_phase_if_none(cls, value: Optional[JobExecPhase], field: ModelField) -> JobExecPhase:
        if value is None:
            return field.default

        return value

    @validator("step", always=True, pre=True)
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
        return f"{self.job_exec_phase.name}{self._NAME_DELIMITER}{self.job_exec_step.name}"

class Job(Serializable, ABC):
    """
    An abstract interface for a job performed by the MaaS system.

    Instances of job objects are equal as long as they both have the same ::attribute:`job_id`.  Implementations that
    need different a separate domain of ids must create this by controlling job id values in some structural way.

    The hash value of a job is calculated as the hash of it's ::attribute:`job_id`.
    """

    allocation_paradigm: AllocationParadigm
    """The ::class:`AllocationParadigm` type value that was used or should be used to make allocations."""

    allocation_priority: int = 0
    """A score for how this job should be prioritized with respect to allocation."""

    allocations: Optional[Tuple[ResourceAllocation, ...]]
    """The scheduler resource allocations for this job, or ``None`` if it is queued or otherwise not yet allocated."""

    cpu_count: int = Field(gt=0)
    """The number of CPUs for this job."""

    data_requirements: List[DataRequirement] = Field(default_factory=list)
    """List of ::class:`DataRequirement` objects representing all data needed for the job."""

    job_id: str = Field(default_factory=lambda: str(uuid_func()))
    """The unique identifier for this particular job."""

    last_updated: datetime = Field(default_factory=datetime.now)
    """ The last time this objects state was updated."""

    memory_size: int = Field(gt=0)
    """The amount of the memory needed for this job."""

    # TODO: do we need to account for jobs for anything other than model exec?
    model_request: ExternalRequest
    """The underlying configuration for the model execution that is being requested."""

    partition_config: Optional[PartitionConfig]
    """This job's partitioning configuration."""

    rsa_key_pair: Optional[RsaKeyPair]
    """The ::class:`'RsaKeyPair'` for this job's shared SSH RSA keys, or ``None`` if not has been set."""

    status: JobStatus = Field(default_factory=lambda: JobStatus(JobExecPhase.INIT))
    """The ::class:`JobStatus` of this object."""

    job_class: Type[Self] = JOB_CLASS_SENTINEL
    """A type or subtype of ::class:`Self`. This can be provided as a str (e.g. "Job"), but will be coerced into a Type
    object. Class names, not including module namespace, are used when coercing from a str into a Type (i.e. "job.Job"
    is invalid; "Job" is valid). This field is required when factory deserializing from a dictionary. The field defaults
    to the type of Self when programmatically creating an instance. It may be possible to specify a `job_class` during
    programmatic initialization, however that capability is subtype dependent.

    Notably, the `job_class` field of subtypes of Job are also covariant in Self. Meaning, the `job_class` field of a
    subtype S can only be S or a subtype of S. Sibling and super types of S are not allowed.
    """

    @classmethod
    def _subclass_search(cls, t: Union[str, Any]) -> Optional[Type[Self]]:
        if isinstance(t, str):
            # base case
            if t == cls.__name__:
                return cls

            current_level: List[Type[Self]] = cls.__subclasses__()
            # bfs subclass search
            while True:
                next_level: List[Type[Self]] = list()
                for subclass in current_level:
                    if  t == subclass.__name__:
                        return subclass
                    next_level.extend(subclass.__subclasses__())

                # no more levels to explore
                if not next_level:
                    raise ValueError(
                        f"`t`: {t!r} must be a str with value name of Type[{cls.__name__}]. This includes subtypes of `{cls.__name__}`"
                    )

                current_level = next_level

        return None

    @validator("job_class", pre=True, always=True)
    def _validate_job_class(cls: Self, value: Union[str, Type[Self]]) -> Type[Self]:
        # default case. Is unreachable when factory init from json.
        if value is JOB_CLASS_SENTINEL:
            return cls

        subclass = cls._subclass_search(value)
        if subclass is not None:
            return subclass

        if value == cls:
            return value

        if issubclass(value, cls):
            return value

        raise ValueError(
            f"`job_class` field must be a Type[{cls.__name__}]. This includes subtypes of `{cls.__name__}`"
        )

    class Config:
        fields = {
            "partition_config": {"alias": "partitioning"}
        }
        field_serializers = {
            "job_class": lambda cls: cls.__name__,
            "last_updated": lambda self, value: value.strftime(self.get_datetime_str_format())
        }

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional[Self]:
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
        try:
            if "job_class" not in json_obj:
                raise KeyError("missing `job_class` field")

            subclass = cls._subclass_search(json_obj["job_class"])

            if subclass is None:
                raise ValueError("`job_class` field must be provided as a type `str`")

            json_obj["job_class"] = subclass
            return subclass(**json_obj)
        except:
            return None

    def __eq__(self, other: object) -> bool:
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

    def __hash__(self) -> int:
        return hash(self.job_id)

    def __lt__(self, other: "Job") -> bool:
        return self.allocation_priority < other.allocation_priority

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

    @abstractmethod
    def set_allocations(self, allocations: List[ResourceAllocation]):
        pass

    @abstractmethod
    def set_data_requirements(self, data_requirements: List[DataRequirement]):
        pass

    @abstractmethod
    def set_partition_config(self, part_config: PartitionConfig):
        pass

    @abstractmethod
    def set_status(self, status: JobStatus):
        pass

    @abstractmethod
    def set_status_phase(self, phase: JobExecPhase):
        pass

    @abstractmethod
    def set_status_step(self, step: JobExecStep):
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
    def status_phase(self) -> JobExecPhase:
        """
        The ::class:`JobExecPhase` for the ::class:`JobStatus` ::attribute:`status` property of this object.

        Returns
        -------
        JobExecPhase
            The ::class:`JobExecPhase` for the ::class:`JobStatus` ::attribute:`status` property of this object.
        """
        return self.status.job_exec_phase

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

    def _setter_methods(self) -> Dict[str, Callable]:
        """Mapping of attribute name to setter method. This supports backwards functional compatibility."""
        # TODO: remove once migration to setters by down stream users is complete
        return {
            "allocations": self.set_allocations,
            "data_requirements": self.set_data_requirements,
            "partition_config": self.set_partition_config,
            "status": self.set_status,
            # derived properties
            "status_phase": self.set_status_phase,
            "status_step": self.set_status_step,
            }

    def __setattr__(self, name: str, value: Any):
        """
        Use property setter method when available.

        Note, all setter methods should modify their associated property using the instance `__dict__`.
        This ensures that calls to, for example, `set_id` don't raise a warning, while `o.id = "new
        id"` do.

        Example:
            ```
            class SomeJob(Job):
                id: str

                def set_id(self, value: str):
                    self.__dict__["id"] = value
            ```
        """
        if name not in self._setter_methods():
            return super().__setattr__(name, value)

        setter_fn = self._setter_methods()[name]

        message = f"Setting by attribute is deprecated. Use `{self.__class__.__name__}.{setter_fn.__name__}` method instead."
        warn(message, DeprecationWarning)

        setter_fn(value)


class JobImpl(Job):
    """
    Basic implementation of ::class:`Job`

    Job ids are simply the string cast of generated UUID values, stored within the ::attribute:`job_uuid` property.
    """

    # NOTE: more specific ExternalRequest subtype than super class
    model_request: ModelExecRequest

    _worker_data_requirements: Optional[List[List[DataRequirement]]] = PrivateAttr(None)
    _allocation_service_names: Optional[Tuple[str]] = PrivateAttr(None)

    @validator("allocation_paradigm", pre=True)
    def _parse_allocation_paradigm(cls, value: Union[AllocationParadigm, str]) -> Union[str, AllocationParadigm]:
        if isinstance(value, AllocationParadigm):
            return value

        # NOTE: potentially remove in future. There are cases in codebase where kabob case is being used.
        return value.replace("-", "_")

    @validator("status", pre=True)
    def _parse_status(cls, value: Optional[Union[str, JobStatus]], field: ModelField) -> JobStatus:
        if value is None:
            if field.default_factory is None:
                raise RuntimeError("unreachable")
            return field.default_factory()

        if isinstance(value, JobStatus):
            return value

        value = str(value)
        return JobStatus.get_for_name(name=value)

    @validator("last_updated", pre=True)
    def _parse_serialized_last_updated(cls, value: Union[str, datetime]) -> datetime:
        if isinstance(value, datetime):
            return value

        try:
            value = str(value)
            return datetime.strptime(value, cls.get_datetime_str_format())
        except:
            return datetime.now()

    @validator("data_requirements", pre=True)
    def _populate_default_data_requirements(cls, value: Optional[List[DataRequirement]]) -> List[DataRequirement]:
        if value is None:
            return list()
        return value

    @validator("model_request", pre=True)
    def _deserialize_model_request(cls, value: Union[Dict[str, Any], ModelExecRequest]) -> ModelExecRequest:
        if isinstance(value, ModelExecRequest):
            return value

        return ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(value)

    @validator("job_id", pre=True)
    def _validate_job_id(cls, value: Optional[Union[UUID, str]], field: ModelField) -> str:
        if value is None:
            if field.default_factory is None:
                raise RuntimeError("unreachable")
            return field.default_factory()

        if isinstance(value, UUID):
            return str(value)

        return str(UUID(value))

    @root_validator(pre=True)
    def _parse_job_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        job_id = values.get("job_id")
        if job_id is not None:
            return values

        values["job_id"] = cls.parse_serialized_job_id(job_id, **values)
        return values

    # TODO: unit test
    # TODO: consider moving this up to Job or even Serializable

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
        if serialized_value is not None:
            return serialized_value

        key_key = 'key'

        # First, try to obtain a serialized value, if one was not already set
        if key_key in kwargs:
            return kwargs.get(kwargs[key_key])

        return None


    def __init__(self, cpu_count: int, memory_size: int, model_request: ExternalRequest,
                 allocation_paradigm: Union[str, AllocationParadigm], alloc_priority: int = 0, **data):
        # deserialization code path.
        # notice absence of `alloc_priority` parameter in super call.
        if data:
            super().__init__(
                allocation_paradigm=allocation_paradigm,
                cpu_count=cpu_count,
                memory_size=memory_size,
                model_request=model_request,
                **data,
            )
            return

        # backwards compatibility path
        super().__init__(
            allocation_paradigm=allocation_paradigm,
            allocation_priority=alloc_priority,
            cpu_count=cpu_count,
            memory_size=memory_size,
            model_request=model_request,
        )
        self._reset_last_updated()

    def _process_per_worker_data_requirements(self) -> List[List[DataRequirement]]:
        """
        Process the "global" data requirements to per-worker requirements, in the context of allocated resources.

        Returns
        -------
        List[List[DataRequirement]]
            List (indexed analogously to worker allocations) of lists of per-worker data requirements.
        """
        if self.allocations is None:
            return []
        # TODO: implement this properly/more efficiently
        return [list(self.data_requirements) for _ in self.allocations]

    def _reset_last_updated(self):
        self.last_updated = datetime.now()

    def add_allocation(self, allocation: ResourceAllocation):
        """
        Add a resource allocation to this object's list of allocations in ::attribute:`allocations`, initializing it if
        previously set to ``None``.

        Parameters
        ----------
        allocation : ResourceAllocation
            A resource allocation object to add.
        """
        if self.allocations is None:
            self.set_allocations(tuple())
        self.set_allocations((*self.allocations, allocation)) # type: ignore
        self._allocation_service_names = None
        self._reset_last_updated()

    def set_allocation_priority(self, priority: int):
        # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
        # docstring for more detail.
        self.__dict__["allocation_priority"] = priority
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
            service_names: List[str] = []
            # TODO: read this from request metadata
            base_name = "{}-worker".format(self.model_request.get_model_name())
            num_allocations = len(self.allocations)
            for alloc_index in range(num_allocations):
                service_names.append("{}{}_{}".format(base_name, str(alloc_index), str(self.job_id)))
            self._allocation_service_names = tuple(service_names)
        return self._allocation_service_names

    def set_allocations(self, allocations: Union[List[ResourceAllocation], Tuple[ResourceAllocation]]):
        if isinstance(allocations, list):
            # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
            # docstring for more detail.
            self.__dict__["allocations"] = tuple(allocations)
        else:
            # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
            # docstring for more detail.
            self.__dict__["allocations"] = allocations
        self._allocation_service_names = None
        self._reset_last_updated()

    def set_data_requirements(self, data_requirements: List[DataRequirement]):
        # Make sure to reset worker data requirements if this is changed
        self._worker_data_requirements = None
        # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
        # docstring for more detail.
        self.__dict__["data_requirements"] = data_requirements
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

    def set_job_id(self, job_id: Union[str, UUID]):
        job_uuid = job_id if isinstance(job_id, UUID) else UUID(str(job_id))
        job_uuid = str(job_uuid)
        if job_uuid != self.job_id:
            # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
            # docstring for more detail.
            self.__dict__["job_id"] = job_uuid
            self._reset_last_updated()

    def set_partition_config(self, part_config: PartitionConfig):
        # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
        # docstring for more detail.
        self.__dict__["partition_config"] = part_config

    def set_rsa_key_pair(self, key_pair: 'RsaKeyPair'):
        if key_pair != self.rsa_key_pair:
            # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
            # docstring for more detail.
            self.__dict__["rsa_key_pair"] = key_pair
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

    def set_status(self, status: JobStatus):
        if status != self.status:
            # NOTE: set using dict to avoid deprecation warning thrown by `__setattr__`.  See `Job.__setattr__`
            # docstring for more detail.
            self.__dict__["status"] = status
            self._reset_last_updated()

    def set_status_phase(self, phase: JobExecPhase):
        self.set_status(JobStatus(phase=phase, step=phase.default_start_step))

    def set_status_step(self, step: JobExecStep):
        self.set_status(JobStatus(phase=self.status.job_exec_phase, step=step))

    @property
    def worker_data_requirements(self) -> Optional[List[List[DataRequirement]]]:
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

    def _setter_methods(self) -> Dict[str, Callable]:
        return {
            **super()._setter_methods(),
            "allocation_priority": self.set_allocation_priority,
            "job_id": self.set_job_id,
            "rsa_key_pair": self.set_rsa_key_pair,
         }

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note, this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
    ) -> "DictStrAny":
        def add(*fields: str, collection: Union[Set[str], Dict[str, bool]]) -> Union[Set[str], Dict[str, bool]]:
            if isinstance(collection, set):
                collection_copy = {*collection}
                for field in fields:
                    collection_copy.add(field)
                return collection_copy

            elif isinstance(exclude, dict):
                collection_copy = {**collection}
                for field in fields:
                    collection_copy[field] = True
                return collection_copy

            return collection

        exclude = exclude or set()

        # conditionally exclude `allocations` and `partitioning` if allocations is None or is empty
        if self.allocations is None or not len(self.allocations):
            exclude = add("allocations", "partitioning", collection=exclude)

        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        # serialize status as "{PHASE}:{STEP}"
        if "status" not in exclude:
            serial["status"] = self.status.name
        return serial


class RequestedJob(JobImpl):
    """
    An implementation of ::class:`Job` for jobs that were created due to the receipt of a client-side scheduling request
    in the form of a ::class:`SchedulerRequestMessage` object.
    """

    originating_request: SchedulerRequestMessage
    """The original request that resulted in the creation of this job."""

    class Config: # type: ignore
        fields = {
            # exclude `model_request` during serialization
            "model_request": {"exclude": True}
            }

    @classmethod
    def factory_init_from_request(cls, job_request: SchedulerRequestMessage) -> 'RequestedJob':
        """
        Factory init function to create an object from the parameters implied by the job request.

        Parameters
        ----------
        job_request

        Returns
        -------
        RequestedJob
        """
        return cls(job_request=job_request)

    def __init__(self, job_request: SchedulerRequestMessage = None, **data):
        # NOTE: in previous version of code, `model_request` was always a derived field.
        # this allows `model_request` be separately specified
        if "model_request" in data:
            super().__init__(**data)
            return

        if data:
            originating_request = data.get("originating_request")
            if originating_request is None:
                # this should fail, let pydantic handle that.
                super().__init__(**data)
                return

            if isinstance(originating_request, SchedulerRequestMessage):
                # inject
                data["model_request"] = originating_request.model_request
            else:
                data["model_request"] = originating_request.get("model_request")

            super().__init__(**data)
            return

        # NOTE: consider refactoring this into `from_job_request` class method.
        super().__init__(
            cpu_count=job_request.cpus,
            memory_size=job_request.memory,
            model_request=job_request.model_request,
            allocation_paradigm=job_request.allocation_paradigm,
            originating_request=job_request,
            )
        # NOTE: this implicitly resets `last_updated` field
        self.set_data_requirements(job_request.model_request.data_requirements)
