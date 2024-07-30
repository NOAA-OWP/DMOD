import numpy as np

from datetime import datetime
from hypy import Catchment
from typing import List, Optional


class CatchmentData:
    """
    Encapsulation of forcing, parameter, and/or other data for a particular catchment over some period.

    Data should be provided as a 2-D numpy array, with an additional init param for specifying column names.  The data
    array should have each row be some datapoint of attribute values for some time step, with the rows ordered according
    to their time step (data from earlier in time should have lower row indexes).

    Optionally, data can contain a column for timestamps of each row/datapoint.  Such timestamps should be standard
    POSIX timestamp values.  They should be consistent with the params for the time range of the instance.

    """
    def __init__(self, catchment: Catchment, range_start: datetime, range_end: datetime, data: np.ndarray,
                 column_names: List[str], timestamp_col: Optional[int] = None):
        self._catchment = catchment
        # TODO: implement correctly for various supported options, if more than just the assembled array is ok
        self._data = data
        if len(self._data.shape) != 2:
            raise ValueError("Data to initialize {} object neither 2-dimensional array or convertible to one".format(
                self.__class__))
        self._range_start = range_start
        self._range_end = range_end
        if timestamp_col is not None and (timestamp_col < 0 or timestamp_col >= self._data.shape[1]):
            raise ValueError("Out-of-range value supplied for Catchment Data timestamp column")
        self._timestamp_col = timestamp_col
        if len(column_names) != self._data.shape[1]:
            raise ValueError("Catchment data column names do not match number of data columns")
        self._data_columns = list()
        for n in column_names:
            self._data_columns.append(n.strip().upper())
        # TODO: add logic later to verify consistency of range values and timestamps (when included in data)
        # TODO: verify no duplicates in column names
        # TODO: if appropriate, verify that the time step for each row/datapoint is equal (or potentially extrapolate)
        # TODO: do other verification to make sure things are consistent

    def __eq__(self, other):
        return isinstance(other, CatchmentData) \
               and self._catchment.id == other._catchment.id \
               and self._range_start == other._range_start \
               and self._range_end == other._range_end \
               and self._timestamp_col == other._timestamp_col \
               and self._data_columns == other._data_columns \
               and self._data == other._data

    def __hash__(self):
        return self._catchment.id.__hash__() \
               + self._range_start.__hash__() \
               + self._range_end.__hash__() \
               + (0 if self._timestamp_col is None else self._timestamp_col + 1) \
               + ','.join(self._data_columns).__hash__() \
               + self._data.__hash__()

    @property
    def catchment(self) -> Catchment:
        return self._catchment

    def check_contains(self, other: 'CatchmentData'):
        """
        Check whether
        Parameters
        ----------
        other

        Returns
        -------

        """
        # TODO:
        pass

    @property
    def data(self) -> np.ndarray:
        return self._data

    @property
    def range_end(self) -> datetime:
        return self._range_end

    @property
    def range_start(self) -> datetime:
        return self._range_start
