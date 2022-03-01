"""
Provides common functionality and constants that may be used across multiple files
"""

import os
import typing

import pandas


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
