"""
Module to define universal logging rules that may be used within and without the service
"""

import os
import logging
import logging.config
import typing
import json
import traceback
import inspect
import functools

# Linters will say this isn't used, but it loads basic log handlers into the memory space for discovery
#
# If additional handlers are added, their package(s) need to be imported here for logging handler discoverability
from logging import handlers

from . import application_values

from utilities import make_message_serializable

MESSAGE = typing.Union[Exception, str, dict]

DEFAULT_LOGGER_NAME = os.environ.get("DEFAULT_EVALUATION_LOGGER", application_values.APPLICATION_NAME.replace(" ", ""))
"""
The name of the default logger to use when configuring the logging system
"""

DEFAULT_SOCKET_LOGGER_NAME = os.environ.get("DEFAULT_SOCKET_LOGGER_NAME", "SocketLogger")
"""
The name of the default logger intended for use by web sockets
"""


class ConfiguredLogger:
    """
    Forwards module level logging functions that differ from stock logging
    """
    def __init__(self, logger_name: str = None):
        self._logger_name = logger_name or DEFAULT_LOGGER_NAME

    def info(self, message: MESSAGE):
        """
        Forwards the module level `info` function

        Args:
            message: An exception, string, or dict to log as basic information text
        """
        info(message=message, logger_name=self._logger_name)

    def warn(self, message: MESSAGE):
        """
        Forwards the module level `warn` function

        See Also: ``service.logging.warn``

        Args:
            message: An exception, string, or dict to log as basic warning text
        """
        warn(message=message, logger_name=self._logger_name)

    def error(self, message: MESSAGE, exception: Exception = None):
        """
        Forwards the module level `error` function

        See Also: ``service.logging.error``

        Args:
            message: An exception, string, or dict to log as basic error text
            exception: An optional exception from the cause of the error
        """
        error(message=message, exception=exception, logger_name=self._logger_name)

    def debug(self, message: MESSAGE):
        """
        Forwards the module level `debug` function

        See Also: ``service.logging.debug``

        Args:
            message: An exception, string, or dict to log as basic debugging text
        """
        debug(message=message, logger_name=self._logger_name)

    def log(self, message: MESSAGE, level: int = None):
        """
        Forwards the module level `log` function

        See Also: ``service.logging.log``

        Args:
            message: An exception, string, or dict to log as basic logging text
            level: The level that a message should be logged as
        """
        log(message=message, logger_name=self._logger_name, level=level)


@functools.cache
def valid_log_levels() -> typing.Collection[str]:
    """
    Returns:
        A list of names of logging levels accepted by the standard python logging library
    """
    return [
        'CRITICAL',
        'ERROR',
        'WARNING',
        'INFO',
        'DEBUG',
        'NOTSET'
    ]


@functools.cache
def available_logging_handlers() -> typing.Mapping[str, typing.Type[logging.Handler]]:
    """
    Returns:
        A list of the full names of all logging handlers that may be used
    """
    def get_handlers(klazz: typing.Type[logging.Handler] = None) -> typing.List[typing.Type[logging.Handler]]:
        """
        Gets all usuable log handlers available for configuration

        Args:
            klazz: The base class to start searching from

        Returns:
            A list of all currently usable log handlers
        """
        if klazz is None:
            klazz = logging.Handler

        log_handlers = list(klazz.__subclasses__())

        for handler in log_handlers:
            log_handlers.extend([
                subclass
                for subclass in get_handlers(handler)
                if subclass not in log_handlers
            ])

        # Return all found handlers except the null, base, and protected handlers
        return [
            handler
            for handler in log_handlers
            if not handler.__name__.startswith("_")
               and 'Base' not in handler.__name__
               and 'Null' not in handler.__name__
        ]

    mapped_handlers: typing.Dict[str, typing.Type[logging.Handler]] = dict()

    for found_handler in get_handlers():
        mapped_handlers[f"{found_handler.__module__}.{found_handler.__name__}"] = found_handler
        mapped_handlers[f"{found_handler.__name__}"] = found_handler


    # Return the full name of each found log handler
    return mapped_handlers


@functools.cache
def get_socket_log_level() -> str:
    """
    Returns:
        The name of the logging level to use for web sockets
    """
    socket_log_level = os.environ.get("EVALUATION_SERVICE_SOCKET_LOG_LEVEL")
    fallback_log_level = 'WARNING' if application_values.in_debug_mode() else 'ERROR'

    if socket_log_level is not None and socket_log_level.upper() not in valid_log_levels():
        print(f"'{socket_log_level}' is not a valid logging level. Defaulting to '{fallback_log_level}'.")
        socket_log_level = fallback_log_level
    elif socket_log_level is None:
        return fallback_log_level

    return socket_log_level.upper()


@functools.cache
def get_log_level() -> str:
    """
    Returns:
        The application-wide log level
    """
    current_log_level = os.environ.get("EVALUATION_SERVICE_LOG_LEVEL")

    if current_log_level is not None and current_log_level.upper() in valid_log_levels():
        return current_log_level.upper()
    elif current_log_level is not None:
        fallback_level = 'DEBUG' if application_values.in_debug_mode() else 'INFO'
        print(f"{current_log_level.upper()} is not a valid logging level. Defaulting to {fallback_level}")
        return fallback_level

    return 'DEBUG' if application_values.in_debug_mode() else 'INFO'


