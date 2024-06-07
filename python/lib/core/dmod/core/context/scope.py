"""
Defines a concrete Scope subclass that may create and remove instances of shared objects through a DMODObjectManager
"""
from __future__ import annotations

from functools import partial
from concurrent import futures

from .base import ObjectManagerScope
from .base import T
from .manager import DMODObjectManager


class DMODObjectManagerScope(ObjectManagerScope):
    """
    Tracks the objects created by an instance of the DMODObjectManager in order to maintain their scope

    The object will remain within the Server as long as there is a single reference to it. This will maintain
    reference to all objects that pertain to a specific scope.
    """
    def __init__(self, name: str, object_manager: DMODObjectManager):
        super().__init__(name)
        self.__object_manager: DMODObjectManager = object_manager
        self._perform_on_close(partial(self.__object_manager.free, self.scope_id))

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
        instance = self.__object_manager.create_object(name, *args, **kwargs)
        self.add_instance(instance)
        return instance

    def monitor(self, operation: futures.Future[T]):
        """
        Monitor the given operation and remove references to this scope when its done

        Args:
            operation: The operation to track
        """
        self.__object_manager.monitor_operation(scope=self, operation=operation)
