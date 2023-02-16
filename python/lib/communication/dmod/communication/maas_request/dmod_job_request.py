from abc import ABC, abstractmethod

from typing import List, Optional, Union

from dmod.core.execution import AllocationParadigm
from dmod.core.meta_data import DataFormat, DataRequirement
from ..message import AbstractInitRequest


class DmodJobRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of messages requesting execution of some kind of workflow job.
    """

    _DEFAULT_CPU_COUNT = 1
    """ The default number of CPUs to assume are being requested for the job, when not explicitly provided. """

    def __init__(self, config_data_id: str, cpu_count: Optional[int] = None,
                allocation_paradigm: Optional[Union[str, AllocationParadigm]] = None, *args, **kwargs):
        super(DmodJobRequest, self).__init__(*args, **kwargs)
        self._config_data_id = config_data_id
        self._cpu_count = (
            cpu_count if cpu_count is not None else self._DEFAULT_CPU_COUNT
        )
        if allocation_paradigm is None:
            self._allocation_paradigm = AllocationParadigm.get_default_selection()
        elif isinstance(allocation_paradigm, str):
            self._allocation_paradigm = AllocationParadigm.get_from_name(
                allocation_paradigm
            )
        else:
            self._allocation_paradigm = allocation_paradigm

    @property
    def allocation_paradigm(self) -> AllocationParadigm:
        """
        The allocation paradigm desired for use when allocating resources for this request.

        Returns
        -------
        AllocationParadigm
            The allocation paradigm desired for use with this request.
        """
        return self._allocation_paradigm

    @property
    def config_data_id(self) -> str:
        """
        Value of ``data_id`` index to uniquely identify the dataset with the primary configuration for this request.

        Returns
        -------
        str
            Value of ``data_id`` identifying the dataset with the primary configuration applicable to this request.
        """
        return self._config_data_id

    @property
    def cpu_count(self) -> int:
        """
        The number of processors requested for this job.

        Returns
        -------
        int
            The number of processors requested for this job.
        """
        return self._cpu_count

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
