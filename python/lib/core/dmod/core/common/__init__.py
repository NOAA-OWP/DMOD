"""
Provides common functions and helper classes
"""
from __future__ import annotations

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
from .helper_functions import flat
from .helper_functions import flatmap
from .helper_functions import package_directory
from .helper_functions import contents_are_equivalent
from .helper_functions import humanize_text
from .helper_functions import generate_identifier
from .helper_functions import generate_key

from .tasks import wait_on_task
from .tasks import cancel_task
from .tasks import cancel_tasks

from .collections import Bag
from .collections import InputCatalog
from .collections import CatalogEntry
from .collections import MapModel
from .collections import SequenceModel
from .collections import CollectionEvent

from .protocols import DBAPIConnection
from .protocols import DBAPICursor
from .protocols import DBAPIColumnDescription

from .types import CommonEnum
from .types import TextValueCollection
from .types import TextValue
from .types import TextValues


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
