import os
import typing
import logging

from datetime import datetime

import dateutil
import numpy


def configure_logging():
    file_log_level = logging.getLevelName(
        os.environ.get('EVALUATION_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "DEBUG"))
    )
    text_format = os.environ.get("LOG_FORMAT", "[%(asctime)s] %(levelname)s: %(message)s")
    date_format = os.environ.get("LOG_DATEFMT", datetime_format())
    logging.basicConfig(
        filename='evaluation_service.log',
        level=file_log_level,
        format=text_format,
        datefmt=date_format,
        force=True
    )

    if logging.StreamHandler not in [type(handler) for handler in logging.root.handlers]:
        console_log = logging.StreamHandler()
        console_log.setFormatter(logging.Formatter(fmt=text_format, datefmt=date_format))
        console_log.setLevel(logging.WARNING)
        logging.root.addHandler(console_log)


def application_prefix() -> str:
    return "MAAS--EVALUATION"


def datetime_format() -> str:
    """
    Returns:
        The format that dates whould use when converted to strings
    """
    return "%Y-%m-%d %H:%M:%S%z"


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


def make_message_serializable(message):
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
        return message.strftime(datetime_format())
    elif not isinstance(message, str) and isinstance(message, typing.Iterable):
        return [make_message_serializable(submessage) for submessage in message]

    return message
