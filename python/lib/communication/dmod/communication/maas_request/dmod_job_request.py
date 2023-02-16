from abc import ABC, abstractmethod

from typing import List

from dmod.core.meta_data import DataFormat, DataRequirement
from ..message import AbstractInitRequest


class DmodJobRequest(AbstractInitRequest, ABC):
    """
    The base class underlying all types of messages requesting execution of some kind of workflow job.
    """

    def __init__(self, *args, **kwargs):
        super(DmodJobRequest, self).__init__(*args, **kwargs)

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
