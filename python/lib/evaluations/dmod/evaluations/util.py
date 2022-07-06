import pathlib
import typing
import inspect
import string
import re
import sys

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import date
from datetime import time

from glob import glob

import json

import dateutil.tz

from dateutil.parser import parse as parse_date

import numpy
import pandas
import pytz

from dateutil.parser import parse as parse_date_string

RE_PATTERN = re.compile(r"(\{.+\}|\[.+\]|\(.+\)|(?<!\\)\.|\{|\}|\]|\[|\(|\)|\+|\*|\\[a-zA-Z]|\?)+")
MULTI_GLOB_PATTERN = re.compile(r"\*+")
EXPLICIT_START_PATTERN = re.compile(r"^(~|\.)?/.*$")

_CLASS_TYPE = typing.TypeVar('_CLASS_TYPE')


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


def get_subclasses(base: typing.Type[_CLASS_TYPE]) -> typing.List[typing.Type[_CLASS_TYPE]]:
    """
    Returns:
        All implemented subclasses
    """
    subclasses = [
        cls
        for cls in base.__subclasses__()
    ]

    concrete_classes = [
        subclass
        for subclass in subclasses
        if not inspect.isabstract(subclass)
    ]

    for subclass in subclasses:
        concrete_classes.extend([
            cls
            for cls in get_subclasses(subclass)
            if cls not in concrete_classes
               and not inspect.isabstract(cls)
        ])

    return concrete_classes


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


def fit_constructor_kwargs(function: typing.Callable, **kwargs) -> typing.Optional[dict]:
    if not inspect.isfunction(function) or not inspect.ismethod(function):
        return None

    signature = inspect.signature(function)

    required_parameters = {
        parameter_name: parameter
        for parameter_name, parameter in signature.parameters.items()
        if parameter.default == parameter.empty
           and parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.POSITIONAL_ONLY)
    }

    missing_parameters = [
        parameter_name for parameter_name in required_parameters if parameter_name not in kwargs
    ]

    if missing_parameters:
        raise ValueError(f"Function cannot be called with fit parameters - missing: '{missing_parameters}'")

    has_variant_keywords = bool([
        parameter_name
        for parameter_name, parameter in signature.parameters.items()
        if parameter.kind == parameter.VAR_KEYWORD
    ])

    if has_variant_keywords:
        return kwargs

    acceptable_arguments = {
        argument_name: argument_value
        for argument_name, argument_value in kwargs.items()
    }

    return acceptable_arguments


def parse_non_naive_dates(datetimes: typing.Sequence[str], *args, **kwargs) -> typing.Sequence[datetime]:
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
        date_and_time = parse_date_string(str(date_string))

        if date_and_time.tzinfo is None:
            date_and_time = date_and_time.replace(tzinfo=timezone.utc)

        data.append(date_and_time)

    return data


def get_timezone(timezone_details: str) -> typing.Optional[timezone]:
    if not timezone_details:
        return timezone(timedelta(hours=0))

    timezone_details = timezone_details.strip()

    if timezone_details in pytz.all_timezones:
        current = datetime.now(dateutil.tz.gettz(timezone_details))
        offset = current.utcoffset()
    elif set(string.ascii_letters).isdisjoint(timezone_details):
        is_negative = timezone_details.startswith("-")

        if timezone_details[0] in ("+", "-"):
            timezone_details = timezone_details[1:]

        timezone_details = timezone_details.replace(":", "")
        timezone_details = timezone_details.zfill(4)
        hours = int(timezone_details[:2])
        minutes = int(timezone_details[2:])

        if is_negative:
            if hours > 0:
                hours *= -1
            else:
                minutes *= -1

        offset = timedelta(hours=hours, minutes=minutes)
    else:
        raise ValueError(f"'{timezone_details}' is not a valid identifier for a timezone")

    return timezone(offset)


