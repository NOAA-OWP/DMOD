import typing
import inspect
import string

from datetime import datetime
from datetime import timezone

import numpy
import pandas

from dateutil.parser import parse as parse_date_string


def type_name_to_dtype(type_name: str) -> typing.Optional[typing.Type]:
    if type_name in ("string", "str", "word", "words"):
        return str
    elif type_name in ["float"]:
        return numpy.float32
    elif type_name in ['int', 'integer']:
        return numpy.int32
    elif type_name in numpy.sctypes:
        return numpy.sctypes[type_name]
    return None


def is_arraytype(obj) -> bool:
    return isinstance(obj, typing.Sequence) and not isinstance(obj, str)


def value_is_number(value: typing.Any) -> bool:
    """
    Whether the passed in value may be interpretted as a number

    Args:
        value: The value to check

    Returns:
        Whether the value may be interpretted as a number
    """
    if isinstance(value, str) and value.isnumeric():
        return True
    elif isinstance(value, bytes) and value.decode().isnumeric():
        return True
    elif hasattr(type(value), "__mro__") and numpy.number in inspect.getmro(type(value)):
        return True

    return isinstance(value, int) or isinstance(value, float) or isinstance(value, complex)


def type_is_number(type_to_check) -> bool:
    """
    Whether the passed in type is some sort of number

    Args:
        type_to_check: The type to check for whether it's a number

    Returns:

    """
    if isinstance(type_to_check, pandas.Series) and numpy.number in inspect.getmro(type_to_check.dtype.type):
        return True
    elif isinstance(type_to_check, pandas.Series):
        return False

    if isinstance(type_to_check, numpy.dtype) and numpy.number in inspect.getmro(type_to_check.type):
        return True

    if hasattr(type_to_check, "__mro__") and numpy.number in inspect.getmro(type_to_check):
        return True

    return type_to_check == float or type_to_check == int or type_to_check == complex


def clean_name(name: str) -> str:
    characters_to_avoid = string.punctuation.replace("_", " ")

    for character in characters_to_avoid:
        name = name.replace(character, "_")

    while "__" in name:
        name = name.replace("__", "_")

    return name


def is_indexed(frame: pandas.DataFrame) -> bool:
    return not isinstance(frame.index, pandas.RangeIndex)


def str_is_float(value: str) -> bool:
    try:
        converted_value = float(value)
        return True
    except ValueError:
        return False


def find_indices(*frames: pandas.DataFrame) -> typing.Sequence[str]:
    if len(frames) < 2:
        return list()

    common_columns: typing.Set[str] = set()

    for frame in frames:
        if is_indexed(frame):
            frame = frame.reset_index()

        columns = {
            column_name
            for column_name in frame.keys()
            if not type_is_number(frame[column_name])
        }

        if common_columns:
            common_columns = common_columns.union(columns)
        else:
            common_columns = columns

    return [column_name for column_name in common_columns]


def parse_non_naive_dates(datetimes: typing.Sequence[str]) -> typing.Sequence[datetime]:
    """
    A datetime parser for pandas that ensures that all parsed dates and times have a time zone

    The timezone will be utc if none is given

    Args:
        datetimes: A sequence of strings to be parsed as dates

    Returns:
        A sequence of non-naive datetimes
    """
    data = list()

    for date_string in datetimes:
        date_and_time = parse_date_string(date_string)

        if date_and_time.tzinfo is None:
            date_and_time = date_and_time.replace(tzinfo=timezone.utc)

        data.append(date_and_time)

    return data
