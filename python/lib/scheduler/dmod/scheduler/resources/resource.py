from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union
from typing_extensions import Self
from pydantic import Field, Extra, validator, root_validator
from warnings import warn
import sys
# TODO: remove guard when 3.8 support is dropped
if sys.version_info >= (3, 9):
    from functools import cache
else:
    # support python <= 3.8
    # functools.cache introduced in 3.9
    # https://docs.python.org/3.9/library/functools.html#functools.cache
    # > Returns the same as lru_cache(maxsize=None)
    from functools import lru_cache
    cache = lru_cache(maxsize=None)


from dmod.core.enum import PydanticEnum
from dmod.core.serializable import Serializable


class ResourceAvailability(PydanticEnum):
    ACTIVE = 1,
    INACTIVE = 2,
    UNKNOWN = -1


class ResourceState(PydanticEnum):
    READY = 1
    NOT_READY = 2,
    UNKNOWN = -1


class AbstractProcessingAssetPool(Serializable, ABC):
    """
    Abstract representation of some collection of assets used for processing jobs/tasks.

    Objects of this type consist of a certain number of processors and certain amount of memory.  This base type does
    not impose restrictions on whether these values may change over time.

    Objects of this type can also be converted to and from serialized dictionaries, with deserialization done using the
    ::method:`factory_init_from_dict` class method, and serialization using the ::method:`to_dict` method.
    """

    cpu_count: int
    memory: int
    pool_id: str
    unique_id_separator: str = ":"

    @classmethod
    def factory_init_from_dict(cls, init_dict: Dict[str, Any],
                               ignore_extra_keys: bool = False) -> Self:
        """
        Initialize a new object from the given dictionary, raising a ::class:`ValueError` if there are missing expected
        keys or there are extra keys when the method is not set to ignore them.

        The dictionary should include the same string keys used in the implementation of ::method:`to_dict`.  Values
        should also typically be similar, though additional value types may be supported where appropriate.  In
        particular, conversions of string values to integer init params (or other numeric types) is likely to be common,
        but other value conversions may be supported also.

        Case sensitivity for keys is ignored.  However, a side effect of this is that if there are "extra" keys in the
        form of like keys with different capitalization, which key is used to source a parameter value will be
        determined according to the rules of iterating through dictionaries, with the first applicable key/value being
        used.

        If there are any additional, unexpected keys, they will trigger a ::class:`ValueError` unless the
        ``ignore_extra_keys`` is set to ``True``.  It is ``False`` by default.

        Parameters
        ----------
        init_dict : dict
            The dictionary from which to initialize a new object.

        ignore_extra_keys : bool
            Whether the method should just ignore any unrecognized dictionary keys, as opposed to raising a ValueError,
            which is ``False`` by default.

        Returns
        -------
        SingleHostProcessingAssetPool
            A newly initialized ::class:`AbstractProcessingResource` object.

        Raises
        ------
        ValueError
            If there are extra keys in the parameter dictionary and ``ignore_extra_keys`` is ``False``.

        TypeError
            If any parameters sourced from the init dictionary are not of a supported type for that param.
        """
        original_extra_level = getattr(cls.Config, "extra", None)

        if ignore_extra_keys:
            setattr(cls.Config, "extra", Extra.ignore)
        else:
            setattr(cls.Config, "extra", Extra.forbid)

        o = cls.parse_obj(init_dict)

        if original_extra_level is None:
            delattr(cls.Config, "extra")
        else:
            setattr(cls.Config, "extra", original_extra_level)

        return o

    class Config:
        extra = Extra.forbid

    @property
    @abstractmethod
    def unique_id(self):
        """
        A unique identifier for this object.

        Returns
        -------
        A unique identifier for this object.
        """
        pass


class SingleHostProcessingAssetPool(AbstractProcessingAssetPool, ABC):
    """
    An extension of ::class:`AbstractProcessingAssetPool` where the represented assets all exist on a single logical
    host.

    , and they will have resource/node
    identifiers and hostnames for the host on which the resources exists, which should not be modified after object
    creation.
    """

    hostname: str


