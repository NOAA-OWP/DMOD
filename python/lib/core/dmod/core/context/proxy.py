"""
@TODO: Put a module wide description here
"""
from __future__ import annotations

import typing
import logging
import inspect
import os

from multiprocessing import managers

from .base import is_property
from ..common.protocols import LoggerProtocol

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
    exposure_criteria: typing.Callable[[typing.Any], bool] = None,
    logger: LoggerProtocol = None
) -> TypeOfRemoteObject:
    """
    Create a remote interface class with the given name and with the list of names of functions that may be
    called which will call the named functions on the remote object

    Args:
        cls: The class to create a proxy for
        exposure_criteria: A function that will decide if a bound object should be exposed through the proxy
        logger: An optional logger to use for debugging purposes

    Returns:
        A proxy type that can be used to interact with the object instantiated in the manager process
    """
    if logger is None:
        logger = logging.getLogger()

    if exposure_criteria is None:
        exposure_criteria = member_should_be_exposed_to_proxy

    logger.debug(f"Creating a proxy class for {cls.__name__} in process {os.getpid()}")

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
