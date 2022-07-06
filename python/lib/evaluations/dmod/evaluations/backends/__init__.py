from .backend import Backend
import inspect
import os
from .. import specification


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'backend.py'
]
from . import *


def get_backend(backend_specification: specification.BackendSpecification, cache_limit: int = None) -> Backend:
    """
    Determine and create the right type of backend

    Args:
        backend_specification: Instructions for what backend to create
        cache_limit: A limit to the amount of backend data that may be kept in memory

    Returns:
         A backend through which to retrieve data
    """
    backend_map = {
        subclass.get_backend_type().lower(): subclass
        for subclass in Backend.__subclasses__()
        if not inspect.isabstract(subclass)
    }

    data_backend = backend_map.get(backend_specification.type.lower())

    if data_backend is None:
        raise TypeError(
                f"'{backend_specification.type}' is not a supported type of data backend."
        )

    return data_backend(backend_specification, cache_limit)
