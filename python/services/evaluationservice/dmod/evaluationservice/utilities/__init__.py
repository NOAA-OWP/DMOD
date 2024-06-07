"""
Common shared utilities used throughout the service
"""
from dmod.metrics import Communicator
from dmod.metrics import CommunicatorGroup

from dmod.core.context import DMODObjectManager
from dmod.core.context.base import ObjectCreatorProtocol

from .common import *
from .communication import RedisCommunicator

from .communication import get_redis_connection
from .communication import get_runner_connection
from .communication import get_channel_connection

from .communication import redis_prefix
from .communication import get_channel_key
from .communication import get_evaluation_pointers
from .communication import get_evaluation_key
from .common import key_separator
from .common import create_basic_credentials
from .common import create_token_credentials
from .message import make_message_serializable


def get_communicator(communicator_id: str, object_manager: ObjectCreatorProtocol = None, **kwargs) -> Communicator:
    """
    Create default communicator to be used for evaluations

    Args:
        communicator_id: The ID of the communicator
        object_manager: The object manager that will create the communicator as a proxy
        **kwargs:

    Returns:
        A proxy for a communicator
    """
    if object_manager is not None:
        return object_manager.create_object("RedisCommunicator", communicator_id=communicator_id, **kwargs)

    return RedisCommunicator(communicator_id=communicator_id, **kwargs)


def get_communicators(communicator_id: str, object_manager: ObjectCreatorProtocol = None, **kwargs) -> CommunicatorGroup:
    """
    Creates the default group of communicators to be used for evaluations

    Args:
        communicator_id: The ID of the core communicator
        object_manager: The object manager used to handle shareable communicators
        **kwargs:

    Returns:
        A group of communicators to be used for evaluations
    """
    return CommunicatorGroup(
        get_communicator(communicator_id=communicator_id, object_manager=object_manager, **kwargs)
    )
