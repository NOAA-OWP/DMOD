"""
Put a module wide description here
"""
import typing

from django.core.cache import cache
from django.core.cache import caches
from django.core.cache.backends.base import BaseCache


def _get_cache(name: str = None) -> BaseCache:
    if name:
        return caches[name]
    return cache


def set_value(
    key: str,
    value: typing.Union[int, str, bytes],
    timeout: int = None,
    cache_name: str = None
):
    """
    Set a value in the cache

    Args:
        key: The key for the value to set
        value: The value to store
        timeout: An optional number of seconds to let the value exist
        cache_name: An optional name for the cache to use; the default cache will be used if one is not indicated
    """
    connection = _get_cache(cache_name)
    connection.set(key=key, value=value, timeout=timeout)


def get_value(
    key: str,
    reset_timeout: int = None,
    cache_name: str = None,
    default=None
) -> typing.Any:
    """
    Get a value from the cache

    Example:
        >>> set_value("example1", 2345)
        >>> get_value("example1")
        b'2345'
        >>> set_value("example2", 234, cache_name="Testtwo")
        >>> get_value("example2")

        >>> get_value("example2", cache_name="Testtwo")
        b'234'
        >>> get_value("example2", default=9)
        9

    Args:
        key: The name of the value
        reset_timeout: The number of seconds to reset the timer for the value by
        cache_name: An optional name for the cache to use; the default cache will be used if one is not indicated
        default: An optional default to return instead of null if the value isn't present

    Returns:
        The value if the key exists, otherwise None or the default value
    """
    connection = _get_cache(cache_name)
    value = connection.get(key, default=default)

    if value and reset_timeout:
        cache.touch(key, reset_timeout)

    return value