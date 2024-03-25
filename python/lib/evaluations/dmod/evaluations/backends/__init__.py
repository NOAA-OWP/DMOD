"""
Module containing classes that handle common IO operations, such as loading input data
"""
import os


__all__ = [
    os.path.splitext(package_file)[0]
    for package_file in os.listdir(os.path.dirname(__file__))
    if package_file != "__init__.py"
       and package_file != 'backend.py'
]


from .backend import Backend

from dmod.core import common
from dmod.core.common.collections import catalog

from . import *

from .. import specification


def get_backend(
    backend_specification: specification.BackendSpecification,
    input_catalog:  catalog.InputCatalog
) -> Backend:
    """
    Determine and create the right type of backend

    Args:
        backend_specification: Instructions for what backend to create
        input_catalog: A shared catalog of data that has been loaded

    Returns:
         A backend through which to retrieve data
    """
    backend_map = {
        subclass.get_backend_type().lower(): subclass
        for subclass in common.get_subclasses(Backend)
    }

    data_backend = backend_map.get(backend_specification.backend_type.lower())

    if data_backend is None:
        raise TypeError(
                f"'{backend_specification.backend_type}' is not a supported type of data backend."
        )

    return data_backend(backend_specification, input_catalog)
