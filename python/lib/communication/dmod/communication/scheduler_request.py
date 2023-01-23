from dmod.core.execution import AllocationParadigm
from .maas_request import ModelExecRequest
from .message import AbstractInitRequest, MessageEventType, Response
from .scheduler_request_response_body import SchedulerRequestResponseBody, UNSUCCESSFUL_JOB
from pydantic import Field, PrivateAttr, validator
from typing import ClassVar, Dict, Optional, Type, Union

class SchedulerRequestMessage(AbstractInitRequest):

    event_type: ClassVar[MessageEventType] = MessageEventType.SCHEDULER_REQUEST
    """ :class:`MessageEventType`: the event type for this message implementation """

    model_request: ModelExecRequest = Field(description="The underlying request for a job to be scheduled.")
    user_id: str = Field(description="The associated user id for this scheduling request.")
    memory: int = Field(500_000, description="The amount of memory, in bytes, requested for the scheduling of this job.")
    cpus_: Optional[int] = Field(description="The number of processors requested for the scheduling of this job.")
    allocation_paradigm_: Optional[AllocationParadigm]

    _memory_unset: bool = PrivateAttr()

    @validator("model_request", pre=True)
    def _factory_init_model_request(cls, value):
        if isinstance(value, ModelExecRequest):
            return value
        return ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(value)

    class Config:
        fields = {
            "memory": {"alias": "mem"},
            "cpus_": {"alias": "cpus"},
            "allocation_paradigm_": {"alias": "allocation_paradigm"},
        }

    @classmethod
    def default_allocation_paradigm_str(cls) -> str:
        """
        Get the default value for the allocation paradigm string.

        This is based directly on ::method:`AllocationParadigm.get_default_selection`.

        Returns
        -------
        str
            The default value for the allocation paradigm string.

        See Also
        -------
        AllocationParadigm.get_default_selection
        """
        return AllocationParadigm.get_default_selection().name

    # TODO: may need to generalize the underlying request to support, say, scheduling evaluation jobs
    def __init__(
        self,
        model_request: ModelExecRequest,
        user_id: str,
        cpus: Optional[int] = None,
        mem: Optional[int] = None,
        allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None,
        **data
    ):
        super().__init__(
            model_request=model_request,
            user_id=user_id,
            cpus=cpus or data.pop("cpus_", None),
            memory=mem or data.pop("memory", None) or self.__fields__["memory"].default,
            allocation_paradigm=allocation_paradigm or data.pop("allocation_paradigm_", None),
            **data
        )
        if mem is None:
            self._memory_unset = True
        else:
            self._memory_unset = False

    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The allocation paradigm requested for the job to be scheduled.

        Returns
        -------
        AllocationParadigm
            The allocation paradigm requested for the job to be scheduled.
        """
        if self.allocation_paradigm_ is None:
            return self.model_request.allocation_paradigm
        else:
            return self.allocation_paradigm_

    @property
    def cpus(self) -> int:
        """
        The number of processors requested for the scheduling of this job.

        If not overridden, this falls back to the analogous CPU count property of the underlying
        ::class:`ModelExecRequest`.

        Returns
        -------
        int
            The number of processors requested for the scheduling of this job.
        """
        return self.model_request.cpu_count if self.cpus_ is None else self.cpus_

    @property
    def memory_unset(self) -> bool:
        """
        Whether a default amount for job scheduling memory amount was used, because no explicit amount was provided.

        Returns
        -------
        bool
            Whether a default amount for job scheduling memory amount was used, and no explicit amount was provided.
        """
        return self._memory_unset

    @property
    def nested_event(self) -> MessageEventType:
        """
        The nested event type of the request this message is trying to have scheduled.

        Returns
        -------
        MessageEventType
            The nested event type of the request this message is trying to have scheduled.
        """
        return self.model_request.get_message_event_type()

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Union[str, int]]:
        # Only including memory value in serial form if it was explicitly set in the first place
        if self.memory_unset:
            exclude = {"memory"} if exclude is None else {"memory", *exclude}

        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

class SchedulerRequestResponse(Response):

    response_to_type: ClassVar[Type[AbstractInitRequest]] = SchedulerRequestMessage

    data: Union[SchedulerRequestResponseBody, Dict[None, None], None]

    def __init__(self, job_id: Optional[int] = None, output_data_id: Optional[str] = None, data: dict = None, **kwargs):
        # TODO: how to handle if kwargs has success=True, but job_id value (as param or in data) implies success=False

        # Create an empty data if not supplied a dict, but only if there is a job_id or output_data_id to insert
        if data is None and (job_id is not None or output_data_id is not None):
            data = {}

        # Prioritize provided job_id over something already in data
        # Note that this condition implies that either a data dict was passed as param, or one just got created above
        if job_id is not None:
            data["job_id"] = job_id

        # Insert this into dict if present also (again, it being non-None implies data must be a dict object)
        if output_data_id is not None:
            data["output_data_id"] = output_data_id

        # Ensure that 'success' is being passed as a kwarg to the superclass constructor
        if "success" not in kwargs:
            kwargs["success"] = data is not None and "job_id" in data and data["job_id"] > 0

        super().__init__(data=data, **kwargs)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.success == other.success and self.job_id == other.job_id

    @property
    def job_id(self) -> int:
        if self.success:
            return self.data.job_id
        else:
            return UNSUCCESSFUL_JOB

    # TODO: make sure this value gets included in the data dict
    @property
    def output_data_id(self) -> Optional[str]:
        """
        The 'data_id' of the output dataset for the requested job, if known.

        Returns
        -------
        Optional[str]
            The 'data_id' of the output dataset for requested job, or ``None`` if not known.
        """
        return self.data.output_data_id

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> "SchedulerRequestResponse":
        # TODO: remove in future. necessary for backwards compatibility
        if isinstance(json_obj, SchedulerRequestResponse):
            return json_obj

        return super().factory_init_from_deserialized_json(json_obj=json_obj)

    # NOTE: legacy support. previously this class was treated as a dictionary
    def __contains__(self, element: str) -> bool:
        return element in self.__dict__

    # NOTE: legacy support. previously this class was treated as a dictionary
    def __getitem__(self, item: str):
        return self.__dict__[item]

