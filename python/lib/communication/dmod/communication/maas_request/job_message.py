from pydantic import Field, validator
from typing import ClassVar, List, Optional, Type

from ..message import AbstractInitRequest, MessageEventType, Response
from .external_request import ExternalRequest

from dmod.core.enum import PydanticEnum


class JobControlAction(PydanticEnum):
    # Skipping ahead a little here in case we eventually put other things in that make sense to be earlier
    STOP = 10
    """ Stop a job. """

    RELEASE = 11
    """ Release resources for a job that has stopped, completed, or failed. """

    RESTART = 12
    """ Attempt to restart a job that has stopped but still has resource allocations. """

    INVALID = -1


class JobControlRequest(ExternalRequest):
    """
    Message for requesting an operation be performed on an existing job.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.SCHEDULER_REQUEST

    action: JobControlAction = Field(description="The desired control action to be performed.")
    job_id: str = Field(description="The identifier of the job of interest.")

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict):
        return JobControlResponse.factory_init_from_deserialized_json(json_obj)


class JobControlResponse(Response):
    """
    Response subtype for a job control request.
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = JobControlRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response. """

    action: JobControlAction = Field(description="The desired control action to be performed.")
    job_id: str = Field(description="The identifier of the job of interest.")


class JobInfoRequest(ExternalRequest):
    """
    Message for requesting the state of an existing job.
    """

    event_type: ClassVar[MessageEventType] = MessageEventType.SCHEDULER_REQUEST

    job_id: str = Field(description="The identifier of the job of interest.")
    status_only: bool = Field(False, description="Whether only the 'status' attribute of the job need be returned.")

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> "JobInfoResponse":
        return JobInfoResponse.factory_init_from_deserialized_json(json_obj=json_obj)


class JobInfoResponse(Response):
    """
    Response to a :class:`JobInfoRequest` with (if successful) the job or job status data in serialized form.

    The :attr:`data` attribute will, for successful requests, contain the serialized JSON for either a job object or a
    status object.  When unsuccessful, :attr:`data` will be ``None``.`
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = JobInfoRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response. """

    job_id: str = Field(description="The identifier of the job of interest.")
    status_only: bool = Field(False, description="Whether only 'status' attribute of job is returned (when success).")

    @validator("data")
    def _validate_data(cls, value: Optional[dict], values: dict) -> dict:
        """
        Validate the :attr:`data` attribute, in particular in the context of whether the response indicates success.

        Validate the value of the :attr:`data` attribute.  For successful responses, this should be a dictionary object
        with at least one key. For failure responses, the attribute should be set to ``None``.

        Parameters
        ----------
        value: Optional[dict]
            The :attr:`data` value.
        values: dict
            Previous attribute values for the instance.

        Returns
        -------
        dict
            The validated value.

        Raises
        ------
        ValueError
            If either:
                1. the response indicates success and the :attr:`data` `value` is ``None``
                2. the response indicates success and the :attr:`data` `value` is has length of ``0``
                3. the response indicates failure and the :attr:`data` `value` is not ``None``
        TypeError
            If the response indicates success and the :attr:`data` `value` is not a :class:`dict` object.
        """
        if values['success']:
            if value is None:
                raise ValueError(f"{cls.__name__} 'data' field must not be 'None' when successful.")
            elif not isinstance(value, dict):
                raise TypeError(f"{cls.__name__} 'data' field should be dictionary but was {value.__class__.__name__}")
            elif len(value) == 0:
                raise ValueError(f"{cls.__name__} 'data' field must not be empty when successful.")
        elif value is not None:
            raise ValueError(f"{cls.__name__} 'data' field must be 'None' when not successful.")

        return value


class JobListRequest(ExternalRequest):
    """
    Message for requesting a list of existing jobs.
    """
    event_type: ClassVar[MessageEventType] = MessageEventType.SCHEDULER_REQUEST

    only_active: bool = Field(False, description="Whether to return only the ids of active jobs.")

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict):
        return JobListResponse.factory_init_from_deserialized_json(json_obj)


class JobListResponse(Response):
    """
    Response to request for list of jobs, returning (if successful) a list of ids in the data field.

    When successful, the :attr:`data` attribute will be list of string job ids.
    """

    response_to_type: ClassVar[Type[AbstractInitRequest]] = JobListRequest
    """ The type of :class:`AbstractInitRequest` for which this type is the response. """

    only_active: bool = Field(False, description="Whether only the ids of active jobs were returned.")

    @validator("data")
    def _validate_data(cls, value: Optional[List[str]], values: dict) -> List[str]:
        """
        Validate the :attr:`data` attribute, in particular in the context of whether the response indicates success.

        Validate the value of the :attr:`data` attribute.  For successful responses, this should be a list of strings,
        though the list may be empty.  For failure responses, the attribute should be set to ``None``.

        Parameters
        ----------
        value: Optional[List[str]]
            The ``data`` value.
        values: dict
            Previous attribute values for the instance.

        Returns
        -------
        List[str]
            The validated value.

        Raises
        ------
        ValueError
            If either:
                1. the response indicates success and the :attr:`data` `value` is ``None``
                2. the response indicates success and the :attr:`data` `value` has a non-string
                3. the response indicates failure and the :attr:`data` `value` is not ``None``
        TypeError
            If the response indicates success and the :attr:`data` `value` is not a :class:`list` object.
        """
        if values['success']:
            if value is None:
                raise ValueError(f"{cls.__name__} 'data' field must not be 'None' when successful.")
            elif not isinstance(value, list):
                raise TypeError(f"{cls.__name__} 'data' field must be list but was {value.__class__.__name__}")
            elif len(value) > 0 and not all(isinstance(n, str) for n in value):
                raise ValueError(f"{cls.__name__} 'data' field was not list of all strings elements.")

        elif value is not None:
            raise ValueError(f"{cls.__name__} 'data' field must be 'None' when not successful.")

        return value
