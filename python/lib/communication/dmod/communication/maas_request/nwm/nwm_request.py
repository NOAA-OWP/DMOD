from typing import ClassVar, List, Optional, Union

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import (
    DataFormat,
    DataRequirement,
)
from ...message import MessageEventType
from ..model_exec_request import ModelExecRequest
from ..model_exec_request_response import ModelExecRequestResponse
from .nwm_exec_request_body import NWMRequestBody


class NWMRequest(ModelExecRequest):

    event_type: ClassVar[MessageEventType] = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""
    # Once more the case senstivity of this model name is called into question
    # note: this is essentially keyed to image_and_domain.yml and the cases must match!
    model_name: ClassVar[str] = "nwm"
    """(:class:`str`) The name of the model to be used"""

    model: NWMRequestBody

    @classmethod
    def factory_init_correct_response_subtype(
        cls, json_obj: dict
    ) -> ModelExecRequestResponse:
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return NWMRequestResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    def __init__(
        self,
        # required in prior version of code
        config_data_id: str = None,
        # optional in prior version of code
        cpu_count: Optional[int] = None,
        allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None,
        **data
    ):
        # assume no need for backwards compatibility
        if "model" in data:
            super().__init__(**data)
            return

        data["model"] = dict()
        nwm_inner_request_body = {"config_data_id": config_data_id}

        if cpu_count is not None:
            nwm_inner_request_body["cpu_count"] = cpu_count

        if allocation_paradigm is not None:
            nwm_inner_request_body["allocation_paradigm"] = allocation_paradigm

        data["model"]["nwm"] = nwm_inner_request_body

        super().__init__(**data)

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        return self.model.data_requirements

    @property
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        return [DataFormat.NWM_OUTPUT]



class NWMRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NWMRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
        - key 'output_data_id' : the 'data_id' of the output dataset for the requested job
        - key 'scheduler_response' : the related :class:`SchedulerRequestResponse`, in serialized dictionary form

    For example:
    {
        'job_id': 1,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': True,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {
                'job_id': 1
            }
        }
    }

    Or:
    {
        'job_id': 0,
        'output_data_id': '00000000-0000-0000-0000-000000000000',
        'scheduler_response': {
            'success': False,
            'reason': 'Testing Stub',
            'message': 'Testing stub',
            'data': {}
        }
    }
    """

    response_to_type = NWMRequest
