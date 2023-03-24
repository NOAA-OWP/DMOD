from abc import ABC, abstractmethod

from pydantic import Field, validator
from typing import ClassVar, List

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import DataFormat, DataRequirement
from ..message import AbstractInitRequest


class DmodJobRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of messages requesting execution of some kind of workflow job.
    """

    _DEFAULT_CPU_COUNT: ClassVar[int] = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    # job type discriminator field. enables constructing correct subclass based on `job_type` field
    # value.
    # override `job_type` in subclasses using `typing.Literal`
    # e.g. `job_type: Literal["ngen"] = "ngen"`
    job_type: str = Field("", description="The name for the type of job being requested.")

    cpu_count: int = Field(_DEFAULT_CPU_COUNT, gt=0, description="The number of processors requested for this job.")
    allocation_paradigm: AllocationParadigm = Field(
        default_factory=AllocationParadigm.get_default_selection,
        description="The allocation paradigm desired for use when allocating resources for this request."
    )

    @validator("job_type", pre=True)
    def _lower_job_type_(cls, value: str):
        # NOTE: this should enable case insensitive subclass construction based on `job_type`, that is
        # if all `job_type` field's are lowercase.
        return str(value).lower()

    def __hash__(self) -> int:
        return hash((self.job_type, self.cpu_count, self.allocation_paradigm))

    @property
    @abstractmethod
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request, as needed for creating a job object.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        pass

    @property
    def is_intelligent_request(self) -> bool:
        """
        Whether this request requires some of DMOD's intelligent automation.

        Whether this request required some intelligence be applied by DMOD, as the details of the requirements are only
        partially explicitly defined, but can (in principle) be determined by examine the currently stored datasets.

        In the default, base implementation, this is ``False``. It should be overridden when/as appropriate in subtypes.

        Returns
        -------
        bool
            Whether this request requires some of DMOD's intelligent automation.
        """
        return False

    @property
    @abstractmethod
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested job.

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested job.
        """
        pass
