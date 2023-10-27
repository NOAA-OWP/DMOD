"""
Defines a wrapper class for Django models that may function within an async context
"""
from __future__ import annotations

import typing
import threading

from django.db import models as django_models
from django.db.models import Q
from django.db.models import QuerySet

_MODEL_TYPE = typing.TypeVar("_MODEL_TYPE", bound=django_models.Model, covariant=True)


class WrapperResults:
    def __init__(self):
        self.__single_value = None
        self.__multiple_values = list()
        self.__mapping = dict()

    @property
    def value(self):
        if self.__single_value is not None:
            return self.__single_value
        elif len(self.__mapping) > 0:
            return {key: value for key, value in self.__mapping.items()}

        return [value for value in self.__multiple_values]

    @value.setter
    def value(self, new_value):
        self.__multiple_values.clear()
        self.__single_value = None
        self.__mapping.clear()
        if isinstance(new_value, typing.Iterable) and not isinstance(new_value, (str, bytes, typing.Mapping)):
            for value in new_value:
                self.__multiple_values.append(value)
        elif isinstance(new_value, typing.Mapping):
            self.__mapping.update(new_value)
        else:
            self.__single_value = new_value

    def __iter__(self):
        if self.__single_value is not None:
            return iter([self.__single_value])
        elif len(self.__mapping) > 0:
            return iter(self.__mapping.items())
        return iter(self.__multiple_values)

    def __repr__(self):
        return str(self.value)


_T = typing.TypeVar("_T")
_V = typing.TypeVar("_V")

class wrapper_fn(typing.Protocol, typing.Generic[_T, _V]):
    def __call__(self, *args: _T, **kwargs: _V) -> typing.Union[_MODEL_TYPE, typing.Sequence[_MODEL_TYPE]]:
        ...


def wrapper_caller(
    function: wrapper_fn[_T, _V],
    _wrapper_return_values: WrapperResults,
    args: typing.Sequence[_T],
    kwargs: typing.Mapping[str, _V],
):
    try:
        function_results = function(*args, **kwargs)

        # A queryset might have nested lazy objects, so call 'get' on each to attempt to fully load them
        if isinstance(function_results, QuerySet):
            processed_results = list()

            if "values" not in function.__name__:
                function_results = function_results.select_related()

            for instance in function_results.all():
                processed_results.append(instance)

            function_results = processed_results

        _wrapper_return_values.value = function_results
    except BaseException as e:
        _wrapper_return_values.value = e


