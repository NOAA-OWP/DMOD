"""
Defines the base class for the DMOD Object Manager along with a protocol that may help prevent circular imports.
"""
from __future__ import annotations

import logging
import typing
import inspect
import uuid
import abc

from ..common import format_stack_trace
from ..common.protocols import LoggerProtocol

T = typing.TypeVar('T')
"""Represents some consistent yet generic type"""


def is_property(obj: object, member_name: str) -> bool:
    """
    Checks to see if a member of an object is a property

    Args:
        obj: The object to check
        member_name: The member on the object to check

    Returns:
        True if the member with the given name on the given object is a property
    """
    if not hasattr(obj, member_name):
        raise AttributeError(f"{obj} has no attribute '{member_name}'")

    if isinstance(obj, type):
        return isinstance(getattr(obj, member_name), property)

    # Is descriptor: inspect.isdatadescriptor(dict(inspect.getmembers(obj.__class__))[member_name])
    parent_reference = dict(inspect.getmembers(obj.__class__))[member_name]
    return isinstance(parent_reference, property)


@typing.runtime_checkable
class ObjectCreatorProtocol(typing.Protocol):
    """
    Defines the bare minimum methods that will be used that may create objects
    """
    def create_object(self, name: str, /, *args, **kwargs) -> T:
        """
        Create an object and store its reference

        Args:
            name: The name of the class to instantiate
            *args: Positional arguments used to instantiate the object
            **kwargs: Keyword arguments used to instantiate the object

        Returns:
            A proxy pointing at the instantiated object
        """


class ObjectManagerScope(abc.ABC):
    """
    Maintains references to objects that have been instantiated via an object manager within a specific scope
    """
    def __init__(self, name: str, logger: LoggerProtocol = None):
        self.__name = name
        self.__items: typing.List[typing.Any] = []
        self.__scope_id: uuid.UUID = uuid.uuid1()
        self.__on_close: typing.List[
            typing.Union[
                typing.Callable[[ObjectManagerScope], typing.Any],
                typing.Callable[[], typing.Any]
            ]
        ] = []
        # Record the 4th frame as to where this scope started
        # 0 = The `format_stack_trace` function
        # 1 = This constructor
        # 2 = The scope subclass' constructor
        # 3 = Where the object was instantiated
        self.__started_at: str = format_stack_trace(3)
        self.__logger: LoggerProtocol = logger or logging.getLogger()

    def _perform_on_close(self, handler: typing.Union[typing.Callable[[ObjectManagerScope], typing.Any], typing.Callable[[], typing.Any]]):
        if not isinstance(handler, typing.Callable):
            raise ValueError(
                f"The handler passed to {self.__class__.__name__}._perform_on_close must be a some sort of function "
                f"but got {type(handler)} instead"
            )

    @abc.abstractmethod
    def create_object(self, name: str, /, *args, **kwargs) -> T:
        """
        Create an object and store its reference

        Args:
            name: The name of the class to instantiate
            *args: Positional arguments used to instantiate the object
            **kwargs: Keyword arguments used to instantiate the object

        Returns:
            A proxy pointing at the instantiated object
        """

    def drop_references(self):
        """
        Delete all stored references within the context

        Objects referenced will not be deleted from the object Server as long as other entities carry a reference to
        them. Those instances will be marked for garbage collection once all references are lost
        """
        while self.__items:
            item = self.__items.pop()
            del item

    def __len__(self):
        return len(self.__items)

    def __contains__(self, item):
        return item in self.__items

    @property
    def name(self) -> str:
        """
        The name of the scope that will contain the objects
        """
        return self.__name

    @property
    def scope_id(self) -> uuid.UUID:
        """
        The ID for the scope that allows for easier tracking
        """
        return self.__scope_id

    @property
    def started_at(self) -> str:
        """
        A string expressing the stack trace of where this scope was created
        """
        return self.__started_at

    def add_instance(self, item):
        """
        Add an instance to the scope to trace

        Args:
            item: The item to track
        """
        self.__items.append(item)

    def __scope_closed(self):
        """
        Handle the situation where the scope of the contained objects has ended with additional functions
        """
        for handler in self.__on_close:
            if inspect.ismethod(handler):
                handler()
            else:
                handler(self)

    @property
    def logger(self) -> LoggerProtocol:
        return self.__logger

    @logger.setter
    def logger(self, logger: LoggerProtocol):
        self.__logger = logger

    def end_scope(self):
        """
        Override to add extra logic for when this scope is supposed to reach its end
        """
        self.drop_references()
        self.__scope_closed()

    def __del__(self):
        self.end_scope()

    def __str__(self):
        return f"Context: {self.name} [{len(self)} Items]"

    def __iter__(self):
        return iter(self.__items)

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return True
