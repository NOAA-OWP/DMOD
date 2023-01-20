from pydantic import validator

from dmod.core.meta_data import TimeRange
from ..model_exec_request_body import ModelExecRequestBody

from typing import List, Literal, Optional


class NGENRequestBody(ModelExecRequestBody):
    name: Literal["ngen"] = "ngen"

    time_range: TimeRange
    hydrofabric_uid: str
    hydrofabric_data_id: str
    bmi_config_data_id: str
    # NOTE: consider pydantic.conlist to constrain this type rather than using validators
    catchments: Optional[List[str]]
    partition_cfg_data_id: Optional[str]

    @validator("catchments")
    def validate_deduplicate_and_sort_catchments(
        cls, value: List[str]
    ) -> Optional[List[str]]:
        if value is None:
            return None

        deduped = set(value)
        return sorted(list(deduped))

    class Config:
        fields = {
            "partition_cfg_data_id": {"alias": "partition_config_data_id"},
        }