class ModelWrapper(typing.Generic[_MODEL_TYPE]):
    @classmethod
    def for_model(cls, model_type: typing.Type[_MODEL_TYPE]) -> ModelWrapper[_MODEL_TYPE]:
        return ModelWrapper(model_type=model_type)

    def __init__(self, model_type: typing.Type[_MODEL_TYPE]):
        self.__model_type: typing.Type[_MODEL_TYPE] = model_type
        self.__manager: django_models.Manager = self.__model_type.objects

        # SQLite cannot handle multiple threads well and ends up locking and causing locking errors.
        #   If the database being used is determined to be SQLite, avoid threading
        self.__can_use_concurrency = True

    def enable_concurrency(self):
        self.__can_use_concurrency = True
        return self

    def disable_concurrency(self):
        self.__can_use_concurrency = False
        return self

    def __call_wrapper(
        self,
        function: wrapper_fn[_T, _V],
        *args: _T,
        **kwargs: _V,
    ) -> typing.Union[_MODEL_TYPE, typing.Sequence[_MODEL_TYPE]]:
        results = WrapperResults()

        if self.__can_use_concurrency:
            caller_thread = threading.Thread(
                target=wrapper_caller,
                kwargs={
                    "function": function,
                    "_wrapper_return_values": results,
                    "args": args,
                    "kwargs": kwargs
                }
            )

            caller_thread.start()
            caller_thread.join()
        else:
            wrapper_caller(function=function, _wrapper_return_values=results, args=args, kwargs=kwargs)

        if isinstance(results.value, BaseException):
            raise results.value

        for value in results:
            if isinstance(value, django_models.Model):
                setattr(value, "objects", ModelWrapper.for_model(value.__class__))

        return results.value

    async def aaggregate(self, *args, **kwargs):
        """
        Return a dictionary containing the calculations (aggregation)
        over the current queryset.

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.
        """
        return self.__call_wrapper(
            self.__manager.aggregate,
            *args,
            **kwargs
        )

    async def abulk_create(
        self,
        models,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ) -> list:
        return self.__call_wrapper(
            self.__manager.bulk_create,
            objs=models,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields
        )

    async def abulk_update(self, models, fields, batch_size=None) -> int:
        return self.__call_wrapper(
            self.__manager.bulk_update,
            objs=models,
            fields=fields,
            batch_size=batch_size
        )

    async def acontains(self, model) -> bool:
        return self.__call_wrapper(
            self.__manager.contains,
            obj=model
        )

    async def acount(self) -> int:
        return self.__call_wrapper(
            self.__manager.count
        )

    async def acreate(self, **kwargs) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.create,
            **kwargs
        )

    async def aearliest(self, *fields) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.earliest,
            *fields
        )

    async def aexists(self) -> bool:
        return self.__call_wrapper(
            self.__manager.exists
        )

    async def afirst(self) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.first
        )

    async def aget(self, *args, **kwargs) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.get,
            *args,
            **kwargs
        )

    async def aget_or_create(self, defaults=None, **kwargs) -> typing.Tuple[_MODEL_TYPE, bool]:
        return self.__call_wrapper(
            self.__manager.get_or_create,
            defaults=defaults,
            **kwargs
        )

    def aggregate(self, *args, **kwargs) -> dict:
        """

        Return a dictionary containing the calculations (aggregation)
        over the current queryset.

        If args is present the expression is passed as a kwarg using
        the Aggregate object's default alias.

        """
        return self.__call_wrapper(
            self.__manager.aggregate,
            *args,
            **kwargs
        )

    async def alast(self) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.last
        )

    async def alatest(self, *fields) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.latest,
            *fields
        )

    def all(self) -> typing.List[_MODEL_TYPE]:
        return self.__call_wrapper(
            self.__manager.all
        )

    async def aupdate(self, **kwargs) -> int:
        return self.__call_wrapper(
            self.__manager.update,
            **kwargs
        )

    async def aupdate_or_create(self, defaults=None, **kwargs) -> typing.Tuple[_MODEL_TYPE, bool]:
        return self.__call_wrapper(
            self.__manager.update_or_create,
            defaults=defaults,
            **kwargs
        )

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ) -> typing.List[_MODEL_TYPE]:
        """

        Insert each of the instances into the database. Do *not* call
        save() on each of the instances, do not send any pre/post_save
        signals, and do not set the primary key attribute if it is an
        autoincrement field (except if features.can_return_rows_from_bulk_insert=True).
        Multi-table models are not supported.

        """
        return self.__call_wrapper(
            self.__manager.bulk_create,
            objs=objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields
        )

    def bulk_update(self, objs, fields, batch_size=None) -> int:
        """

        Update the given fields in each of the given objects in the database.

        """
        return self.__call_wrapper(
            self.__manager.bulk_update,
            objs=objs,
            fields=fields,
            batch_size=batch_size
        )

    def complex_filter(self, filter_obj: typing.Union[Q, typing.Dict[str, typing.Any]]) -> typing.List[_MODEL_TYPE]:
        """

        Return a new list instance with filter_obj added to the filters.

        filter_obj can be a Q object or a dictionary of keyword lookup
        arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.

        """
        return self.__call_wrapper(
            self.__manager.complex_filter,
            filter_obj=filter_obj
        )

    def contains(self, model) -> bool:
        """
        Return True if the QuerySet contains the provided obj,
        False otherwise.
        """
        return self.__call_wrapper(
            self.__manager.contains,
            obj=model
        )

    def count(self) -> int:
        """

        Perform a SELECT COUNT() and return the number of records as an
        integer.

        If the QuerySet is already fully cached, return the length of the
        cached results set to avoid multiple SELECT COUNT(*) calls.

        """
        return self.__call_wrapper(
            self.__manager.count
        )

    def create(self, **kwargs) -> _MODEL_TYPE:
        """

        Create a new object with the given kwargs, saving it to the database
        and returning the created object.

        """
        return self.__call_wrapper(
            self.__manager.create,
            **kwargs
        )

    def distinct(self, *field_names) -> typing.List[_MODEL_TYPE]:
        """

        Return a new list instance that will select only distinct results.

        """
        return self.__call_wrapper(
            self.__manager.distinct,
            *field_names
        )

    def earliest(self, *fields) -> _MODEL_TYPE:
        return self.__call_wrapper(
            self.__manager.earliest,
            *fields
        )

    def exclude(self, *args, **kwargs) -> typing.List[_MODEL_TYPE]:
        """

        Return a new QuerySet instance with NOT (args) ANDed to the existing
        set.

        """
        return self.__call_wrapper(
            self.__manager.exclude,
            *args,
            **kwargs
        )

    def exists(self) -> bool:
        """

        Return True if the QuerySet would have any results, False otherwise.

        """
        return self.__call_wrapper(
            self.__manager.exists
        )

    def filter(self, *args, **kwargs) -> typing.List[_MODEL_TYPE]:
        """

        Return a new QuerySet instance with the args ANDed to the existing
        set.

        """
        return self.__call_wrapper(
            self.__manager.filter,
            *args,
            **kwargs
        )

    def first(self) -> _MODEL_TYPE:
        """
        Return the first object of a query or None if no match is found.
        """
        return self.__call_wrapper(
            self.__manager.first
        )

    def get(self, *args, **kwargs) -> _MODEL_TYPE:
        """

        Perform the query and return a single object matching the given
        keyword arguments.

        """
        return self.__call_wrapper(
            self.__manager.get,
            *args,
            **kwargs
        )

    def get_or_create(self, defaults=None, **kwargs) -> typing.Tuple[_MODEL_TYPE, bool]:
        """

        Look up an object with the given kwargs, creating one if necessary.
        Return a tuple of (object, created), where created is a boolean
        specifying whether an object was created.

        """
        return self.__call_wrapper(
            self.__manager.get_or_create,
            defaults=None,
            **kwargs
        )

    def last(self) -> _MODEL_TYPE:
        """
        Return the last object of a query or None if no match is found.
        """
        return self.__call_wrapper(
            self.__manager.last
        )

    def latest(self, *fields) -> _MODEL_TYPE:
        """

        Return the latest object according to fields (if given) or by the
        model's Meta.get_latest_by.

        """
        return self.__call_wrapper(
            self.__manager.latest,
            *fields
        )

    def order_by(self, *field_names) -> typing.List[_MODEL_TYPE]:
        """
        Return a new QuerySet instance with the ordering changed.
        """
        return self.__call_wrapper(
            self.__manager.order_by,
            *field_names
        )

    def prefetch_related(self, *lookups) -> typing.List[_MODEL_TYPE]:
        """

        Return a new QuerySet instance that will prefetch the specified
        Many-To-One and Many-To-Many related objects when the QuerySet is
        evaluated.

        When prefetch_related() is called more than once, append to the list of
        prefetch lookups. If prefetch_related(None) is called, clear the list.

        """
        return self.__call_wrapper(
            self.__manager.prefetch_related,
            *lookups
        )

    def raw(self, raw_query, params=(), translations=None, using=None) -> typing.List[_MODEL_TYPE]:
        return self.__call_wrapper(
            self.__manager.raw,
            raw_query=raw_query,
            params=params,
            translations=translations,
            using=using
        )

    def reverse(self) -> typing.List[_MODEL_TYPE]:
        """
        Reverse the ordering of the QuerySet.
        """
        return self.__call_wrapper(
            self.__manager.reverse
        )

    def select_related(self, *fields) -> typing.List[_MODEL_TYPE]:
        """

        Return a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.

        If select_related(None) is called, clear the list.

        """
        return self.__call_wrapper(
            self.__manager.select_related,
            *fields
        )

    def update(self, **kwargs) -> int:
        """

        Update all elements in the current QuerySet, setting all the given
        fields to the appropriate values.

        """
        return self.__call_wrapper(
            self.__manager.update,
            **kwargs
        )

    def update_or_create(self, defaults=None, **kwargs) -> typing.Tuple[_MODEL_TYPE, bool]:
        """
        Look up an object with the given kwargs, updating one with defaults
        if it exists, otherwise create a new one.
        Return a tuple (object, created), where created is a boolean
        specifying whether an object was created.
        """
        return self.__call_wrapper(
            self.__manager.update_or_create,
            defaults=defaults,
            **kwargs
        )

    def values(self, *fields, **expressions) -> typing.Sequence[typing.Dict]:
        return self.__call_wrapper(
            self.__manager.values,
            *fields,
            **expressions
        )

    def values_list(self, *fields, flat=False, named=False) -> typing.Sequence[typing.Tuple]:
        return self.__call_wrapper(
            self.__manager.values_list,
            *fields,
            flat=flat,
            named=named
        )

    def __str__(self):
        return f"Wrapper for {self.__model_type}"

    def __repr__(self):
        return f"{str(self.__model_type)}: {'Concurrent' if self.__can_use_concurrency else 'Synchronous'}"