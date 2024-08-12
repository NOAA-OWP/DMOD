"""
Common functions and objects that may be used throughout the codebase
"""
import base64
import typing
import traceback

from datetime import datetime
from datetime import timedelta

from exceptiongroup import ExceptionGroup

ErrorIdentifier = typing.Tuple[typing.Union[typing.Type[BaseException], typing.Tuple[str, int, str]], ...]


def get_error_identifier(error: BaseException) -> ErrorIdentifier:
    """
    Create a pickleable common identifier for an error

    This is a common key that will match with other exceptions of the same type triggered via the same code path

    Args:
        error: The error to create a key for

    Returns:
        A tuple of values describing the type of error and where it came from
    """
    error_details: typing.List[typing.Union[typing.Type[BaseException], typing.Tuple[str, int, str]]] = [
        error.__class__
    ]

    trace = error.__traceback__

    if trace is not None:
        try:
            for frame_summary in traceback.extract_tb(trace):
                error_details.append((
                    frame_summary.filename,
                    frame_summary.lineno,
                    frame_summary.name,
                ))
        except:
            pass

    error_identifier: ErrorIdentifier = tuple(error_details)
    return error_identifier


class ErrorCounter:
    """
    A counter for loops that handle repeated operations that need to handle exceptions

    If a certain type of error occurs too many times, that error will be thrown to stop the containing control structure
    """
    def __init__(self, limit: int, lifetime: timedelta = None):
        """
        Args:
            limit: The maximum amount of a specific failure that may occur before the error is raised.
                A specific failure is identified via its code path
            lifetime: The period over which an error must occur multiple times
        """
        self.__error_limit = limit
        self.__exeedance_handlers: typing.List[typing.Callable[[BaseException], typing.Any]] = []
        self.__occurrences: typing.Dict[ErrorIdentifier, typing.List[datetime]] = {}
        self.__lifetime = lifetime or timedelta(minutes=1)

    def on_exceedance(self, handler: typing.Callable[[BaseException], typing.Any]):
        """
        Add an action to perform when an exception has occurred too many times. Duplicate handlers will not be called

        Args:
            handler: A function that will be called when an exception has occurred
        """
        if handler not in self.__exeedance_handlers:
            self.__exeedance_handlers.append(handler)

    @property
    def total(self):
        """
        The total number of errors encountered
        """
        return sum(len(occurrences) for occurrences in self.__occurrences.values())

    @property
    def error_limit(self):
        """
        The maximum amount of errors that can occur before the error is raised
        """
        return self.__error_limit

    def count(self, error: typing.Union[BaseException, ErrorIdentifier]) -> int:
        """
        Get the number of times a certain type of error has been thrown

        Args:
            error: The error to be checked

        Returns:
            The number of times that the error has been checked
        """
        if isinstance(error, BaseException):
            error_identifier = get_error_identifier(error)
        else:
            error_identifier = error

        return len(self.__occurrences.get(error_identifier, []))

    def _handle_exceedance(self, error: BaseException) -> None:
        """
        Call functions on a type of error that has occurred too many times

        Args:
            error: The error the was deemed to be too much
        """
        handler_errors: typing.List[Exception] = []

        for error_handler in self.__exeedance_handlers:
            try:
                error_handler(error)
            except Exception as e:
                traceback.print_exc()
                handler_identifier = getattr(error_handler, getattr(error_handler, '__name__', str(error_handler)))
                e.args = tuple(arg if index > 0 else f"{handler_identifier}: {arg}" for index, arg in enumerate(e.args))
                handler_errors.append(e)

        if handler_errors:
            raise ExceptionGroup(
                "Exceptions were encountered when calling handlers for when exceptions were called too many times",
                handler_errors
            ) from error

    def __purge_old_errors(self, encounter_time: datetime) -> None:
        """
        Remove records of errors that occurred outside the time of interest

        Args:
            encounter_time: The time of the most recent error
        """
        # Filter out all of the old occurrences
        self.__occurrences = {
            error_identifier: [
                occurrence_time
                for occurrence_time in occurrence_times
                if occurrence_time > encounter_time - self.__lifetime
            ]
            for error_identifier, occurrence_times in self.__occurrences.items()
        }

        # Remove all records of errors that no longer have occurrences
        self.__occurrences = {
            error_identifier: occurrence_times
            for error_identifier, occurrence_times in self.__occurrences.items()
            if len(occurrence_times) > 0
        }

    def add_error(self, error: BaseException):
        """
        Add an error to the tracker and throw it if the limit on that type has passed

        Args:
            error: The error to record
        """
        encounter_time = now()

        # Remove old errors - this ensures that errors aren't thrown if they occur too far apart
        self.__purge_old_errors(encounter_time=encounter_time)

        error_identifier = get_error_identifier(error=error)
        self.__occurrences.setdefault(error_identifier, []).append(encounter_time)

        if self.count(error_identifier) > self.__error_limit:
            self._handle_exceedance(error)
            raise error


def key_separator() -> str:
    """
    The separator to use when forming redis keys

    The separator MUST be a valid URL character due to messaging requirements, otherwise the value would be '::'

    Returns:
        The character(s) to use as delimiters when forming redis keys
    """
    return "--"


def create_basic_credentials(
    username: typing.Union[str, bytes],
    password: typing.Union[str, bytes]
) -> typing.Mapping[typing.Literal["HTTP_AUTHORIZATION"], str]:
    """
    Creates a key-value pair with the appropriate header key and header value for basic credential authentication

    Args:
        username: The username for the credentials
        password: The password for the credentials

    Returns:
        A mapping from the header key to the header value
    """
    if isinstance(username, bytes):
        username = username.decode()

    if isinstance(password, bytes):
        password = password.decode()

    username_and_password = f"{username}:{password}".encode()
    return {"HTTP_AUTHORIZATION": f"Basic {base64.b64encode(username_and_password).decode()}"}


def create_token_credentials(
    token: typing.Union[bytes, str]
) -> typing.Mapping[typing.Literal["HTTP_AUTHORIZATION"], str]:
    """
    Creates a key-value pair with the appropriate header key and header value for token credential authentication

    Args:
        token: An assigned token

    Returns:
        A mapping from the header key to the header value
    """
    if isinstance(token, bytes):
        token = token.decode()

    return {"HTTP_AUTHORIZATION": f"Token {token}"}


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

    if local:
        timezone = None
    else:
        from datetime import timezone as tz
        timezone = tz.utc

    return datetime.now(tz=timezone)
