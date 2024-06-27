"""
Defines the DMODObjectManager class which provides distributed object functionality
"""
from __future__ import annotations

import logging
import typing
import multiprocessing

from concurrent import futures

from multiprocessing import managers
from multiprocessing import context
from multiprocessing import RLock

from .base import ObjectManagerScope
from .base import T
from .server import DMODObjectServer
from .monitor import FutureMonitor
from .proxy import get_proxy_class
from ..common.protocols import LoggerProtocol

TypeOfRemoteObject = typing.Union[typing.Type[managers.BaseProxy], type]
"""A wrapper object that is used to communicate to objects created by Managers"""

_PREPARATION_LOCK: RLock = RLock()


class DMODObjectManager(managers.BaseManager):
    """
    An implementation of a multiprocessing context manager specifically for DMOD
    """

    def __str__(self):
        representation = self.__class__.__name__

        if self.address and self.__monitor_scope:
            representation += f" at {self.address} "
            representation += f"and monitoring objects through a {self.__scope_monitor.__class__.__name__}"
        elif self.address:
            representation += f" at {self.address} "
        elif self.__monitor_scope:
            representation += f" monitoring objects through a {self.__scope_monitor.__class__.__name__}"

        return representation

    def __repr__(self):
        return self.__str__()

    __initialized: bool = False
    _Server = DMODObjectServer

    def __init__(
        self,
        address: typing.Tuple[str, int] = None,
        authkey: bytes = None,
        serializer: typing.Literal['pickle', 'xmlrpclib'] = 'pickle',
        ctx: context.BaseContext = None,
        scope_creator: typing.Callable[[str, DMODObjectManager], ObjectManagerScope] = None,
        monitor_scope: bool = False,
        logger: LoggerProtocol = None
    ):
        """
        Constructor

        Args:
            address: the address on which the manager process listens for new connections.
                If address is None then an arbitrary one is chosen.
            authkey: the authentication key which will be used to check the validity of
                incoming connections to the server process. If authkey is None then current_process().authkey is used.
                Otherwise authkey is used and it must be a byte string.
            serializer: The type of serializer to use when sending messages to the server containing the remote objects
            ctx: context object which has the same attributes as the multiprocessing module.
                The results of `get_context` if None
        """
        self.__class__.prepare()
        self.__scope_creator = scope_creator
        self.__scopes: typing.Dict[str, ObjectManagerScope] = {}
        self.__monitor_scope = monitor_scope
        self.__logger: LoggerProtocol = logger or logging.getLogger()
        self.__scope_monitor = FutureMonitor(logger=self.__logger) if monitor_scope else None
        super().__init__(address=address, authkey=authkey, serializer=serializer, ctx=ctx)

    def get_server(self):
        """
        Return server object with serve_forever() method and address attribute
        """
        if self._state.value != managers.State.INITIAL:
            if self._state.value == managers.State.STARTED:
                raise multiprocessing.ProcessError("Already started server")
            elif self._state.value == managers.State.SHUTDOWN:
                raise multiprocessing.ProcessError("Manager has shut down")
            else:
                raise multiprocessing.ProcessError(f"Unknown state {self._state.value}")
        return DMODObjectServer(self._registry, self.address, self._authkey, self._serializer)

    @classmethod
    def register_class(
        cls,
        class_type: type,
        type_of_proxy: TypeOfRemoteObject = None
    ) -> typing.Type[DMODObjectManager]:
        """
        Add a class to the builder that may be reached remotely

        Args:
            class_type: The class to register
            type_of_proxy: The class that will define how to communicate with the remote instance
        """
        # An automagical proxy may be created in python 3.9+. That is being avoided here because the proxy created
        # here is more robust
        if type_of_proxy is None:
            type_of_proxy = get_proxy_class(class_type)

        super().register(
            typeid=class_type.__name__,
            callable=class_type,
            proxytype=type_of_proxy
        )
        return cls

    @classmethod
    def prepare(
        cls,
        additional_proxy_types: typing.Mapping[type, typing.Optional[TypeOfRemoteObject]] = None
    ) -> typing.Type[DMODObjectManager]:
        """
        Attatches all proxies found on the SyncManager to this Manager to maintain parity and function.
        Will also attach additionally provided proxies

        Args:
            additional_proxy_types: A mapping between class types and the type of proxies used to operate
                upon them remotely
        """
        with _PREPARATION_LOCK:
            if not cls.__initialized:
                if not isinstance(additional_proxy_types, typing.Mapping):
                    additional_proxy_types = {}

                already_registered_items: typing.List[str] = list(getattr(cls, "_registry").keys())

                for real_class, proxy_class in additional_proxy_types.items():
                    name = real_class.__name__ if hasattr(real_class, "__name__") else None

                    if name is None:
                        raise TypeError(f"Cannot add a proxy for {real_class} - {real_class} is not a standard type")

                    if name in already_registered_items:
                        print(f"'{name}' is already registered to {cls.__name__}")
                        continue

                    cls.register_class(class_type=real_class, type_of_proxy=proxy_class)
                    already_registered_items.append(name)

                # Now find all proxies attached to the SyncManager and attach those
                # This will ensure that this manager has proxies for objects and structures like dictionaries
                registry_initialization_arguments = (
                    {
                        "typeid": typeid,
                        "callable": attributes[0],
                        "exposed": attributes[1],
                        "method_to_typeid": attributes[2],
                        "proxytype": attributes[3]
                    }
                    for typeid, attributes in getattr(managers.SyncManager, "_registry").items()
                    if typeid not in already_registered_items
                )

                for arguments in registry_initialization_arguments:
                    cls.register(**arguments)

            cls.__initialized = True
            return cls

    def create_and_track_object(self, __class_name: str, __scope_name: str, /, *args, **kwargs) -> T:
        """
        Create an item by name

        This can be used to bypass a linter

        Args:
            __class_name: The name of the object on the manager to create
            __scope_name: A key used to cache and keep track of the generated proxy object
            *args: Positional arguments for the object
            **kwargs: Keyword arguments for the object

        Returns:
            A proxy to the newly created object
        """
        if isinstance(__scope_name, bytes):
            __scope_name = __scope_name.decode()

        if not isinstance(__scope_name, str):
            raise TypeError(
                f"The tracking key used when creating a '{__class_name}' object must be a str. "
                f"Received '{__scope_name}' ({type(__scope_name)})"
            )

        if __scope_name not in self.__scopes:
            self.establish_scope(__scope_name)

        new_instance = self.create_object(__class_name, *args, **kwargs)

        self.__scopes[__scope_name].add_instance(new_instance)

        return new_instance

    def create_object(self, __class_name, /, *args, **kwargs) -> T:
        """
        Create an item by name

        This can be used to bypass a linter

        Args:
            __class_name: The name of the object on the manager to create
            *args: Positional arguments for the object
            **kwargs: Keyword arguments for the object

        Returns:
            A proxy to the newly created object
        """
        function = getattr(self, __class_name, None)

        if function is None:
            raise KeyError(f"{self.__class__.__name__} has no item named '{__class_name}' that may be created remotely")

        value = function(*args, **kwargs)

        return value

    def free(self, scope_name: str):
        """
        Remove all items associated with a given tracking key from the object manager

        Args:
            scope_name: The key used to keep track of like items

        Returns:
            The number of items that were deleted
        """
        if not scope_name:
            raise ValueError(f"Cannot free resources from {self}. No tracking key provided")

        if not isinstance(scope_name, str):
            raise TypeError(
                f"The tracking key used freeing data must be a string. "
                f"Received '{scope_name}' ({type(scope_name)}"
            )

        if scope_name not in self.__scopes:
            raise KeyError(f"Cannot free objects from {self} - no items are tracked by the key {scope_name}")

        del self.__scopes[scope_name]

    def __inject_scope(self, scope: ObjectManagerScope):
        """
        Adds a scope object to the manager

        Args:
            scope: The scope object to add
        """
        if scope.name in self.__scopes:
            raise KeyError(
                f"Cannot add a scope object '{scope.name}' to {self} - there is already a scope by that name. "
                f"Evaluate the implementation of {self.__scope_creator} to ensure that it does not "
                f"yield conflicting names."
            )

        self.__scopes[scope.name] = scope

    def establish_scope(self, name: str) -> ObjectManagerScope:
        """
        Create a scope that will track objects for a workflow context

        Args:
            name: The name for the scope

        Returns:
            A scope object
        """
        if not self.__scope_creator:
            raise RuntimeError(
                f"Cannot establish a context for {self} - "
                f"no scope creation function was given at {self.__class__.__name__} instantiation"
            )

        scope = self.__scope_creator(name, self)
        self.__inject_scope(scope)

        return scope

    def monitor_operation(self, scope: typing.Union[ObjectManagerScope, str, bytes], operation: futures.Future):
        """
        Monitor a parallel operation and remove the associated scope when it is completed

        Args:
            scope: A scope object containing references to shared objects that need to be kept alive
            operation: The operation using the shared objects
        """
        if not self.__monitor_scope or not self.__scope_monitor:
            if isinstance(scope, ObjectManagerScope):
                scope_name = scope.name
            elif isinstance(scope, bytes):
                scope_name = scope.decode()
            else:
                scope_name = str(scope)

            raise RuntimeError(
                f"Cannot monitor an operation using the scope {scope_name} as this {self.__class__.__name__} "
                f"is not set up to monitor operations"
            )

        if isinstance(scope, bytes):
            scope = scope.decode()

        if not isinstance(operation, futures.Future):
            raise ValueError(
                f"Cannot monitor an operation using the scope '{scope}' if the object is not a Future-like object"
            )

        if isinstance(scope, str):
            # Throw an error if the scope doesn't exist - there's nothing to monitor if it's not there
            if scope not in self.__scopes:
                raise KeyError(
                    f"Cannot monitor an operation for the scope named '{scope}' - "
                    f"the scope doesn't exist within this manager"
                )
            scope = self.__scopes[scope]
        elif not isinstance(scope, ObjectManagerScope):
            raise ValueError(f"Cannot monitor an operation for a scope of type {type(scope)}")
        elif scope.name not in self.__scopes:
            raise KeyError(
                f"Cannot monitor an operation for the scope named '{scope}' - "
                f"the scope doesn't exist within this manager"
            )

        self.logger.info(f"Preparing to monitor the scope for '{scope.name}'")
        self.__scope_monitor.add(scope=scope, value=operation)

    @property
    def logger(self) -> LoggerProtocol:
        return self.__logger

    @logger.setter
    def logger(self, logger: LoggerProtocol):
        """
        Set the logger on this and all entities owned by this

        Args:
            logger: The logger to attach
        """
        self.__logger = logger

        # The scopes handle work for the manager. If this logger is set, set the logger on all the scopes to ensure
        # that everything is written in the correct places
        for scope in self.__scopes.values():
            scope.logger = logger

        # As above, the scope monitor serves at the pleasure of the manager. If the logger is set here, make sure
        # the logger on the monitor is kept up to speed.
        if self.__scope_monitor:
            self.__scope_monitor.logger = logger
