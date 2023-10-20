"""
Provides common functions and helper classes
"""
from __future__ import annotations

import typing
import math
from abc import abstractmethod
from typing import Sequence
from typing import overload

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

from .types import CommonEnum
from .types import TEXT_VALUE_COLLECTION


class Status(str, CommonEnum):
    """
    Very basic enumeration used to describe the status of something
    """
    UNKNOWN = "UNKNOWN"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def default(cls) -> Status:
        """
        The default Status
        """
        return cls.UNKNOWN
