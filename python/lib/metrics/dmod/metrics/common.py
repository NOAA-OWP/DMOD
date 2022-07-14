"""
Provides common functionality and constants that may be used across multiple files
"""

import os
import typing
import logging
import logging.handlers
import logging.config

import pandas


def configure_logging() -> typing.NoReturn:
    """
    Forms a very basic logger
    """
    # Remove preexisting StreamHandlers - this will reduce the possibility of having multiple writes to stdout and
    # make sure only the correct level is written to
    preexisting_streamhandlers = [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
    ]

    for stream_handler in preexisting_streamhandlers:
        logging.getLogger().removeHandler(stream_handler)

    level = logging.getLevelName(os.environ.get('METRIC_LOG_LEVEL', os.environ.get("DEFAULT_LOG_LEVEL", "INFO")))
    log_format = os.environ.get("LOG_FORMAT", "[%(asctime)s] %(levelname)s: %(message)s")
    date_format = os.environ.get("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S%z")

    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        level=min(level, logging.DEBUG) if 'UDP_LOG_PORT' in os.environ else level
    )

    log_formatter = logging.Formatter(log_format)

    file_handler = logging.handlers.TimedRotatingFileHandler("metrics.log", when='D', backupCount=14)
    file_handler.setLevel(level)
    file_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(file_handler)

    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(stdout_handler)

    udp_port = os.environ.get("UDP_LOG_PORT")

    if udp_port:
        udp_port = int(float(udp_port))
        other_udp_handlers = [
            handler
            for handler in logging.getLogger().handlers
            if isinstance(handler, logging.handlers.DatagramHandler)
               and handler.port == udp_port
        ]

        if not other_udp_handlers:
            udp_handler = logging.handlers.DatagramHandler(
                host="127.0.0.1",
                port=udp_port
            )
            udp_level = os.environ.get("UDP_LOG_LEVEL") or "DEBUG"
            udp_handler.setLevel(logging.getLevelName(udp_level))
            udp_handler.setFormatter(log_formatter)
            logging.getLogger().addHandler(udp_handler)


EPSILON = float(os.environ.get('METRIC_EPSILON')) if os.environ.get("METRIC_EPSILON") else 0.0001
"""
The distance there may be between two numbers and still considered equal

    Example:
        Function A might produce 84.232323232 and another function may produce 84.2323. Those numbers aren't exactly the 
        same but are similar enough for our purposes.
    
The smaller the number the greater the precision.
"""


class CommonTypes:
    """
    Common, composite types used for type hinting
    """

    ARGS = typing.Optional[typing.Sequence[typing.Any]]
    """
    An optional array of values of any type
    
    Used for the `*args` variable in method signatures
    """

    KWARGS = typing.Optional[typing.Dict[str, typing.Any]]
    """
    An optional dictionary mapping strings to values of any type
    
    Used for the `**kwargs` variable in method signatures
    """

    NUMBER = typing.Union[int, float]
    """
    Either an integer or a floating point number
    
    Note: This is used instead of `numbers.Number` because mathematical functions don't expect it, 
        causing linting warnings
    """

    PANDAS_DATA = typing.Union[pandas.DataFrame, pandas.Series]
    """
    Either a pandas DataFrame or Series
    """

    NUMERIC_OPERATOR = typing.Callable[[NUMBER, NUMBER, typing.Optional[NUMBER]], NUMBER]
    """
    A function that operates on two numbers and a count to produce another number
    """

    NUMERIC_TRANSFORMER = typing.Callable[[NUMBER], NUMBER]
    """
    A simple function that transforms one number into another
    """

    NUMERIC_FILTER = typing.Callable[[NUMBER, NUMBER], bool]
    """
    A simple function that tells whether the first number passes some condition based on the second
    """

    FRAME_FILTER = typing.Callable[[pandas.DataFrame], pandas.DataFrame]
    """
    A function that filters rows out of a pandas DataFrame
    """

    KEY_AND_ROW = typing.Tuple[typing.Hashable, pandas.Series]
    """
    The key and row of a pandas series for use as it is being iterated
    """
