from .backend import Backend
from .file import FileBackend
from .. import specification

__BACKEND_TYPE_MAP = {
    "file": FileBackend
}


def get_backend(backend_specification: specification.BackendSpecification, cache_limit: int = None) -> Backend:
    """
    Determine and create the right type of backend

    Args:
        backend_specification: Instructions for what backend to create
        cache_limit: A limit to the amount of backend data that may be kept in memory

    Returns:
         A backend through which to retrieve data
    """
    data_backend = None

    if backend_specification.type.lower() in __BACKEND_TYPE_MAP:
        data_backend = __BACKEND_TYPE_MAP[backend_specification.type.lower()](backend_specification, cache_limit)

    if backend is None:
        raise TypeError(f"'{backend_specification.type}' is not a supported type of data backend.")

    return data_backend
