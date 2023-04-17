from .common import *
from .communication import RedisCommunicator
from .communication import get_redis_connection
from .communication import redis_prefix
from .communication import get_channel_key
from .communication import get_evaluation_pointers
from .communication import get_evaluation_key
from .common import key_separator
from .async_orm import communicate_with_database
from .async_orm import select_from_database
from .message import make_message_serializable

from dmod.metrics import Communicator
from dmod.metrics import CommunicatorGroup


def get_communicator(communicator_id: str, **kwargs) -> Communicator:
    return RedisCommunicator(communicator_id=communicator_id, **kwargs)


def get_communicators(communicator_id: str, **kwargs) -> CommunicatorGroup:
    return CommunicatorGroup(get_communicator(communicator_id, **kwargs))
