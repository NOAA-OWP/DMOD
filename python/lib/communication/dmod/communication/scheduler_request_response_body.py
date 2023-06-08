from pydantic import Extra

from dmod.core.serializable import Serializable

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny, DictStrAny

UNSUCCESSFUL_JOB = -1


class SchedulerRequestResponseBody(Serializable):
    job_id: int = UNSUCCESSFUL_JOB
    output_data_id: Optional[str]

    class Config:
        # allow extra model fields
        extra = Extra.allow

    def __eq__(self, other: object):
        if isinstance(other, dict):
            return self.to_dict() == other
        return super().__eq__(other)

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    def __getattr__(self, key: str):
        return self.__dict__[key]

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True,  # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = True,  # noop
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> "DictStrAny":
        # Note: for backwards compatibility, unset fields are excluded by default
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=True,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
