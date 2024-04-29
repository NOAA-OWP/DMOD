"""
Defines a custom Context Manager
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import sys
import threading
import typing
import inspect
import platform

from multiprocessing import managers
from multiprocessing import RLock
from multiprocessing import util
from multiprocessing.context import BaseContext
from traceback import format_exc

from .decorators import version_range

_PREPARATION_LOCK: RLock = RLock()

SENTINEL = object()
"""A basic sentinel value to serve as a true 'null' value"""

T = typing.TypeVar("T")
"""Some generic type of object"""

Manager = typing.TypeVar("Manager", bound=managers.BaseManager, covariant=True)
"""Any type of manager object"""

ManagerType = typing.Type[Manager]
"""The type of a manager object itself"""

TypeOfRemoteObject = typing.Union[typing.Type[managers.BaseProxy], type]
"""A wrapper object that is used to communicate to objects created by Managers"""

_PROXY_TYPE_CACHE: typing.MutableMapping[typing.Tuple[str, typing.Tuple[str, ...]], TypeOfRemoteObject] = {}
"""A simple mapping of recently created proxies to remote objects"""

__ACCEPTABLE_DUNDERS = (
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__contains__",
    "__call__",
    "__iter__",
    "__gt__",
    "__ge__",
    "__lt__",
    "__le__",
    "__eq__",
    "__mul__",
    "__truediv__",
    "__floordiv__",
    "__mod__",
    "__sub__",
    "__add__",
    "__ne__",
    "__get_property__",
    "__set_property__",
    "__del_property__"
)
"""A collection of dunder names that are valid names for functions on proxies to shared objects"""

PROXY_SUFFIX: typing.Final[str] = "Proxy"
"""
Suffix for how proxies are to be named - naming proxies programmatically will ensure they are correctly referenced later
"""


@typing.runtime_checkable
class ProxiableGetPropertyProtocol(typing.Protocol):
    """
    Outline for a class that can explicitly retrieve a property value
    """
    def __get_property__(self, key: str) -> typing.Any:
        ...

@typing.runtime_checkable
class ProxiableSetPropertyProtocol(typing.Protocol):
    """
    Outline for a class that can explicitly set a property value
    """
    def __set_property__(self, key: str, value) -> None:
        ...


@typing.runtime_checkable
class ProxiableDeletePropertyProtocol(typing.Protocol):
    """
    Outline for a class that can explicitly delete a property value
    """
    def __del_property__(self, key: str) -> None:
        ...


class ProxiablePropertyMixin(ProxiableGetPropertyProtocol, ProxiableSetPropertyProtocol, ProxiableDeletePropertyProtocol):
    """
    Mixin functions that allow property functions (fget, fset, fdel) to be called explicitly rather than implicitly
    """
    def __get_property__(self, key: str) -> typing.Any:
        field = getattr(self.__class__, key)
        if not isinstance(field, property):
            raise TypeError(f"'{key}' is not a property of type '{self.__class__.__name__}'")

        if field.fget is None:
            raise Exception(f"Cannot retrieve the value for '{key}' on type '{self.__class__.__name__} - it is write-only")
        return field.fget(self)

    def __set_property__(self, key: str, value) -> None:
        field = getattr(self.__class__, key)
        if not isinstance(field, property):
            raise TypeError(f"'{key}' is not a property of type '{self.__class__.__name__}'")

        if field.fset is None:
            raise Exception(f"Cannot modify '{key}' on type '{self.__class__.__name__}' - it is read-only")

        field.fset(self, value)

    def __del_property__(self, key: str) -> None:
        field = getattr(self.__class__, key)
        if not isinstance(field, property):
            raise TypeError(f"'{key}' is not a property of type '{self.__class__.__name__}'")

        if field.fdel is None:
            raise Exception(f"The property '{key}' cannot be deleted from a type '{self.__class__.__name__}'")

        field.fdel(self)


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


def form_proxy_name(cls: type) -> str:
    """
    Programmatically form a name for a proxy class

    Args:
        cls: The class that will end up with a proxy
    Returns:
        The accepted name for a proxy class
    """
    if not hasattr(cls, "__name__"):
        raise TypeError(f"Cannot create a proxy name for {cls} - it has no consistent '__name__' attribute")

    return f"{cls.__name__}{PROXY_SUFFIX}"


def find_proxy(name: str) -> typing.Optional[typing.Type[managers.BaseProxy]]:
    """
    Retrieve a proxy class from the global context by name

    Args:
        name: The name of the proxy class to retrieve
    Returns:
        The proxy class that matches the name
    """
    if name not in globals():
        return None

    found_item = globals()[name]

    if not issubclass(found_item, managers.BaseProxy):
        raise TypeError(f"The item named '{name}' in the global context is not a proxy")

    return found_item


def member_should_be_exposed_to_proxy(member: typing.Any) -> bool:
    """
    Determine whether the member of a class should be exposed through a proxy

    Args:
        member: The member of a class that might be exposed

    Returns:
        True if the member should be accessible via the proxy
    """
    if inspect.isclass(member) or inspect.ismodule(member):
        return False

    if isinstance(member, property):
        return True

    member_is_callable = inspect.isfunction(member) or inspect.ismethod(member) or inspect.iscoroutinefunction(member)
    if not member_is_callable:
        return False

    member_name = getattr(member, "__name__", None)

    # Not having a name is not a disqualifier.
    # We want to include properties in this context and they won't have names here
    if member_name is None:
        return False

    # Double underscore functions/attributes (dunders in pythonic terms) are denoted by '__xxx__'
    # and are special functions that define things like behavior of `instance[key]`, `instance > other`,
    # etc. Only SOME of these are valid, so we need to ensure that these fall into the correct subset
    member_is_dunder = member_name.startswith("__") and member_name.endswith("__")

    if member_is_dunder:
        return member_name in __ACCEPTABLE_DUNDERS

    # A member is considered private if the name is preceded by '_'. Since these are private,
    # they shouldn't be used by outside entities, so we'll leave these out
    if member_name.startswith("_"):
        return False

    return True


def make_proxy_type(
    cls: typing.Type,
    exposure_criteria: typing.Callable[[typing.Any], bool] = None
) -> TypeOfRemoteObject:
    """
    Create a remote interface class with the given name and with the list of names of functions that may be
    called which will call the named functions on the remote object

    Args:
        cls: The class to create a proxy for
        exposure_criteria: A function that will decide if a bound object should be exposed through the proxy

    Returns:
        A proxy type that can be used to interact with the object instantiated in the manager process
    """
    if exposure_criteria is None:
        exposure_criteria = member_should_be_exposed_to_proxy

    logging.debug(f"Creating a proxy class for {cls.__name__} in process {os.getpid()}")

    # This dictionary will contain references to functions that will be placed in a dynamically generated proxy class
    new_class_members: typing.Dict[str, typing.Union[typing.Dict, typing.Callable, typing.Tuple]] = {}

    # Determine what members and their names to expose based on the passed in criteria for what is valid to expose
    members_to_expose = dict(inspect.getmembers(object=cls, predicate=exposure_criteria))
    lines_of_code: typing.List[str] = []
    for member_name, member in members_to_expose.items():
        if isinstance(member, property):
            if member.fget:
                lines_of_code.extend([
                    "@property",
                    f"def {member_name}(self):",
                    f"    return self._callmethod('{member_name}')"
                ])
            if member.fset:
                lines_of_code.extend([
                    f"@{member_name}.setter",
                    f"def {member_name}(self, value):",
                    f"    self._callmethod('{member_name}', (value,))"
                ])
        else:
            lines_of_code.extend([
                f"def {member_name}(self, /, *args, **kwargs):",
                f"    return self._callmethod('{member_name}', args, kwargs)"
            ])

    # '__hash__' is set to 'None' if '__eq__' is defined but not '__hash__'. Add a default '__hash__'
    #   if '__eq__' was defined and not '__hash__'
    if "__eq__" in members_to_expose and "__hash__" not in members_to_expose:
        lines_of_code.extend((
            "def __hash__(self, /, *args, **kwargs):",
            "    return hash(self._id)"
        ))
        members_to_expose["__hash__"] = None

    source_code = os.linesep.join(lines_of_code)

    # This is wonky, so I'll do my best to explain it
    #   `exec` compiles and runs the string that passes through it, with a reference to a dictionary
    #   for any variables needed when running the code. Even though 9 times out of 10 the dictionary
    #   only PROVIDES data, making the code text define a function ends up assigning that function
    #   BACK to the given dictionary that it considers to be the global scope.
    #
    # Being clever here and adding special handling via text for properties will cause issues later
    # down the line in regards to trying to call functions that are actually strings
    #
    # Linters do NOT like the `exec` function. This is one of the few cases where it should be used, so ignore warnings
    # for it
    exec(
        source_code,
        new_class_members
    )

    exposure_names = list(members_to_expose.keys())

    # Proxies need an '_exposed_' tuple to help direct what items to serve.
    #   Members whose names are NOT within the list of exposed names may not be called through the proxy.
    new_class_members["_exposed_"] = tuple(exposure_names)

    # Form a name programaticcally - other processes will need to reference this and they won't necessarily have the
    #   correct name for it if is isn't stated here
    name = form_proxy_name(cls)

    # The `class Whatever(ParentClass):` syntax is just
    #   `type("Whatever", (ParentClass,)  (function1, function2, function3, ...))` without the syntactical sugar.
    #   Invoke that here for dynamic class creation
    proxy_type: TypeOfRemoteObject = type(
        name,
        (managers.BaseProxy,),
        new_class_members
    )

    # Attach the type to the global scope
    #
    #   WARNING!!!!
    #
    # Failing to do this will limit the scope to which this class is accessible. If this isn't employed, the created
    # proxy class that is returned MUST be assigned to the outer scope via variable definition and the variable's
    # name MUST be the programmatically generated name employed here. Failure to do so will result in a class that
    # can't be accessed in other processes and scopes
    globals()[name] = proxy_type

    return proxy_type


def get_proxy_class(
    cls: typing.Type,
    exposure_criteria: typing.Callable[[typing.Any], bool] = None
) -> typing.Type[managers.BaseProxy]:
    """
    Get or create a proxy class based on the class that's desired to be used remotely
    Args:
        cls: The class that will have a proxy built
        exposure_criteria: A function that determines what values to expose when creating a new proxy type
    Returns:
        A new class type that may be used to communicate with a remote instance of the indicated class
    """
    proxy_name = form_proxy_name(cls=cls)
    proxy_type = find_proxy(name=proxy_name)

    # If a proxy was found, it may be returned with no further computation
    if proxy_type is not None:
        return proxy_type

    # ...Otherwise create a new one
    proxy_type = make_proxy_type(cls=cls, exposure_criteria=exposure_criteria)
    return proxy_type


@version_range(maximum_version="3.12.99")
class DMODObjectServer(managers.Server):
    """
    A multiprocessing object server that may serve non-callable values
    """
    def serve_client(self, conn):
        """
        Handle requests from the proxies in a particular process/thread

        This differs from the default Server implementation in that it allows access to exposed non-callables
        """
        util.debug('starting server thread to service %r', threading.current_thread().name)

        recv = conn.recv
        send = conn.send
        id_to_obj = self.id_to_obj

        while not self.stop_event.is_set():
            member_name: typing.Optional[str] = None
            object_identifier: typing.Optional[str] = None
            served_object = None
            args: tuple = tuple()
            kwargs: typing.Mapping = {}

            try:
                request = recv()
                object_identifier, member_name, args, kwargs = request
                try:
                    served_object, exposed_member_names, gettypeid = id_to_obj[object_identifier]
                except KeyError as ke:
                    try:
                        served_object, exposed_member_names, gettypeid = self.id_to_local_proxy_obj[object_identifier]
                    except KeyError as inner_keyerror:
                        raise inner_keyerror from ke

                if member_name not in exposed_member_names:
                    raise AttributeError(
                        f'Member {member_name} of {type(served_object)} object is not in exposed={exposed_member_names}'
                    )

                if not hasattr(served_object, member_name):
                    raise AttributeError(
                        f"{served_object.__class__.__name__} objects do not have a member named '{member_name}'"
                    )

                if is_property(served_object, member_name):
                    served_class_property: property = getattr(served_object.__class__, member_name)
                    if len(args) == 0:
                        value_or_function = served_class_property.fget
                        args = (served_object,)
                    else:
                        value_or_function = served_class_property.fset
                        args = (served_object,) + args
                else:
                    value_or_function = getattr(served_object, member_name)

                try:
                    if isinstance(value_or_function, typing.Callable):
                        result = value_or_function(*args, **kwargs)
                    else:
                        result = value_or_function
                except Exception as e:
                    msg = ('#ERROR', e)
                else:
                    typeid = gettypeid and gettypeid.get(member_name, None)
                    if typeid:
                        rident, rexposed = self.create(conn, typeid, result)
                        token = managers.Token(typeid, self.address, rident)
                        msg = ('#PROXY', (rexposed, token))
                    else:
                        msg = ('#RETURN', result)

            except AttributeError:
                if member_name is None:
                    msg = ('#TRACEBACK', format_exc())
                else:
                    try:
                        fallback_func = self.fallback_mapping[member_name]
                        result = fallback_func(self, conn, object_identifier, served_object, *args, **kwargs)
                        msg = ('#RETURN', result)
                    except Exception:
                        msg = ('#TRACEBACK', format_exc())

            except EOFError:
                util.debug('got EOF -- exiting thread serving %r', threading.current_thread().name)
                sys.exit(0)

            except Exception:
                msg = ('#TRACEBACK', format_exc())

            try:
                try:
                    send(msg)
                except Exception:
                    send(('#UNSERIALIZABLE', format_exc()))
            except Exception as e:
                util.info('exception in thread serving %r', threading.current_thread().name)
                util.info(' ... message was %r', msg)
                util.info(' ... exception was %r', e)
                conn.close()
                sys.exit(1)


class DMODObjectManager(managers.BaseManager):
    """
    An implementation of a multiprocessing context manager specifically for DMOD
    """
    __initialized: bool = False
    _Server = DMODObjectServer
    def __init__(
        self,
        address: typing.Tuple[str, int] = None,
        authkey: bytes = None,
        serializer: typing.Literal['pickle', 'xmlrpclib'] = 'pickle',
        ctx: BaseContext = None
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
        return DMODObjectServer(self._registry, self._address, self._authkey, self._serializer)

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
        # There is a bug that exists within autoproxies between 3.5 and 3.9 that tries to
        #   pass a removed parameter into a function. Since the fix came out too late into 3.8's
        #   lifetime, it was not backported, meaning that autoproxies are not valid prior to 3.9.
        #   Create a new proxy type in this case
        version_triple = tuple(int(version) for version in platform.python_version_tuple())

        if type_of_proxy is None and version_triple < (3, 9):
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

    def create_object(self, name, /, *args, **kwargs) -> T:
        """
        Create an item by name

        This can be used to bypass a linter

        Args:
            name: The name of the object on the manager to create
            *args: Positional arguments for the object
            **kwargs: Keyword arguments for the object

        Returns:
            A proxy to the newly created object
        """
        function = getattr(self, name, None)

        if function is None:
            raise KeyError(f"{self.__class__.__name__} has no item named '{name}' that may be created remotely")

        return function(*args, **kwargs)