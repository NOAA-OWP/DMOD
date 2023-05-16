from typing import ClassVar, List, Literal

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
    """(::class:`MessageEventType`) The type of event for this message. """
    # Once more the case sensitivity of model_name/job_type is called into question
    # note: this is essentially keyed to image_and_domain.yml and the cases must match!
    model_name: ClassVar[str] = "nwm"
    """ (::class:`str`) The name of the model to be used. """
    job_type: Literal["nwm"] = model_name
    """ (::class:`str`) The name of the job type from such a request, which for this type is the model name. """

    request_body: NWMRequestBody

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
        **data
    ):
        # assume no need for backwards compatibility
        if "request_body" in data:
            super().__init__(**data)
        else:
            data["request_body"] = dict()
            nwm_inner_request_body = {"config_data_id": config_data_id}
            data["request_body"]["nwm"] = nwm_inner_request_body
            super().__init__(**data)

    @classmethod
    def get_model_name(cls) -> str:
        # NOTE: overridden b.c. nwm request has nested model field. In the future we should be able
        # to remove this.
        return cls.__fields__["request_body"].type_.__fields__["nwm"].type_.__fields__["name"].default

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        return self.request_body.data_requirements

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
