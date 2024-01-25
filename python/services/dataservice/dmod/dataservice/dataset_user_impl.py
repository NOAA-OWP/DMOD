from dmod.core.dataset import DatasetUser
from dmod.scheduler.job import Job
from typing import Union
from uuid import UUID


class JobDatasetUser(DatasetUser):
    """
    Implementation that also holds a job object and represents that job's role as the user of datasets.
    """

    def __init__(self, job: Union[Job, UUID, str], *args, **kwargs):
        """

        Parameters
        ----------
        job: Union[Job, UUID, str]
            The associated job itself or its unique id.
        args
        kwargs
        """
        super().__init__(*args, **kwargs)
        if isinstance(job, Job):
            self._job_uuid = UUID(job.job_id)
        elif isinstance(job, str):
            self._job_uuid = UUID(job)
        else:
            self._job_uuid = job

    @property
    def uuid(self) -> UUID:
        """
        UUID for this instance.

        Returns
        -------
        UUID
            UUID for this instance.
        """
        return self._job_uuid
