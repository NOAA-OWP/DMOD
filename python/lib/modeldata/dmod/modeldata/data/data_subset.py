from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Collection, Optional, Sequence, Tuple
from ..subset import SimpleHydrofabricSubset


class AbstractDataSubset(ABC, SimpleHydrofabricSubset):
    """
    Extension of ::class:`HydrofabricSubset` that also encapsulates the applicable data.
    """

    __slots__ = ["_data_directory", "_range_start", "_range_end"]

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str], hydrofabric, range_start: datetime,
                 range_end: datetime, data_directory: Path):

        super(AbstractDataSubset, self).__init__(catchment_ids, nexus_ids, hydrofabric)
        self._data_directory = None
        self.data_directory = data_directory
        self._storage_size: int = 0
        self._range_start = range_start
        self._range_end = range_end

    @property
    def data_directory(self) -> Path:
        return self._data_directory

    @data_directory.setter
    def data_directory(self, data_directory: Path):
        if not data_directory.exists():
            data_directory.mkdir()
        elif not data_directory.is_dir():
            raise ValueError("Received existing, non-directory file '{}' as {} data directory.".format(
                self.__class__.__name__))
        self._data_directory = data_directory

    @property
    def range_end(self) -> datetime:
        return self._range_end

    @property
    def range_start(self) -> datetime:
        return self._range_start

    @abstractmethod
    @property
    def storage_size(self) -> int:
        """
        Get the size of the backing data files for this data subset, if such files exist.

        Returns
        -------
        int
            The size of backing data files, in bytes, or ``0`` if there are no (known) backing data files.
        """
        pass
