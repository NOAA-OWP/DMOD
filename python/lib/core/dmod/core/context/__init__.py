"""
Tools for managing objects across different processes
"""
import typing

from .base import is_property
from .manager import DMODObjectManager
from .scope import DMODObjectManagerScope


def get_object_manager(
    address: typing.Tuple[str, int] = None,
    authkey: bytes = None,
    monitor_scope: bool = None
) -> DMODObjectManager:
    """
    Creates an default object manager using consistent behavior

    Args:
        address:
        authkey:
        monitor_scope:

    Returns:
        An object manager with consistent settings
    """
    if monitor_scope is None:
        monitor_scope = True

    scope_creation_function: typing.Optional[typing.Callable[[str, DMODObjectManager], DMODObjectManagerScope]] = None

    if monitor_scope:
        scope_creation_function = DMODObjectManagerScope

    return DMODObjectManager(
        address=address,
        authkey=authkey,
        monitor_scope=monitor_scope,
        scope_creator=scope_creation_function
    )
