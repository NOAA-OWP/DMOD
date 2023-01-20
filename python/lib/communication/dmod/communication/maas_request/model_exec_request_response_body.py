from ..scheduler_request import SchedulerRequestResponse, SchedulerRequestResponseBody


class ModelExecRequestResponseBody(SchedulerRequestResponseBody):
    scheduler_response: SchedulerRequestResponse

    @classmethod
    def from_scheduler_request_response(
        cls, scheduler_response: SchedulerRequestResponse
    ) -> "ModelExecRequestResponseBody":
        return cls(
            job_id=scheduler_response.job_id,
            output_data_id=scheduler_response.output_data_id,
            scheduler_response=scheduler_response.copy(),
        )

    # NOTE: legacy support. previously this class was treated as a dictionary
    def __contains__(self, element: str) -> bool:
        return element in self.__dict__

    # NOTE: legacy support. previously this class was treated as a dictionary
    def __getitem__(self, item: str):
        return self.__dict__[item]
