from abc import ABC

from typing import Optional

from ..message import InitRequestResponseReason
from .external_request_response import ExternalRequestResponse
from .model_exec_request import ModelExecRequest


class ModelExecRequestResponse(ExternalRequestResponse, ABC):

    _data_dict_key_job_id = "job_id"
    _data_dict_key_output_data_id = "output_data_id"
    _data_dict_key_scheduler_response = "scheduler_response"
    response_to_type = ModelExecRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response"""

    @classmethod
    def _convert_scheduler_response_to_data_attribute(cls, scheduler_response=None):
        if scheduler_response is None:
            return None
        elif isinstance(scheduler_response, dict) and len(scheduler_response) == 0:
            return {}
        elif isinstance(scheduler_response, dict):
            return scheduler_response
        else:
            return {
                cls._data_dict_key_job_id: scheduler_response.job_id,
                cls._data_dict_key_output_data_id: scheduler_response.output_data_id,
                cls._data_dict_key_scheduler_response: scheduler_response.to_dict(),
            }

    @classmethod
    def get_job_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`job_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`job_id` property.
        """
        return str(cls._data_dict_key_job_id)

    @classmethod
    def get_output_data_id_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the ::attribute:`output_data_id` property.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the ::attribute:`output_data_id` property.
        """
        return str(cls._data_dict_key_output_data_id)

    @classmethod
    def get_scheduler_response_key(cls) -> str:
        """
        Get the serialization dictionary key for the field containing the 'scheduler_response' value.

        Returns
        -------
        str
            Serialization dictionary key for the field containing the 'scheduler_response' value.
        """
        return str(cls._data_dict_key_scheduler_response)

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        """
        Factory create a new instance of this type based on a JSON object dictionary deserialized from received JSON.

        Parameters
        ----------
        json_obj

        Returns
        -------
        response_obj : Response
            A new object of this type instantiated from the deserialize JSON object dictionary, or none if the provided
            parameter could not be used to instantiated a new object.

        See Also
        -------
        _factory_init_data_attribute
        """
        try:
            return cls(
                success=json_obj["success"],
                reason=json_obj["reason"],
                message=json_obj["message"],
                scheduler_response=json_obj["data"],
            )
        except Exception as e:
            return None

    def __init__(self, scheduler_response=None, *args, **kwargs):
        data = self._convert_scheduler_response_to_data_attribute(scheduler_response)
        if data is not None:
            kwargs["data"] = data
        super().__init__(*args, **kwargs)

    @property
    def job_id(self):
        if (
            not isinstance(self.data, dict)
            or self._data_dict_key_job_id not in self.data
        ):
            return -1
        else:
            return self.data[self._data_dict_key_job_id]

    @property
    def output_data_id(self) -> Optional[str]:
        """
        The 'data_id' of the output dataset for the requested job, if the associated request was successful.

        Returns
        -------
        Optional[str]
            The 'data_id' of the output dataset for requested job, if request was successful; otherwise ``None``.
        """
        if (
            not isinstance(self.data, dict)
            or self._data_dict_key_output_data_id not in self.data
        ):
            return None
        else:
            return self.data[self._data_dict_key_output_data_id]

    @property
    def reason_enum(self):
        try:
            return InitRequestResponseReason[self.reason]
        except:
            return InitRequestResponseReason.UNKNOWN
