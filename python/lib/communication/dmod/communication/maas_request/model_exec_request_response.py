from abc import ABC
from typing import Any, ClassVar, Dict, Optional, Type, Union
from pydantic import validator

from ..scheduler_request import SchedulerRequestResponse, UNSUCCESSFUL_JOB
from ..message import AbstractInitRequest, InitRequestResponseReason
from .external_request_response import ExternalRequestResponse
from .model_exec_request import ModelExecRequest
from .model_exec_request_response_body import ModelExecRequestResponseBody


class ModelExecRequestResponse(ExternalRequestResponse, ABC):

    response_to_type: ClassVar[Type[AbstractInitRequest]] = ModelExecRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    data: Optional[Union[ModelExecRequestResponseBody, Dict[str, Any]]] = None

    @validator("data", pre=True)
    def _convert_data_field(cls, value: Optional[Union[SchedulerRequestResponse, ModelExecRequestResponseBody, Dict[str, Any]]]) -> Optional[Union[ModelExecRequestResponseBody, Dict[str, Any]]]:
        if value is None:
            return value

        elif isinstance(value, SchedulerRequestResponse):
            return ModelExecRequestResponseBody.from_scheduler_request_response(value)

        return value

    @classmethod
    def get_job_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`job_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`job_id` property.
        """
        return "job_id"

    @classmethod
    def get_output_data_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`output_data_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`output_data_id` property.
        """
        return "output_data_id"

    @classmethod
    def get_scheduler_response_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the 'scheduler_response' value.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the 'scheduler_response' value.
        """
        return "scheduler_response"

    def __init__(
        self,
        scheduler_response: Optional[
            Union[
                SchedulerRequestResponse, ModelExecRequestResponseBody, Dict[str, Any]
            ]
        ] = None,
        **kwargs
    ):
        if scheduler_response is None:
            super().__init__(**kwargs)
            return

        # NOTE: if `scheduler_response` is not None, it is given precedence over "data" that might
        # be present in `kwargs`.
        kwargs["data"] = scheduler_response
        super().__init__(**kwargs)

    @property
    def job_id(self) -> int:
        if isinstance(self.data, ModelExecRequestResponseBody):
            return self.data.job_id

        elif isinstance(self.data, dict) and self.get_job_id_key() in self.data:
            return self.data[self.get_job_id_key()]

        return UNSUCCESSFUL_JOB

    @property
    def output_data_id(self) -> Optional[str]:
        """
        The 'data_id' of the output dataset for the requested job, if the associated request was successful.

        Returns
        -------
        Optional[str]
            The 'data_id' of the output dataset for requested job, if request was successful; otherwise ``None``.
        """
        if isinstance(self.data, ModelExecRequestResponseBody):
            return self.data.output_data_id

        elif isinstance(self.data, dict) and self.get_output_data_id_key() in self.data:
            return self.data[self.get_output_data_id_key()]

        return None

    @property
    def reason_enum(self):
        try:
            return InitRequestResponseReason[self.reason]
        except:
            return InitRequestResponseReason.UNKNOWN
