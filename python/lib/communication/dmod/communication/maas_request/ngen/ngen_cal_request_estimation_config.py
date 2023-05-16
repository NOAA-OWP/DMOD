from pydantic import Field
from typing import Any, Dict, List
from .ngen_exec_request_body import NGENRequestBody


class NgenCalRequestEstimationConfig(NGENRequestBody):

    parallel_proc: int = Field(1, gt=0, description="Number of parallel ngen processes for ngen-cal to use.")
    # TODO: #needs_issue - Add validator for supported values
    algorithm: str = Field("dds", description="The calibration optimization algorithm.")
    objective_function: str = Field(description="The calibration objective function.")
    iterations: int = Field(gt=0, description="The number of ngen iterations to run through during calibration.")
    # TODO: #needs_issue - Add validator to ensure this isn't larger than the total number of iterations
    start_iteration: int = Field(1, gt=0, description="The starting iteration, which is greater than 1 for restarts.")
    # TODO: #needs_issue - Add validator for supported values (independent, uniform, explicit)
    # TODO: #needs_issue - Add validator for adjusting case when needed
    model_strategy: str = Field(description="The particular ngen calibration strategy to use.")
    model_params: Dict[str, List[Dict[str, Any]]]
    ngen_cal_config_data_id: str
