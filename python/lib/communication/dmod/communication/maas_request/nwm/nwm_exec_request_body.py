from pydantic import root_validator

from dmod.core.meta_data import (
    DataCategory,
    DataDomain,
    DataFormat,
    DataRequirement,
    DiscreteRestriction,
)
from dmod.core.execution import AllocationParadigm
from dmod.core.serializable import Serializable
from ..model_exec_request_body import ModelExecRequestBody

from typing import List, Literal


class NWMInnerRequestBody(ModelExecRequestBody):
    name: Literal["nwm"] = "nwm"

    # NOTE: default value, `None`, is not validated by pydantic
    data_requirements: List[DataRequirement] = None

    @root_validator()
    def _add_data_requirements_if_missing(cls, values: dict):
        data_requirements = values["data_requirements"]

        # None is non-validated default
        if data_requirements is None:
            config_data_id: str = values["config_data_id"]

            data_id_restriction = DiscreteRestriction(
                variable="data_id", values=[config_data_id]
            )
            values["data_requirements"] = [
                DataRequirement(
                    domain=DataDomain(
                        data_format=DataFormat.NWM_CONFIG,
                        discrete_restrictions=[data_id_restriction],
                    ),
                    is_input=True,
                    category=DataCategory.CONFIG,
                )
            ]

        return values

    class Config:
        # NOTE: `name` field is not included at this point for backwards compatibility sake. This
        # may change in the future.
        fields = {"name": {"exclude": True}}


class NWMRequestBody(Serializable):
    # TODO: flatten this hierarchy by replacing NWMRequestBody with NWMInnerRequestBody.
    nwm: NWMInnerRequestBody

    @property
    def name(self) -> str:
        return self.nwm.name

    @property
    def config_data_id(self) -> str:
        return self.nwm.config_data_id

    @property
    def cpu_count(self) -> int:
        return self.nwm.cpu_count

    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        return self.nwm.allocation_paradigm

    @property
    def data_requirements(self) -> List[DataRequirement]:
        return self.nwm.data_requirements