def to_date_or_time(
        possible_date: typing.Union[str, dict]
) -> typing.Optional[typing.Union[date, time]]:
    if possible_date is None or isinstance(possible_date, date) or isinstance(possible_date, time):
        return possible_date

    current_date = datetime.utcnow()
    if isinstance(possible_date, dict):
        adjusted_possible_date = {
            key.lower() if isinstance(key, str) else key: item
            for key, item in possible_date.items()
        }
        has_year = 'year' in adjusted_possible_date
        has_month = 'month' in adjusted_possible_date
        has_day = 'day' in adjusted_possible_date
        has_separated_date = has_year or has_month
        has_date = 'date' in adjusted_possible_date

        has_time = 'time' in adjusted_possible_date
        has_hour = 'hour' in adjusted_possible_date
        has_minute = 'minute' in adjusted_possible_date
        has_timezone = 'timezone' in adjusted_possible_date or 'tz' in adjusted_possible_date
        has_separated_time = has_hour or has_minute

        has_datetime = 'datetime' in adjusted_possible_date

        value = None

        if has_datetime:
            if isinstance(adjusted_possible_date['datetime'], float):
                try:
                    value = datetime.utcfromtimestamp(adjusted_possible_date['datetime'])
                    return value
                except:
                    # 'datetime' is present, but possibly not the right field
                    pass
            else:
                try:
                    value = parse_date(adjusted_possible_date['datetime'])
                    if value:
                        return value
                except:
                    # 'datetime' is present, but possibly not the right field
                    pass

        if has_date:
            try:
                if isinstance(adjusted_possible_date['date'], float):
                    value = datetime.fromtimestamp(adjusted_possible_date['date'])
                elif isinstance(adjusted_possible_date['date'], str):
                    value = parse_date(adjusted_possible_date['date'])

                try:
                    if has_time and value:
                        parsed_time = parse_date(adjusted_possible_date['time'])
                        value = value.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=parsed_time.second)
                    elif has_separated_time and value:
                        hour = 0
                        if has_hour:
                            possible_hour = adjusted_possible_date['hour']

                            if isinstance(possible_hour, str):
                                possible_hour = int(float(possible_hour))

                            if possible_hour:
                                hour = possible_hour

                        minute = 0

                        if has_minute:
                            possible_minute = adjusted_possible_date['minute']

                            if isinstance(possible_minute, str):
                                possible_minute = int(float(possible_minute))

                            if possible_minute:
                                minute = possible_minute

                        value = value.replace(hour=hour, minute=minute)

                        timezone_details = adjusted_possible_date.get('timezone') or adjusted_possible_date.get('tz')
                        if timezone_details is not None:
                            time_zone = get_timezone(str(timezone_details))
                            value = value.replace(tzinfo=time_zone)

                except:
                    # some sort of 'time' is present, but it's not the right type of data
                    pass

                if value:
                    return value
            except:
                # 'date' is present, but possibly not the right field. move on.
                pass

        if has_separated_date and has_separated_time:
            datetime_string = ""

            if has_year:
                year_string = str(adjusted_possible_date['year'])

                current_year = str(current_date.year)

                if len(year_string) == 1:
                    year_string = current_year[:3] + year_string
                elif len(year_string) == 2:
                    year_string = current_year[:2] + year_string
                elif len(year_string) == 3:
                    year_string = current_year[0] + year_string
                elif not year_string:
                    year_string = current_year

                datetime_string += f"{year_string}"

            if has_month:
                if has_year:
                    datetime_string += "-"
                datetime_string += f"{str(adjusted_possible_date['month']).zfill(2)}"

            if has_month and has_day:
                datetime_string += f"-{str(adjusted_possible_date['day']).zfill(2)}"

            if has_hour:
                datetime_string += f"T{str(adjusted_possible_date['hour']).zfill(2)}"
            else:
                datetime_string += f"T00"

            if has_minute:
                datetime_string += f":{str(adjusted_possible_date['minute']).zfill(2)}"
            else:
                datetime_string += f":00"

            timezone_details = adjusted_possible_date.get('timezone') or adjusted_possible_date.get('tz')
            time_zone = None
            if timezone_details is not None:
                time_zone = get_timezone(str(timezone_details))

            try:
                value = parse_date(datetime_string)
                if value:
                    if time_zone:
                        value = value.replace(tzinfo=time_zone)

                    return value
            except:
                # The full separated date and time conversion didn't work - it may work when separating them out
                pass

        if has_separated_date:
            date_string = ""

            if has_year:
                year_string = str(adjusted_possible_date['year'])

                current_year = str(current_date.year)

                if len(year_string) == 1:
                    year_string = current_year[:3] + year_string
                elif len(year_string) == 2:
                    year_string = current_year[:2] + year_string
                elif len(year_string) == 3:
                    year_string = current_year[0] + year_string
                elif not year_string:
                    year_string = current_year

                date_string += f"{year_string}"

            if has_month:
                if has_year:
                    date_string += "-"
                date_string += f"{str(adjusted_possible_date['month']).zfill(2)}"

            if has_month and has_day:
                date_string += f"-{str(adjusted_possible_date['day']).zfill(2)}"

            if has_time:
                time_string = str(adjusted_possible_date["time"])

                if ":" in time_string and len(time_string) < 5:
                    split_time_string = time_string.split(":")
                    time_string = f"{split_time_string[0].zfill(2)}:{split_time_string[1].zfill(2)}"
                elif len(time_string) < 4:
                    time_string = time_string.zfill(4)

                date_string += f"T{time_string}"

            timezone_details = adjusted_possible_date.get('timezone') or adjusted_possible_date.get('tz')
            time_zone = None
            if timezone_details is not None:
                time_zone = get_timezone(str(timezone_details))

            try:
                value = parse_date(date_string)
                if value:
                    if has_time and has_timezone:
                        value = value.replace(tzinfo=time_zone)
                    else:
                        value = value.date()
                    return value
            except:
                #
                pass
        if has_time:
            value = parse_date(adjusted_possible_date['time'])
            return value.time()
        if has_separated_time:
            time_string = ""

            if has_hour:
                time_string += f"{adjusted_possible_date['hour'].zfill(2)}"
            else:
                time_string += "00"

            if has_minute:
                time_string += f":{adjusted_possible_date['minute'].zfill(2)}"
            else:
                time_string += ":00"

            date_from_time = parse_date(time_string)
            return date_from_time.time()
    elif isinstance(possible_date, str):
        value = parse_date(possible_date)
        return value

    return None


