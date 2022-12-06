from numbers import Number
from dmod.core.meta_data import TimeRange
from typing import Dict, List, Optional, Set, Tuple, Union

from ...message import MessageEventType
from ...maas_request import ExternalRequestResponse
from .ngen_request import NGENRequest


class NgenCalibrationRequest(NGENRequest):
    """
    An extension of ::class:`NGENRequest` for requesting ngen-cal calibration jobs.
    """

    event_type: MessageEventType = MessageEventType.CALIBRATION_REQUEST
    model_name = 'ngen-cal' #FIXME case sentitivity

    # TODO: probably will need to re-examine this
    _DEFAULT_CPU_COUNT = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    _KEY_CAL_STRATEGY_ALGO = 'strategy_algorithm'
    _KEY_CAL_STRATEGY_OBJ_FUNC = 'strategy_objective_function'
    _KEY_CAL_STRATEGY_TYPE = 'strategy_type'
    _KEY_EVALUTATION_TIME = 'evaluation_time_range'
    _KEY_IS_OBJ_FUNC_MIN = 'is_obj_func_min'
    _KEY_IS_RESTART = 'is_restart'
    _KEY_ITERATIONS = 'iterations'
    _KEY_JOB_NAME = 'job_name'
    _KEY_MODEL_CAL_PARAMS = 'model_cal_params'
    _KEY_MODEL_STRATEGY = 'model_strategy'

    @classmethod
    def _additional_deserialized_args(cls, json_obj: dict) -> dict:
        """
        Parse any additional, (sub)class-specific deserialization params.
                
        Parameters
        ----------
        json_obj

        Returns
        -------
        dict
        """
        additional_kw_args = dict()
        additional_kw_args['cal_strategy_algorithm'] = json_obj[cls._KEY_CAL_STRATEGY_ALGO]
        additional_kw_args['cal_strategy_objective_func'] = json_obj[cls._KEY_CAL_STRATEGY_OBJ_FUNC]
        additional_kw_args['cal_strategy_type'] = json_obj[cls._KEY_CAL_STRATEGY_TYPE]
        additional_kw_args['evaluation_time_range'] = TimeRange.factory_init_from_deserialized_json(json_obj[cls._KEY_EVALUTATION_TIME])
        additional_kw_args['is_objective_func_minimized'] = json_obj[cls._KEY_IS_OBJ_FUNC_MIN]
        additional_kw_args['is_restart'] = json_obj[cls._KEY_IS_RESTART]
        additional_kw_args['iterations'] = json_obj[cls._KEY_ITERATIONS]
        additional_kw_args['job_name'] = json_obj[cls._KEY_JOB_NAME]
        additional_kw_args['model_cal_params'] = json_obj[cls._KEY_MODEL_CAL_PARAMS]
        additional_kw_args['model_strategy'] = json_obj[cls._KEY_MODEL_STRATEGY]
        return additional_kw_args

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

    def __init__(self, evaluation_time_range: TimeRange, model_cal_params: Dict[str, Tuple[float, float, float]],
                 iterations: int, cal_strategy_type: str = 'estimation', cal_strategy_algorithm: str = 'dds',
                 cal_strategy_objective_func: str = 'nnse', is_objective_func_minimized: bool = True,
                 model_strategy: str = 'uniform', job_name: Optional[str] = None, is_restart: bool = False, *args,
                 **kwargs):
        """
        Initialize an instance.

        Parameters
        ----------
        evaluation_time_range : TimeRange
            The time range for calibration for use within the ngen-cal config for the job.
        model_cal_params : Dict[str, Tuple[float, float, float]]
            A collection of the calibratable params, keyed by name, with a tuple of the min, max, and initial values.
        iterations : int
            The total number of search iterations to run.
        cal_strategy_type : str
            The ngen-cal general strategy type for the calibration config (default: ``estimation``).
        cal_strategy_algorithm : str
            Calibration strategy algorithm ("dds" by default).
        cal_strategy_objective_func : str
            The standard name ("kling_gupta", "nnse", "custom", "single_peak", "volume") or full ngen_cal package module
            name for the objective function to use ("nnse" by default).
        is_objective_func_minimized : bool
            Whether to minimize the objective function (implies maximize when ``False``; default value: ``True``).
        model_strategy : str
            The ngen-cal model calibration strategy; one of :
                'uniform' : Each catchment shares the same parameter space, evaluates at one observable nexus
                'independent' : Each catchment upstream of observable nexus gets its own permutated parameter space,
                                evaluates at one observable nexus
                'explicit' : Only calibrates basins in the realization_config with a "calibration" definition and an
                observable nexus
        job_name : Optional[str]
            Optional job name for the calibration run, which can be used by ngen-cal when generating files.
        is_restart : bool
            Whether this represents restarting a previous job; ``False`` by default.

        Keyword Args
        -----------
        time_range : TimeRange
            A definition of the time range for the configured execution of the ngen framework.
        hydrofabric_uid : str
            The unique ID of the applicable hydrofabric for modeling, which provides the outermost geospatial domain.
        hydrofabric_data_id : str
            A data identifier for the hydrofabric, for distinguishing between different hydrofabrics that cover the same
            set of catchments and nexuses (i.e., the same sets of catchment and nexus ids).
        catchments : Optional[Union[Set[str], List[str]]]
            An optional collection of the catchment ids to narrow the geospatial domain, where the default of ``None``
            or an empty collection implies all catchments in the hydrofabric.
        bmi_cfg_data_id : Optional[str]
            The optional BMI init config ``data_id`` index, for identifying the particular BMI init config datasets
            applicable to this request.
        config_data_id : str
            The config data id index, for identifying the particular configuration datasets applicable to this request.
        session_secret : str
            The session secret for the right session when communicating with the MaaS request handler
        """
        super(NgenCalibrationRequest, self).__init__(*args, **kwargs)
        self.evaluation_time_range = evaluation_time_range
        self.model_cal_params = model_cal_params
        self.iterations = iterations
        self.cal_strategy_type = cal_strategy_type
        self.cal_strategy_algorithm = cal_strategy_algorithm
        self.cal_strategy_objective_function = cal_strategy_objective_func
        self.is_objective_func_minimized = is_objective_func_minimized
        self.model_strategy = model_strategy
        self.job_name = job_name

        self.is_restart = is_restart

        # TODO: may need to modify this to have (realization) config dataset start empty (at least optionally) and apply

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = super(NgenCalibrationRequest, self).to_dict()
        serial[self._KEY_EVALUTATION_TIME] = self.evaluation_time_range.to_dict()
        serial[self._KEY_MODEL_CAL_PARAMS] = self.model_cal_params
        serial[self._KEY_CAL_STRATEGY_TYPE] = self.cal_strategy_type
        serial[self._KEY_CAL_STRATEGY_ALGO] = self.cal_strategy_algorithm
        serial[self._KEY_CAL_STRATEGY_OBJ_FUNC] = self.cal_strategy_objective_function
        serial[self._KEY_IS_OBJ_FUNC_MIN] = self.is_objective_func_minimized
        serial[self._KEY_ITERATIONS] = self.iterations
        serial[self._KEY_JOB_NAME] = self.job_name
        serial[self._KEY_MODEL_STRATEGY] = self.model_strategy
        serial[self._KEY_IS_RESTART] = self.is_restart
        return serial


class NgenCalibrationResponse(ExternalRequestResponse):
    response_to_type = NgenCalibrationRequest
