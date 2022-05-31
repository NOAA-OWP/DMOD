from .maas_request import ModelExecRequest, ModelExecRequestResponse
from .message import AbstractInitRequest, MessageEventType, Response
from typing import Optional


class SchedulerRequestMessage(AbstractInitRequest):

    _DEFAULT_ALLOCATION_PARADIGM = 'SINGLE_NODE'

    event_type: MessageEventType = MessageEventType.SCHEDULER_REQUEST
    """ :class:`MessageEventType`: the event type for this message implementation """

    @classmethod
    def default_allocation_paradigm_str(cls) -> str:
        """
        Get the default value for the allocation paradigm string.

        Returns
        -------
        str
            The default value for the allocation paradigm string.
        """
        return cls._DEFAULT_ALLOCATION_PARADIGM

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        SchedulerRequestMessage
            A new object of this type instantiated from the deserialize JSON object dictionary, or ``None`` if the
            provided parameter could not be used to instantiated a new object of this type.
        """
        try:
            model_request = ModelExecRequest.factory_init_correct_subtype_from_deserialized_json(json_obj['model_request'])
            if model_request is not None:
                return cls(model_request=model_request,
                           user_id=json_obj['user_id'],
                           # This may be absent to indicate use the value from the backing model request
                           cpus=json_obj['cpus'] if 'cpus' in json_obj else None,
                           # This may be absent to indicate it should be marked "unset" and a default should be used
                           mem=json_obj['mem'] if 'mem' in json_obj else None,
                           allocation_paradigm=json_obj['allocation'])
            else:
                return None
        except:
            return None

    # TODO: may need to generalize the underlying request to support, say, scheduling evaluation jobs
    def __init__(self, model_request: ModelExecRequest, user_id: str, cpus: Optional[int] = None, mem: Optional[int] = None,
                 allocation_paradigm: Optional[str] = None):
        self.model_request = model_request
        self.user_id = user_id
        self._cpus = cpus
        if mem is None:
            self._memory_unset = True
            self._memory = 500000
        else:
            self._memory_unset = False
            self._memory = mem

        if isinstance(allocation_paradigm, str) and allocation_paradigm.strip():
            self.allocation_paradigm: str = allocation_paradigm
        else:
            self.allocation_paradigm: str = self.default_allocation_paradigm_str()

    def __eq__(self, other):
        return self.__class__ == other.__class__ \
               and self.model_request == other.model_request \
               and self.cpus == other.cpus \
               and self.memory == other.memory \
               and self.user_id == other.user_id \
               and self.allocation_paradigm == other.allocation_paradigm

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
        return self.model_request.cpu_count if self._cpus is None else self._cpus

    @property
    def memory(self) -> int:
        """
        The amount of memory, in bytes, requested for the scheduling of this job.

        Returns
        -------
        int
            The amount of memory, in bytes, requested for the scheduling of this job.
        """
        return self._memory

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

    def to_dict(self) -> dict:
        serial = {'model_request': self.model_request.to_dict(), 'user_id': self.user_id,
                  'allocation': self.allocation_paradigm}
        # Don't include this in serial form if property value is sourced from underlying model request
        if self._cpus is not None:
            serial['cpus'] = self._cpus
        # Only including memory value in serial form if it was explicitly set in the first place
        if not self.memory_unset:
            serial['mem'] = self.memory
        return serial


class SchedulerRequestResponse(Response):
    response_to_type = SchedulerRequestMessage

    def __init__(self, job_id: Optional[int] = None, output_data_id: Optional[str] = None, data: dict = None, **kwargs):
        # TODO: how to handle if kwargs has success=True, but job_id value (as param or in data) implies success=False
        key_job_id = ModelExecRequestResponse.get_job_id_key()
        # Create an empty data if not supplied a dict, but only if there is a job_id or output_data_id to insert
        if data is None and (job_id is not None or output_data_id is not None):
            data = {}
        # Prioritize provided job_id over something already in data
        # Note that this condition implies that either a data dict was passed as param, or one just got created above
        if job_id is not None:
            data[key_job_id] = job_id
        # Insert this into dict if present also (again, it being non-None implies data must be a dict object)
        if output_data_id is not None:
            data[ModelExecRequestResponse.get_output_data_id_key()] = output_data_id
        # Ensure that 'success' is being passed as a kwarg to the superclass constructor
        if 'success' not in kwargs:
            kwargs['success'] = data is not None and key_job_id in data and data[key_job_id] > 0
        super(SchedulerRequestResponse, self).__init__(data=data, **kwargs)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.success == other.success and self.job_id == other.job_id

    @property
    def job_id(self):
        if self.success and self.data is not None:
            return self.data[ModelExecRequestResponse.get_job_id_key()]
        else:
            return -1

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
        if self.data is not None and ModelExecRequestResponse.get_output_data_id_key() in self.data:
            return self.data[ModelExecRequestResponse.get_output_data_id_key()]
        else:
            return None