def get_local_subclasses(module, parent_class: typing.Type) -> typing.Sequence:
    if not hasattr(parent_class, "__subclasses__"):
        return list()

    subclasses = [
        member
        for name, member in inspect.getmembers(module)
        if inspect.isclass(member)
            and not inspect.isabstract(member)
           and member in parent_class.__subclasses__()
    ]

    return subclasses


def data_to_dictionary(data: typing.Union[typing.IO, str, bytes, typing.Dict[str, typing.Any]]) -> dict:
    if hasattr(data, 'read'):
        data: typing.Union[str, bytes] = data.read()

    if isinstance(data, bytes):
        data: str = data.decode()

    if isinstance(data, str):
        data: typing.Dict[str, typing.Any] = json.loads(data)

    if not isinstance(data, dict):
        raise ValueError("Input data could not be converted to an object")

    return data


class Day:
    """
    A simple wrapper around an integer value between 1 and 366 to represent a consistent number of a day of a year

    These takes leap year into account, where 2021/5/23 will have the same value as 2020/5/23
    """
    __slots__ = ['__day']

    LEAP_DAY_OR_FIRST_OF_MARCH = 60

    def __init__(
            self,
            day: typing.Union[
                str,
                pandas.Timestamp,
                numpy.datetime64,
                datetime,
                int,
                dict,
                typing.Sequence[typing.Union[str, int]]]
    ):
        if day is None:
            raise ValueError("The day is not defined; 'None' has been passed.")

        if is_arraytype(day) and len(day) == 1:
            day = day[0]

        if is_arraytype(day):
            possible_args = [
                int(float(argument))
                for argument in day
                if value_is_number(argument)
            ]
            if len(possible_args) == 1:
                day = possible_args[0]
            elif len(possible_args) == 2:
                # We are going to interpret this as month-day
                day = pandas.Timestamp(year=2020, month=possible_args[0], day=possible_args[1])
            elif len(possible_args) > 3:
                # We're going to interpret this as year-month-day. Further args may include time, but those are not
                # important for this
                day = pandas.Timestamp(year=possible_args[0], month=possible_args[1], day=possible_args[2])
            else:
                raise ValueError("A list of no numbers was passed; a Day cannot be interpretted.")

        if isinstance(day, str) and value_is_number(day):
            day = float(day)

        if isinstance(day, float):
            day = int(day)

        if isinstance(day, int) and (day < 1 or day > 366):
            raise ValueError(f"'{day}' cannot be used as a day number - only days between 1 and 366 are allowable.")

        if isinstance(day, str):
            day = parse_date(day)

        if not isinstance(day, pandas.Timestamp) and isinstance(day, (numpy.core.datetime64, datetime)):
            day = pandas.Timestamp(day)

        # Due to the leap day, the day of the year number changes every four years, making the numbers inconsistent.
        # All day of the year numbers will be one behind after the non-existent February 29th, so that number
        # is incremented by 1 to ensure that it matches in and out of leap years.
        if isinstance(day, pandas.Timestamp):
            if not day.is_leap_year and day >= datetime(day.year, month=3, day=1, tzinfo=day.tzinfo):
                day = day.day_of_year + 1
            else:
                day = day.day_of_year

        self.__day = numpy.core.uint16(day)

    @property
    def day_number(self) -> int:
        """
        The number of the day of the year; consistent between leap and non-leap years

        Note: This number will not always point to the true day of the year number. All values post-February 28th
        on non-leap years will be increased by 1 to make the value consistent across leap and non-leap years.

        Returns:
            The number of the day of the year; consistent between leap and non-leap years.
        """
        return self.__day

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        this_year = datetime.now().year
        not_leap_year = datetime.now().year % 4 != 0

        # The day will have been adjusted if this weren't a leap year and was at or after the last day in February,
        # so reverse the adjustment to get the right date
        if not_leap_year and self.__day >= self.LEAP_DAY_OR_FIRST_OF_MARCH:
            day = self.__day - 1
        else:
            day = self.__day

        parsed_date = datetime.strptime(f"{this_year}-{day}", "%Y-%j")
        representation = parsed_date.strftime("%B %-d")
        return representation

    def __eq__(self, other) -> bool:
        if not isinstance(other, Day):
            other = Day(other)

        return self.__day == other.day_number

    def __ge__(self, other) -> bool:
        if not isinstance(other, Day):
            other = Day(other)

        return self.__day >= other.day_number

    def __le__(self, other) -> bool:
        if not isinstance(other, Day):
            other = Day(other)

        return self.__day <= other.day_number

    def __gt__(self, other) -> bool:
        if not isinstance(other, Day):
            other = Day(other)

        return self.__day > other.day_number

    def __lt__(self, other) -> bool:
        if not isinstance(other, Day):
            other = Day(other)

        return self.__day < other.day_number

    def __hash__(self):
        return hash(self.__repr__())


def get_globbed_address(address: str) -> str:
    """
    Returns:
        The address except with regular expressions converted to glob statements
    """
    globbed_address = RE_PATTERN.sub("*", address)

    if globbed_address.endswith("$"):
        globbed_address = globbed_address[:-1]
    else:
        globbed_address += "*"

    if not EXPLICIT_START_PATTERN.match(globbed_address):
        globbed_address = f"*{globbed_address}"

    # Make sure to remove multiple '*' from the glob that may have been added
    globbed_address = MULTI_GLOB_PATTERN.sub("*", globbed_address)
    globbed_address = globbed_address.replace("\\", "")

    return globbed_address


def get_matching_paths(address: str) -> typing.Sequence[typing.Union[str, pathlib.Path]]:
    globbed_address = get_globbed_address(address)
    matching_paths_by_glob: typing.Sequence[str] = glob(globbed_address, recursive=True)

    address_pattern: re.Pattern = re.compile(address)
    matching_paths = [
        path
        for path in matching_paths_by_glob
        if address_pattern.match(path)
    ]
    return matching_paths
