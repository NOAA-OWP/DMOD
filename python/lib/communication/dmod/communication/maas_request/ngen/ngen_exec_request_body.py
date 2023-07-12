from pydantic import Field, validator

from .partial_realization_config import PartialRealizationConfig

from dmod.core.meta_data import TimeRange
from dmod.core.serializable import Serializable

from typing import List, Optional


class NGENRequestBody(Serializable):

    time_range: TimeRange
    hydrofabric_uid: str
    hydrofabric_data_id: str
    realization_config_data_id: str = Field(description="Unique id of the realization config dataset for this request.")
    forcings_data_id: Optional[str] = Field(None, description="Unique id of forcings dataset, if provided.")
    bmi_config_data_id: str
    # NOTE: consider pydantic.conlist to constrain this type rather than using validators
    catchments: Optional[List[str]]
    partial_realization_config: Optional[PartialRealizationConfig] = Field(
        default=None, description="Partial realization config, when supplied by user.")
    partition_cfg_data_id: Optional[str]
    t_route_config_data_id: Optional[str] = Field(None, description="Id of composite source of t-route config.")

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

    def dict(self, **kwargs) -> dict:
        # if exclude is set, ignore this _get_exclude_fields()
        only_if_set = ("catchments", "partition_cfg_data_id", "forcings_data_id", "partial_realization_config",
                       "t_route_config_data_id")
        if kwargs.get("exclude", False) is False:
            kwargs["exclude"] = {f for f in only_if_set if not self.__getattribute__(f)}
        return super().dict(**kwargs)
