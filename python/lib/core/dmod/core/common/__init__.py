"""
Provides common functions and helper classes
"""
from __future__ import annotations

import typing
import math

from .failure import Failure
from .helper_functions import get_current_function_name
from .helper_functions import is_sequence_type
from .helper_functions import is_iterable_type
from .helper_functions import on_each
from .helper_functions import get_subclasses
from .helper_functions import truncate
from .helper_functions import is_true
from .helper_functions import to_json
from .helper_functions import order_dictionary
from .helper_functions import find
from .helper_functions import contents_are_equivalent
from .helper_functions import humanize_text
from .helper_functions import generate_identifier
from .helper_functions import generate_key
from .tasks import wait_on_task
from .tasks import cancel_task
from .tasks import cancel_tasks
from .collection import Bag

from ..enum import PydanticEnum

class Status(PydanticEnum):
    UNKNOWN = "UNKNOWN"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def get(cls, status: typing.Union[Status, typing.SupportsInt, str] = None) -> typing.Optional[Status]:
        if status is None:
            return cls.default()
        elif isinstance(status, Status):
            return status
        elif isinstance(status, str):
            return cls.by_name(status)
        elif status is math.nan:
            return None
        elif isinstance(status, typing.SupportsInt):
            return cls.by_value(status)
        raise KeyError(f"No {cls.__name__} values can be found with a value or name of {str(status)}")

    @classmethod
    def default(cls) -> Status:
        return cls.UNKNOWN

    @classmethod
    def entry_to_index(cls) -> typing.Mapping[Status, int]:
        return {
            status: index
            for index, status in enumerate(cls)
        }

    @classmethod
    def get_index(cls, status: typing.Union[Status, typing.SupportsInt, str]) -> typing.SupportsInt:
        if not isinstance(status, Status):
            status = cls.get(status)
        return cls.entry_to_index().get(status, math.nan)

    @classmethod
    def by_name(cls, name: str) -> typing.Optional[Status]:
        for entry in cls:
            if entry.name.lower() == name.lower():
                return entry
        return None

    @classmethod
    def by_value(cls, value: typing.SupportsInt) -> typing.Optional[Status]:
        for entry in cls:
            if entry.value == value:
                return entry
        return None

    def __eq__(self, other: typing.Union[Status, typing.SupportsInt, str]) -> bool:
        if self == other:
            return True

        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index == other_index

    def __lt__(self, other: typing.Union[Status, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index < other_index

    def __le__(self, other: typing.Union[Status, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index <= other_index

    def __gt__(self, other: typing.Union[Status, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index > other_index

    def __ge__(self, other: typing.Union[Status, typing.SupportsInt, str]) -> bool:
        other_index = self.__class__.get_index(other)
        this_index = self.__class__.get_index(self)

        return this_index >= other_index