@functools.cache
def get_evaluation_service_logging_filename() -> str:
    evaluation_service_log_filename = os.environ.get(
        'APPLICATION_LOG_PATH',
        os.path.join(application_values.BASE_DIRECTORY, f'{DEFAULT_LOGGER_NAME}.log')
    )

    if not evaluation_service_log_filename.endswith(".log"):
        evaluation_service_log_filename += ".log"

    return evaluation_service_log_filename


@functools.cache
def get_socket_log_filename() -> str:
    socket_log_filename = os.environ.get(
        "EVALUATION_SOCKET_LOG_PATH",
        os.path.join(application_values.BASE_DIRECTORY, "EvaluationSockets.log")
    )

    if not socket_log_filename.endswith(".log"):
        socket_log_filename += ".log"

    return socket_log_filename


@functools.cache
def get_maximum_log_size() -> int:
    maximum_log_size = os.environ.get("MAXIMUM_LOG_SIZE", "5").upper()

    if maximum_log_size.endswith("B"):
        if maximum_log_size[-2] not in ("K", "M", "G"):
            old_log_unit = maximum_log_size[-2:] if maximum_log_size[-2].isalpha() else maximum_log_size[-1]
            new_log_unit = "KB" if not maximum_log_size[-2].isalpha() else "MB"
            print(
                f"WARNING: Only KB, MB, and GB are acceptable log file sizes and {old_log_unit} was used instead. "
                f"Defaulting to {new_log_unit}"
            )
            maximum_log_size = maximum_log_size[:-2] + new_log_unit
        log_unit = maximum_log_size[-2:].upper()
        quantity = float(maximum_log_size[:-2])
        while quantity < 0:
            if log_unit in ('MB', 'GB'):
                quantity *= 10
            else:
                quantity = 1

            if log_unit == 'GB':
                log_unit = 'MB'
            elif log_unit == 'MB':
                log_unit = 'KB'

        if log_unit == 'KB':
            maximum_log_size = quantity * 1000
        elif log_unit == 'MB':
            maximum_log_size = quantity * 1000 * 1000
        else:
            print(
                "WARNING: The size of log files have been described in terms of GB; "
                "log files stand to become very large."
            )
            maximum_log_size = quantity * 1000 * 1000 * 1000
    else:
        # If a size unit (KB, MB, GB) wasn't passed, assume MB
        maximum_log_size = int(float(maximum_log_size) * 1000 * 1000)

    return maximum_log_size


@functools.cache
def get_maximum_log_backups() -> int:
    maximum_backups = os.environ.get("MAXIMUM_LOGFILE_BACKUPS", "5")
    return int(float(maximum_backups))


def create_handler_configuration(
    level: str,
    handler_classname: str = None,
    possible_filename: str = None,
    **kwargs
) -> dict:
    """
    Creates a configuration for a  handler based off of environment conditions and passed in arguments

    Args:
        level: The minimum level of message that this handler will accept
        handler_classname: An optional name of the class that this configuration will create
        possible_filename: An optional file name for where data should be saved if the created handler writes to files
        **kwargs:

    Returns:
        A configuration for a logging handler
    """
    # Go with the default handler if one wasn't explicitly specified. This will generally log to a file
    if not handler_classname:
        handler_classname = os.environ.get("DEFAULT_LOG_HANDLER", "logging.handlers.RotatingFileHandler")

    # Create a catalog of all handlers that may be created ({'class name': class})
    #
    # Both the bare name of the class AND the name of the class plus the package will be included.
    # This means that a `logging.handlers.RotatingFileHandler` may be created by passing either
    # 'RotatingFileHandler' or 'logging.handlers.RotatingFileHandler'
    available_handlers = available_logging_handlers()

    if handler_classname not in available_handlers:
        raise KeyError(f"'{handler_classname}' is not an available class of logging handlers.")

    handler = available_handlers[handler_classname]

    handler_configuration = {
        "level": level,
        "formatter": "standard_formatter",
        'class': f"{handler.__module__}.{handler.__name__}"
    }

    # Read the parameters off of the constructor signature to see what may be pulled in
    handler_constructor_parameters = inspect.signature(available_handlers[handler_classname]).parameters

    # Attach a filename if accepted. This will generally be for FileHandlers
    if 'filename' in handler_constructor_parameters:
        handler_configuration['filename'] = possible_filename

    # Attach a maxBytes if accepted. This will generally be for Rotating Handlers
    if 'maxBytes' in handler_constructor_parameters:
        handler_configuration['maxBytes'] = get_maximum_log_size()

    # Attach a backupCount if accepted. This will generally be for Rotating Handlers
    if 'backupCount' in handler_constructor_parameters:
        handler_configuration['backupCount'] = get_maximum_log_backups()

    # Attach a host name if accepted. This will generally be for handlers that write through TCP or UDP
    if 'host' in handler_constructor_parameters:
        host = kwargs.get("host") or os.environ.get("DEFAULT_LOGGING_HOST")
        if host:
            handler_configuration['host'] = host

    # Attach a port designation if accepted. This will generally be for handlers that write through TCP or UDP
    if 'port' in handler_constructor_parameters:
        port = kwargs.get("port") or os.environ.get("DEFAULT_LOGGING_PORT")
        if port:
            handler_configuration['port'] = port

    # Attach the address if accepted. This will generally be for handlers that write to syslogs
    if 'address' in handler_constructor_parameters:
        address = kwargs.get("address")
        if address is None:
            host = kwargs.get("host") or os.environ.get("DEFAULT_LOGGING_HOST")
            port = kwargs.get("port") or os.environ.get("DEFAULT_LOGGING_PORT")
            if host:
                address = (host, port)
        if address:
            handler_configuration['address'] = address

    # Go through the rest of the kwargs and attach anything that may seem pertinent
    for key, value in kwargs.items():
        if key in handler_constructor_parameters and key not in handler_configuration:
            handler_configuration[key] = value

    return handler_configuration


