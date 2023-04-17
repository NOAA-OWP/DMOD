from datetime import datetime

import dateutil


def key_separator() -> str:
    """
    The separator to use when forming redis keys

    The separator MUST be a valid URL character due to messaging requirements, otherwise the value would be '::'

    Returns:
        The character(s) to use as delimiters when forming redis keys
    """
    return "--"


def application_prefix() -> str:
    """
    Returns:
        The key prefix for this application in redis
    """
    return f"MAAS{key_separator()}EVALUATION"


def string_might_be_json(possible_json: str) -> bool:
    """
    Checks to see if a string might be a valid JSON document.

    This just detects if it's worth attempting to parse a string as json, not that a string IS json

    Args:
        possible_json: A string that might be a json document

    Returns:
        If it's worth attempting to parse a string as JSON
    """
    might_be_json = possible_json is not None
    might_be_json = might_be_json and isinstance(possible_json, str)
    might_be_json = might_be_json and len(possible_json) > 2

    if might_be_json:
        is_object = possible_json.startswith("{") and possible_json.endswith("}")
        is_array = possible_json.startswith("[") and possible_json.endswith("]")

        might_be_json = is_object or is_array

    return might_be_json


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
