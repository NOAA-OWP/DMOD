"""
Helper functions used for interacting with the Django ORM in an asynchronous context
"""
import typing
import functools
import asyncio
import threading

from django.db.models import QuerySet


_T = typing.TypeVar("_T")
LAZY_RETRIEVER = typing.Callable[[typing.Any, ...], typing.Optional[QuerySet[_T]]]


def get_values_eagerly(function: LAZY_RETRIEVER, *args, **kwargs) -> typing.Optional[typing.Sequence[_T]]:
    """
    Loads all values from a function that retrieves a queryset

    Django QuerySets are lazy, meaning that data is only retrieved when immediately referenced. All data must be
    retrieved at once if Django ORM data is to be used in asynchronous functions.

    MUST BE CALLED IF RETRIEVING DATA VIA THE DJANGO ORM.

    :param function: A function that returns a queryset
    :param args: Positional arguments passed to the function
    :param kwargs: Keyword arguments passed to the function
    :return: All values that would have been loaded through the lazy load
    """
    result: typing.Optional[QuerySet] = function(*args, **kwargs)

    if result and isinstance(result, QuerySet):
        return list(model for model in result)

    return result


async def communicate_with_database(function: typing.Callable[[typing.Any, ...], _T], *args, **kwargs) -> _T:
    """
    Use a function that has to use the Django database.

    Async functions can't typically communicate with the django database due to a safeguard used for protecting data
    in databases with a high volume of transactions. The general solution is to call a service that schedules the
    function execution. Instead of contacting a service, this will call the function in another thread and await the
    result.

    Args:
        function: The function to call
        *args: Positional arguments to use in the function call
        **kwargs: Keyword arguments to use in the function call

    Returns:
        The results of the function
    """
    prepared_function = functools.partial(get_values_eagerly, function, *args, **kwargs)
    result = await asyncio.get_running_loop().run_in_executor(None, prepared_function)
    return result

def wrapper_communicate(function: typing.Callable[[typing.Any, ...], _T], cwds_return_data: typing.MutableMapping, kwargs: typing.Mapping):
    results = function(**kwargs)

    if results and isinstance(results, QuerySet):
        cwds_return_data['results'] = list(model for model in results)
    else:
        cwds_return_data['results'] = results


def select_from_database(function: typing.Callable[[typing.Any, ...], _T], **kwargs) -> _T:
    _cwds_return_data = {
        "results": []
    }

    thread = threading.Thread(
        target=wrapper_communicate,
        kwargs={
            "function": function,
            "cwds_return_data": _cwds_return_data,
            "kwargs": kwargs
        }
    )

    thread.start()
    thread.join()

    return _cwds_return_data['results']