DEFAULT_LOGGING_CONFIGURATION = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'standard_formatter': {
            'format': os.environ.get("LOG_FORMAT", "[%(asctime)s] %(levelname)s: %(message)s"),
            'datefmt': os.environ.get("LOG_DATEFMT", application_values.COMMON_DATETIME_FORMAT)
        },
    },
    'root': {
        'handlers': [f'{DEFAULT_LOGGER_NAME}_Handler', 'stdout'],
        'level': get_log_level()
    },
    'handlers': {
        f'{DEFAULT_LOGGER_NAME}_Handler': create_handler_configuration(
            level=get_log_level(),
            possible_filename=get_evaluation_service_logging_filename()
        ),
        f"{DEFAULT_SOCKET_LOGGER_NAME}_Handler": create_handler_configuration(
            level=get_socket_log_level(),
            possible_filename=get_socket_log_filename()
        ),
        'stdout': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard_formatter'
        }
    },
    'loggers': {
        DEFAULT_LOGGER_NAME: {
            'handlers': [f'{DEFAULT_LOGGER_NAME}_Handler', 'stdout'],
            'level': get_log_level()
        },
        "SOCKETS": {
            'handlers': [f"{DEFAULT_SOCKET_LOGGER_NAME}_Handler"],
            'level': get_socket_log_level()
        }
    }
}


def configure_logging():
    """
    Attaches the configured logging elements to the python logging module
    """
    if len(logging.getLogger().handlers) > 0:
        return

    configuration_filename = os.environ.get("LOGGING_CONFIGURATION")

    # If an actual config file is designated, default to that. It can and WILL be more detailed and specific
    if configuration_filename and os.path.isfile(configuration_filename):
        logging.config.fileConfig(fname=configuration_filename, disable_existing_loggers=False)
    else:
        # Otherwise, roll with the generated configuration
        logging.config.dictConfig(DEFAULT_LOGGING_CONFIGURATION)


def log(message: MESSAGE, exception: Exception = None, logger_name: str = None, level: int = None):
    """
    Log a message to a logger

    Args:
        message: Something to be logged. If it is some sort of object, it will be attempted to be converted to a loggable version
        exception: An optional exception to write detailed information about (like a stack trace)
        logger_name: The name of a logger to write to. Falls back to the default configured logger if none given
        level: The level at which the message should be logged
    """
    configure_logging()

    if isinstance(message, Exception):
        message = os.linesep.join(traceback.format_exception_only(type(message), message))

    message = make_message_serializable(message)
    message = json.dumps(message, indent=4)

    if exception is not None:
        exception_message = os.linesep
        if isinstance(exception, Exception):
            exception_message += os.linesep.join(traceback.format_exception_only(type(exception), exception))
        elif isinstance(exception, dict):
            exception_message += json.dumps(make_message_serializable(exception), indent=4)
        elif isinstance(exception, bytes):
            exception_message = exception.decode()
        else:
            exception_message += str(exception)

        message += os.linesep
        message += exception_message

    if logger_name is None:
        logger_name = DEFAULT_LOGGER_NAME

    if level is None:
        level = logging.INFO
    elif not isinstance(level, int):
        level = logging.getLevelName(str(level).upper())
        if not isinstance(level, str):
            level = logging.INFO

    logger = logging.getLogger(logger_name)
    logger.log(level=level, msg=message)


def info(message: MESSAGE, logger_name: str = None):
    log(message, logger_name, level=logging.INFO)


def warn(message: MESSAGE, logger_name: str = None):
    log(message, logger_name, level=logging.WARNING)


def error(message: MESSAGE, exception: Exception = None, logger_name: str = None):
    log(message=message, exception=exception, logger_name=logger_name, level=logging.ERROR)


def debug(message: MESSAGE, logger_name: str = None):
    log(message, logger_name, level=logging.DEBUG)


def get_logger(logger_name: str = None) -> ConfiguredLogger:
    return ConfiguredLogger(logger_name)


configure_logging()
