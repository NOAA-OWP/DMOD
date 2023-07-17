from typing import ClassVar, Literal
from datetime import datetime
from ...message import MessageEventType
from ...maas_request import ModelExecRequestResponse
from .ngen_request import ExternalAbstractNgenRequest
from .ngen_cal_request_estimation_config import NgenCalRequestEstimationConfig


class NgenCalibrationRequest(ExternalAbstractNgenRequest):
    """
    An extension of ::class:`ExternalAbstractNgenRequest` for requesting ngen framework calibration jobs using ngen-cal.
    """
    request_body: NgenCalRequestEstimationConfig

    event_type: ClassVar[MessageEventType] = MessageEventType.CALIBRATION_REQUEST

    # See comments in DmodJobRequest super class for this field for more details on its purpose.
    job_type: Literal["ngen-cal"] = "ngen-cal"
    """ The name for the job type being requested. """

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> 'NgenCalibrationResponse':
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------
        CalibrationJobResponse
            A response of the correct type, with state details from the provided JSON.
        """
        return NgenCalibrationResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    @property
    def evaluation_start(self) -> datetime:
        return self.request_body.time_range.begin

    @property
    def evaluation_stop(self) -> datetime:
        return self.request_body.time_range.end

    @property
    def is_restart(self) -> bool:
        """
        Whether this is a request to restart a previously running job.

        Returns
        -------
        bool
            Whether this is a request to restart a previously running job.
        """
        return self.request_body.start_iteration != 0

    @property
    def use_serial_ngen(self) -> bool:
        return self.request_body.parallel_proc < 2


# TODO: aaraney. this looks unfinished
# class NgenCalibrationResponse(ExternalRequestResponse):
class NgenCalibrationResponse(ModelExecRequestResponse):

    response_to_type = NgenCalibrationRequest
