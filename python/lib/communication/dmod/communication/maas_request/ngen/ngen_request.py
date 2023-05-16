from typing import ClassVar, Literal, Type
from ...message import AbstractInitRequest
from .abstract_nextgen_request import ExternalAbstractNgenRequest
from ..model_exec_request import ModelExecRequest
from ..model_exec_request_response import ModelExecRequestResponse


class NGENRequest(ModelExecRequest, ExternalAbstractNgenRequest):

    model_name: ClassVar[str] = "ngen"
    """ (::class:`str`) The name of the model to be used. """
    # See comments in DmodJobRequest super class for this field for more details on its purpose.
    job_type: Literal["ngen"] = model_name
    """ The name for the job type being requested. """

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

    def __eq__(self, other: "NGENRequest"):
        try:
            return (
                self.time_range == other.time_range
                and self.hydrofabric_data_id == other.hydrofabric_data_id
                and self.hydrofabric_uid == other.hydrofabric_uid
                and self.realization_config_data_id == other.realization_config_data_id
                and self.bmi_config_data_id == other.bmi_config_data_id
                and self.session_secret == other.session_secret
                and self.cpu_count == other.cpu_count
                and self.partition_cfg_data_id == other.partition_cfg_data_id
                and self.catchments == other.catchments
            )
        except AttributeError:
            return False

    def __hash__(self) -> int:
        hash_str = "{}-{}-{}-{}-{}-{}-{}-{}-{}".format(
            self.time_range.to_json(),
            self.hydrofabric_data_id,
            self.hydrofabric_uid,
            self.realization_config_data_id,
            self.bmi_config_data_id,
            self.session_secret,
            self.cpu_count,
            self.partition_cfg_data_id,
            ",".join(self.catchments),
        )
        return hash(hash_str)

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

    response_to_type: ClassVar[Type[AbstractInitRequest]] = NGENRequest
