from numbers import Number

from typing import Dict, List, Optional, Set, Union

from dmod.core.meta_data import TimeRange
from ...message import MessageEventType
from .abstract_nextgen_request import ExternalAbstractNgenRequest
from ..model_exec_request import ModelExecRequest
from ..model_exec_request_response import ModelExecRequestResponse


class NGENRequest(ModelExecRequest, ExternalAbstractNgenRequest):

    event_type = MessageEventType.MODEL_EXEC_REQUEST
    """(:class:`MessageEventType`) The type of event for this message"""

    model_name = "ngen"  # FIXME case sentitivity
    """(:class:`str`) The name of the model to be used"""

    @classmethod
    def deserialize_for_init(cls, json_obj: dict) -> dict:
        """
        Deserialize a JSON representation to the keyword args needed for use with this type's ::method:`__init__`.

        Note that this type's implementation, as is the case with others, relies on the superclass's implementation for
        a large part of the logic.  However, since the serialized format of this type is a little shifted compared to
        the superclass's (see docstring for this instance's ::method:`to_dict`), this function copies the received JSON,
        flattens this copy, and sends this flattened copy to the superclass call.

        Parameters
        ----------
        json_obj: dict
            A serialized JSON representation of an instance.

        Returns
        -------
        dict
            A dictionary containing the keyword args (both required and any contained optional) necessary for
            initializing an instance, with the values deserialized from the received JSON.

        See Also
        -------
        to_dict
        """
        # Because of the weird formatting of the JSON, have to manipulate things before passing to the superclass method
        flattened_copy = json_obj.copy()
        model_part = flattened_copy.pop("model")
        flattened_copy.update(model_part)

        return super().deserialize_for_init(flattened_copy)

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
        return NGENRequestResponse.factory_init_from_deserialized_json(
            json_obj=json_obj
        )

    def __init__(self, *args, **kwargs):
        """
        Initialize an instance.

        Keyword Args
        ----------
        time_range : TimeRange
            A definition of the time range for the requested model execution.
        hydrofabric_uid : str
            The unique ID of the applicable hydrofabric for modeling, which provides the outermost geospatial domain.
        hydrofabric_data_id : str
            A data identifier for the hydrofabric, for distinguishing between different hydrofabrics that cover the same
            set of catchments and nexuses (i.e., the same sets of catchment and nexus ids).
        catchments : Optional[Union[Set[str], List[str]]]
            An optional collection of the catchment ids to narrow the geospatial domain, where the default of ``None``
            or an empty collection implies all catchments in the hydrofabric.
        bmi_cfg_data_id : Optional[str]
            The optioanl BMI init config ``data_id`` index, for identifying the particular BMI init config datasets
            applicable to this request.
        config_data_id : str
            The config data id index, for identifying the particular configuration datasets applicable to this request.
        session_secret : str
            The session secret for the right session when communicating with the MaaS request handler
        """
        super().__init__(*args, **kwargs)

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Converts the request to a dictionary that may be passed to web requests

        Will look like:

        {
            'model': {
                'name': 'ngen',
                'allocation_paradigm': <allocation_paradigm_str>,
                'cpu_count': <cpu_count>,
                'time_range': { <serialized_time_range_object> },
                'hydrofabric_data_id': 'hy-data-id-val',
                'hydrofabric_uid': 'hy-uid-val',
                'config_data_id': 'config-data-id-val',
                'bmi_config_data_id': 'bmi-config-data-id',
                'partition_config_data_id': 'partition_config_data_id',
                ['catchments': { <serialized_catchment_discrete_restriction_object> },]
                'version': 4.0
            },
            'session_secret': 'secret-string-val'
        }

        As a reminder, the ``catchments`` item may be absent, which implies the object does not have a specified list of
        catchment ids.

        Returns
        -------
        Dict[str, Union[str, Number, dict, list]]
            A dictionary containing all the data in such a way that it may be used by a web request
        """
        model = super().to_dict()
        model["name"] = self.get_model_name()
        # Move this to outer layer
        session_secret_val = model.pop("session_secret")
        return {"model": model, "session_secret": session_secret_val}

    @property
    def use_serial_ngen(self) -> bool:
        """
        Whether this request specifies to use the variant of the Nextgen framework compiled for serial execution.

        Nextgen may be compiled to execute either serially or using parallelization.  DMOD and its Nextgen job workers
        can now support either.  This property indicates whether this request indicates that serially execution should
        be used.

        In the current implementation, this property is ``True`` IFF the request required a CPU count of exactly ``1``.

        Returns
        -------
        bool
            Whether this request specifies serial Nextgen execution for the job.

        See Also
        -------
        use_parallel_ngen
        """
        return self.cpu_count == 1


class NGENRequestResponse(ModelExecRequestResponse):
    """
    A response to a :class:`NGENRequest`.

    Note that, when not ``None``, the :attr:`data` value will be a dictionary with the following format:
        - key 'job_id' : the appropriate job id value in response to the request
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

    response_to_type = NGENRequest
