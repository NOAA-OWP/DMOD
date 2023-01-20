from pydantic import Extra

from dmod.core.serializable import Serializable

from typing import Optional

UNSUCCESSFUL_JOB = -1


class SchedulerRequestResponseBody(Serializable):
    job_id: int = UNSUCCESSFUL_JOB
    output_data_id: Optional[str]

    class Config:
        # allow extra model fields
        extra = Extra.allow
