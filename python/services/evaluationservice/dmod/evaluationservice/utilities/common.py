import typing
import os
import traceback
import logging

from datetime import datetime

import dateutil
import numpy

from dmod.evaluationservice.service.application_values import COMMON_DATETIME_FORMAT


def is_true(value: str) -> bool:
    """
    Whether a passed value is meant to represent a `True` value.

    Needed in instances where strings need to be evaluated since the string "False" counts as `True`.

    Args:
        value: The value to test against

    Returns:
        Whether a passed value is meant to represent a `True` value.
    """
    if isinstance(value, bytes):
        value = value.decode()

    if not isinstance(value, str):
        logging.warning("A non-string value was passed to dmod.evaluation_service.utilities.common.is_true")
        return bool(value)

    return str(value).lower() in ("yes", "y", "1", 'true', 'on')


def key_separator() -> str:
    """
    The separator to use when forming redis keys

    The separator MUST be a valid URL character due to messaging requirements, otherwise the value would be '::'

    Returns:
        The character(s) to use as delimiters when forming redis keys
    """
    return "--"


def application_prefix() -> str:
    return f"MAAS{key_separator()}EVALUATION"


def now(local: bool = True) -> datetime:
    """
    Generates a timezone aware date and time

    Args:
        local: Whether the given timezone should be local
    Returns:
        Returns the current date and time with the proper timezone information
    """
    if local is None:
        local = True

    timezone = dateutil.tz.tzlocal() if local else dateutil.tz.tzutc()

    return datetime.now(tz=timezone)


def make_message_serializable(message: typing.Union[dict, str, bytes, typing.SupportsFloat, datetime, typing.Iterable]):
    if isinstance(message, dict):
        for key, value in message.items():
            message[key] = make_message_serializable(value)
    elif isinstance(message, bytes):
        return message.decode()
    elif isinstance(message, typing.SupportsFloat):
        if numpy.isneginf(message):
            return "-Infinity"
        if numpy.isposinf(message):
            return "Infinity"
        if numpy.isnan(message):
            return "NaN"
    elif isinstance(message, datetime):
        return message.strftime(COMMON_DATETIME_FORMAT)
    elif isinstance(message, Exception):
        return os.linesep.join(traceback.format_exception_only(type(message), message))
    elif not isinstance(message, str) and isinstance(message, typing.Iterable):
        return [make_message_serializable(submessage) for submessage in message]

    return message
