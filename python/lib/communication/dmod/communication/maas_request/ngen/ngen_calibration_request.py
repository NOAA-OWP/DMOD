from pydantic import PrivateAttr
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction
from typing import ClassVar, List, Literal
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

    job_name: str

    _calibration_config_data_requirement = PrivateAttr(None)

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
    def calibration_config_data_requirement(self) -> DataRequirement:
        """
        A requirement object defining of the ngen-cal configuration needed to execute this request.

        Returns
        -------
        DataRequirement
            A requirement object defining of the ngen-cal configuration needed to execute this request.
        """
        # TODO: #needs_issue - Should all these individual requirement properties (here and elsewhere) be done away with?
        if self._calibration_config_data_requirement is None:
            if self.request_body.ngen_cal_config_data_id is None:
                self.request_body.ngen_cal_config_data_id = "{}-{}".format(self.job_type, self.job_name)
            ngen_cal_restrict = [
                DiscreteRestriction(
                    variable="data_id", values=[self.request_body.ngen_cal_config_data_id]
                )
            ]
            ngen_cal_config_domain = DataDomain(
                data_format=DataFormat.NGEN_CAL_CONFIG,
                discrete_restrictions=ngen_cal_restrict,
            )
            self._calibration_config_data_requirement = DataRequirement(
                domain=ngen_cal_config_domain, is_input=True, category=DataCategory.CONFIG
            )
        return self._calibration_config_data_requirement

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        data_requirements = super().data_requirements
        return [self.calibration_config_data_requirement, *data_requirements]

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
