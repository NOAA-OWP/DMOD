from abc import ABC, abstractmethod

from typing import List, Optional, Union

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import DataFormat, DataRequirement
from ..message import AbstractInitRequest


class DmodJobRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of messages requesting execution of some kind of workflow job.
    """

    # TODO: #pydantic_rebase - Pydantic-ly add config_data_id, cpu_count, allocation_paradigm properties here

    # TODO: #pydantic_rebase - reconcile the above property additions with subclasses implementations

    # TODO: #pydantic_rebase - fix this for pydantic format
    _DEFAULT_CPU_COUNT = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

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