class Resource(SingleHostProcessingAssetPool):
    """
    Representation of a resource from which processing assets can be allocated.

    E.g.:
            {
                'node_id': "Node-0001",
                'Hostname': "my-host",
                'Availability': "active",
                'State': "ready",
                'CPUs': 18,
                'MemoryBytes': 33548128256,
                'Total CPUs': 18,
                'Total Memory: 33548128256
            }

    The ::attribute:`resource_id` property is expected to be unique within the domain of ::class:`Resource` objects.

    In addition to the ::attribute:`cpu_count` and ::attribute:`memory` properties, which represent available values for
    the resource, resources also maintain ::attribute:`total_cpu_count` and ::attribute:`total_memory` properties.
    These are initially set to the available values if no explicit values are set at initialization.  In general, these
    are expected to never change for a resource.
    """

    availability: ResourceAvailability
    """
    The availability of the resource.

    Note that the property setter accepts both string and ::class:`ResourceAvailability` values.  For a string, the
    argument is converted to a ::class:`ResourceAvailability` value using ::method:`get_resource_enum_value`.

    However, if the conversion of a string with ::method:`get_resource_enum_value` returns ``None``, the setter
    sets ::attribute:`availability` to the ``UNKNOWN`` enum value, rather than ``None``.  This is more applicable
    and allows the getter to always return an actual ::class:`ResourceAvailability` instance.
    """

    state: ResourceState = Field(description="The readiness state of the resource.")
    """
    Note that the property setter accepts both string and ::class:`ResourceState` values.  For a string, the
    argument is converted to a ::class:`ResourceState` value using ::method:`get_resource_enum_value`.

    However, if the conversion of a string with ::method:`get_resource_enum_value` returns ``None``, the setter sets
    ::attribute:`state` to the ``UNKNOWN`` enum value, rather than ``None``.  This is more applicable and allows the
    getter to always return an actual ::class:`ResourceState` instance.
    """

    total_cpus: Optional[int] = Field(description="The total number of CPUs known to be on this resource.")

    total_memory: Optional[int] = Field(description="The total amount of memory known to be on this resource.")

    class Config:
        fields = {
            "availability": {"alias": "Availability"},
            "cpu_count": {"alias": "CPUs"},
            "hostname": {"alias": "Hostname"},
            "memory": {"alias": "MemoryBytes"},
            "pool_id": {"alias": "node_id"},
            "state": {"alias": "State"},
            "total_cpus": {"alias": "Total CPUs"},
            "total_memory": {"alias": "Total Memory"},
            "unique_id_separator": {"exclude": True}
        }

    @validator("availability", pre=True)
    def _validate_availability(cls, value: Optional[Any]) -> Union[Any, ResourceAvailability]:
        if value is None:
            return ResourceAvailability.UNKNOWN
        return value

    @validator("state", pre=True)
    def _validate_state(cls, value: Optional[Any]) -> Union[Any, ResourceState]:
        if value is None:
            return ResourceState.UNKNOWN
        return value

    @root_validator(pre=True)
    def _remap_alias_case_insensitive(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        alias_field_map = cls._alias_field_map()

        # NOTE: consider removing this in the future and enforcing case sensitive keys
        new_values: Dict[str, Any] = dict()
        for k, v in values.items():
            if k.lower() in alias_field_map:
                new_values[alias_field_map[k.lower()]] = v
                continue
            new_values[k] = v
        return new_values

    @root_validator()
    def _set_total_cpus_and_total_memory_if_unset(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get("total_cpus") is None:
            values["total_cpus"] = values["cpu_count"]

        if values.get("total_memory") is None:
            values["total_memory"] = values["memory"]

        msg_template = "`{}` cannot be larger than `{}`. {} > {}"
        if values["cpu_count"] > values["total_cpus"]:
            raise ValueError(msg_template.format("cpu_count", "total_cpus", values["cpu_count"], values["total_cpus"]))

        if values["memory"] > values["total_memory"]:
            raise ValueError(msg_template.format("memory", "total_memory", values["memory"], values["total_memory"]))

        return values

    @classmethod
    @cache
    def _alias_field_map(cls) -> Dict[str, str]:
        """Mapping of lower cased alias names to cased alias names."""
        return {v.alias.lower(): v.alias for v in cls.__fields__.values()}

    @classmethod
    def generate_unique_id(cls, resource_id: str, separator: str):
        """
        For an arbitrary resource id string, generate the appropriate derived value for ::attribute:`unique_id`, which
        can be used for things such as Redis keys.

        Parameters
        ----------
        resource_id
        separator

        Returns
        -------
        str
            The derived unique id.
        """
        return f"{cls.__name__}{separator}{resource_id}"

    @classmethod
    def get_cpu_hash_key(cls) -> str:
        """
        Get the hash key value for serialized dictionaries/hashes representations of objects.

        Returns
        -------
        str
            The hash key value for serialized dictionaries/hashes representations.
        """
        return "CPUs"

    @classmethod
    def get_resource_enum_value(cls, enum_type: Union[Type[ResourceAvailability], Type[ResourceState]],
                                text_val: str) -> Optional[Union[ResourceAvailability, ResourceState]]:
        """
        Get the enum value for the given enum class type, corresponding to the provided text string.

        Get the enum value for the given enum class type, corresponding to the provided text string, where a string
        corresponds to a value if it matches the value's ``name`` in a case-insensitive comparison, and with any
        trailing and leading whitespace trimmed.

        Only the enums used within the ::class:`Resource` class are supported.

        If there is no match within the domain of the provided enum type, the method will return ``None``.

        Parameters
        ----------
        enum_type : Union[Type[ResourceAvailability], Type[ResourceState]]
            The specific class of enum for which values should be checked and for which a value should be returned.

        text_val : str
            The string expected to be a case-insensitive representation of an enum value.

        Returns
        -------
        Optional[Union[ResourceAvailability, ResourceState]]
            The applicable corresponding enum value of the appropriate type, or ``None`` if there is no match.
        """
        if not isinstance(text_val, str):
            return None
        converted_text_value = text_val.strip().upper()
        for val in enum_type:
            if val.name.upper() == converted_text_value:
                return val
        return None


    def __eq__(self, other: object):
        if not isinstance(other, Resource):
            return super().__eq__(other)
        else:
            return self.resource_id == other.resource_id and self.hostname == other.hostname \
                   and self.availability == other.availability and self.state == other.state \
                   and self.cpu_count == other.cpu_count and self.memory == other.memory \
                   and self.total_cpus == other.total_cpus and self.total_memory == other.total_memory

    def allocate(self, cpu_count: int, memory: int) -> Tuple[int, int, bool]:
        """
        Request an allocation of sub-resources in the given amounts.

        The method will return a tuple with the allocated amount of CPUs and memory.  Note this can be less than what
        was requested, if the request amounts are not available, but sub-resources are still allocated (and otherwise
        made unavailable) in such cases.  Thus, it is the responsibility of the entity making the allocation request to
        release such resources in cases when receiving less than the requested allocation amounts results in the entity
        not needing the allocation.

        Parameters
        ----------
        cpu_count : int
            The number of CPUs requested.

        memory : int
            The amount of memory requested.

        Returns
        -------
        Tuple[int, int, bool]
            A tuple of the actual number of CPUs allocated, actual amount of memory allocated, and whether the request
            was fully (as opposed to only partially) allocated.
        """
        is_fully_allocated = True
        if self.cpu_count >= cpu_count:
            self.cpu_count = self.cpu_count - cpu_count
            allocated_cpus = cpu_count
        else:
            is_fully_allocated = False
            allocated_cpus = self.cpu_count
            self.cpu_count = 0
        if self.memory >= memory:
            self.memory = self.memory - memory
            allocated_mem = memory
        else:
            is_fully_allocated = False
            allocated_mem = self.memory
            self.memory = 0
        return allocated_cpus, allocated_mem, is_fully_allocated

    def set_availability(self, availability: Union[str, ResourceAvailability]):
        if isinstance(availability, ResourceAvailability):
            enum_val = availability
        else:
            enum_val = self.get_resource_enum_value(ResourceAvailability, availability)
        self.__dict__["availability"] = ResourceAvailability.UNKNOWN if enum_val is None else enum_val

    def is_allocatable(self) -> bool:
        """
        Get whether it is possible to allocate something from this resource.

        For this to be ``True``, ::attribute:`availability` must be ``ACTIVE`` of ::class:`ResourceAvailability,
        ::attribute:`state` must be ``READY`` of ::class:`ResourceState`, and both ::attribute:`cpu_count` and
        ::attribute:`memory` must be greater than ``0``.

        Returns
        -------
        bool
            Whether it is possible to allocate something from this resource.
        """
        return self.availability == ResourceAvailability.ACTIVE and self.state == ResourceState.READY \
            and self.cpu_count > 0 and self.memory > 0

    def release(self, cpu_count: int, memory: int):
        """
        Release previously allocated sub-resources in the given amounts.

        Parameters
        ----------
        cpu_count : int
            The number of CPUs released.

        memory : int
            The amount of memory released.
        """
        # TODO: do something to make sure we don't somehow get back more than we started with
        self.cpu_count = self.cpu_count + cpu_count
        self.memory = self.memory + memory

    @property
    def total_cpu_count(self) -> int:
        """
        The total number of CPUs known to be on this resource.
        Returns
        -------
        int
            The total number of CPUs known to be on this resource.
        """
        # NOTE: total cpus will be set or derived from `cpu_count`
        return self.total_cpus # type: ignore


    @property
    def resource_id(self) -> str:
        return self.pool_id

    def set_state(self, state: Union[str, ResourceState]):
        if isinstance(state, ResourceState):
            enum_val = state
        else:
            enum_val = self.get_resource_enum_value(ResourceState, state)
        self.__dict__["state"] = ResourceState.UNKNOWN if enum_val is None else enum_val

    @property
    def unique_id(self) -> str:
        return self.generate_unique_id(resource_id=self.resource_id, separator=self.unique_id_separator)

    def _setter_methods(self) -> Dict[str, Callable]:
        """Mapping of attribute name to setter method. This supports backwards functional compatibility."""
        # TODO: remove once migration to setters by down stream users is complete
        return {
            "state": self.set_state,
            "availability": self.set_availability,
            }

    def __setattr__(self, name: str, value: Any):
        """
        Use property setter method when available.

        Note, all setter methods should modify their associated property using the instance `__dict__`.
        This ensures that calls to, for example, `set_id` don't raise a warning, while `o.id = "new
        id"` do.

        Example:
            ```
            class SomeJob(Job):
                id: str

                def set_id(self, value: str):
                    self.__dict__["id"] = value
            ```
        """
        if name not in self._setter_methods():
            return super().__setattr__(name, value)

        setter_fn = self._setter_methods()[name]

        message = f"Setting by attribute is deprecated. Use `{self.__class__.__name__}.{setter_fn.__name__}` method instead."
        warn(message, DeprecationWarning)

        setter_fn(value)
