from abc import ABC
from pydantic import Field, validator

from dmod.core.serializable import Serializable
from dmod.core.execution import AllocationParadigm

from typing import ClassVar


class ModelExecRequestBody(Serializable, ABC):
    _DEFAULT_CPU_COUNT: ClassVar[int] = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    # model type discriminator field. enables constructing correct subclass based on `name` field
    # value.
    # override `name` in subclasses using `typing.Literal`
    # e.g. `name: Literal["ngen"] = "ngen"`
    name: str = Field("", description="The name of the model to be used")

    config_data_id: str = Field(description="Uniquely identifies the dataset with the primary configuration for this request.")
    cpu_count: int = Field(_DEFAULT_CPU_COUNT, gt=0, description="The number of processors requested for this job.")
    allocation_paradigm: AllocationParadigm = Field(
        default_factory=AllocationParadigm.get_default_selection,
        description="The allocation paradigm desired for use when allocating resources for this request."
    )

    @validator("name", pre=True)
    def _lower_model_name_(cls, value: str):
        # NOTE: this should enable case insensitive subclass construction based on `name`, that is
        # if all `name` field's are lowercase.
        return str(value).lower()
