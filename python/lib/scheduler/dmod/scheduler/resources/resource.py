from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union
from pydantic import Field, Extra, validator


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
                               ignore_extra_keys: bool = False) -> 'AbstractProcessingAssetPool':
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

    def __init__(self, pool_id: str, hostname: str, cpu_count: int, memory: int):
        super().__init__(pool_id=pool_id, cpu_count=cpu_count, memory=memory)
        self._hostname = hostname

    @property
    def hostname(self) -> str:
        return self._hostname


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

    @classmethod
    def factory_init_from_dict(cls, init_dict: dict, ignore_extra_keys: bool = False) -> 'Resource':
        """
        Initialize a new object from the given dictionary, raising a ::class:`ValueError` if there are missing expected
        keys or there are extra keys when the method is not set to ignore them.

        Note that this method will allow ::class:`ResourceAvailability` and ::class:`ResourceState` values for the
        init values of ``availability`` and ``state`` respectively, in addition to strings.  It will also convert
        numeric types from string values appropriately.

        Also, unlike other implementations, ``total cpus`` and ``total memory`` are expected keys, but they are not
        required.  If they are not present, the defaults (the respective available values) are used by the initializer.

        parent:
        """
        node_id = None
        hostname = None
        avail = None
        state = None
        cpus = None
        total_cpus = None
        memory = None
        total_memory = None

        for param_key in init_dict:
            # We don't care about non-string keys directly, but they are implicitly extra ...
            if not isinstance(param_key, str):
                if not ignore_extra_keys:
                    raise ValueError("Unexpected non-string resource init key")
                else:
                    continue
            lower_case_key = param_key.lower()
            if lower_case_key == 'node_id' and node_id is None:
                node_id = init_dict[param_key]
            elif lower_case_key == 'hostname' and hostname is None:
                hostname = init_dict[param_key]
            elif lower_case_key == 'availability' and avail is None:
                avail = init_dict[param_key]
            elif lower_case_key == 'state' and state is None:
                state = init_dict[param_key]
            elif lower_case_key == 'cpus' and cpus is None:
                cpus = int(init_dict[param_key])
            elif lower_case_key == 'memorybytes' and memory is None:
                memory = int(init_dict[param_key])
            elif lower_case_key == 'total cpus' and total_cpus is None:
                total_cpus = int(init_dict[param_key])
            elif lower_case_key == 'total memory' and total_memory is None:
                total_memory = int(init_dict[param_key])
            elif not ignore_extra_keys:
                raise ValueError("Unexpected resource init key (or case-insensitive duplicate) {}".format(param_key))

        # Make sure we have everything required set
        if node_id is None or hostname is None or cpus is None or memory is None or avail is None or state is None:
            raise ValueError("Insufficient valid values keyed within resource init dictionary")

        return cls(resource_id=node_id, hostname=hostname, availability=avail, state=state, cpu_count=cpus,
                   memory=memory, total_cpu_count=total_cpus, total_memory=total_memory)

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
        return cls.__name__ + separator + resource_id

    @classmethod
    def get_cpu_hash_key(cls) -> str:
        """
        Get the hash key value for serialized dictionaries/hashes representations of objects.

        Returns
        -------
        str
            The hash key value for serialized dictionaries/hashes representations.
        """
        return 'CPUs'

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

    def __eq__(self, other):
        if not isinstance(other, Resource):
            return super().__eq__(other)
        else:
            return self.resource_id == other.resource_id and self.hostname == other.hostname \
                   and self.availability == other.availability and self.state == other.state \
                   and self.cpu_count == other.cpu_count and self.memory == other.memory \
                   and self.total_cpu_count == other.total_cpu_count and self.total_memory == other.total_memory

    def __init__(self, resource_id: str, hostname: str, availability: Union[str, ResourceAvailability],
                 state: Union[str, ResourceState], cpu_count: int, memory: int, total_cpu_count: Optional[int],
                 total_memory: Optional[int]):
        super().__init__(pool_id=resource_id, hostname=hostname, cpu_count=cpu_count, memory=memory)

        self._availability = None
        self.availability = availability

        self._state = state
        self.state = state

        self._total_cpu_count = cpu_count if total_cpu_count is None else total_cpu_count
        self._total_memory = memory if total_memory is None else total_memory

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

    @property
    def availability(self) -> ResourceAvailability:
        """
        The availability of the resource.

        Note that the property setter accepts both string and ::class:`ResourceAvailability` values.  For a string, the
        argument is converted to a ::class:`ResourceAvailability` value using ::method:`get_resource_enum_value`.

        However, if the conversion of a string with ::method:`get_resource_enum_value` returns ``None``, the setter
        sets ::attribute:`availability` to the ``UNKNOWN`` enum value, rather than ``None``.  This is more applicable
        and allows the getter to always return an actual ::class:`ResourceAvailability` instance.

        Returns
        -------
        ResourceAvailability
            The availability of the resource.
        """
        return self._availability

    @availability.setter
    def availability(self, availability: Union[str, ResourceAvailability]):
        if isinstance(availability, ResourceAvailability):
            enum_val = availability
        else:
            enum_val = self.get_resource_enum_value(ResourceAvailability, availability)
        self._availability = ResourceAvailability.UNKNOWN if enum_val is None else enum_val

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
    def resource_id(self) -> str:
        return self.pool_id

    @property
    def state(self) -> ResourceState:
        """
        The readiness state of the resource.

        Note that the property setter accepts both string and ::class:`ResourceState` values.  For a string, the
        argument is converted to a ::class:`ResourceState` value using ::method:`get_resource_enum_value`.

        However, if the conversion of a string with ::method:`get_resource_enum_value` returns ``None``, the setter sets
        ::attribute:`state` to the ``UNKNOWN`` enum value, rather than ``None``.  This is more applicable and allows the
        getter to always return an actual ::class:`ResourceState` instance.

        Returns
        -------
        ResourceState
            The readiness state of the resource.
        """
        return self._state

    @state.setter
    def state(self, state: Union[str, ResourceState]):
        if isinstance(state, ResourceState):
            enum_val = state
        else:
            enum_val = self.get_resource_enum_value(ResourceState, state)
        self._state = ResourceState.UNKNOWN if enum_val is None else enum_val

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """
        Convert the object to a serialized dictionary.

        Key names are as shown in the example below.  Enum values are represented as the lower-case version of the name
        for the given value.  Values shown for CPU and Memory are the max values.

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

        Returns
        -------
        Dict[str, Union[str, int]]
            The object as a serialized dictionary.
        """
        return {'node_id': self.resource_id, 'Hostname': self.hostname, 'Availability': self.availability.name.lower(),
                'State': self.state.name.lower(), self.get_cpu_hash_key(): self.cpu_count, 'MemoryBytes': self.memory,
                'Total CPUs': self.total_cpu_count, 'Total Memory': self.total_memory}

    @property
    def total_cpu_count(self) -> int:
        """
        The total number of CPUs known to be on this resource.

        Returns
        -------
        int
            The total number of CPUs known to be on this resource.
        """
        return self._total_cpu_count

    @property
    def total_memory(self) -> int:
        """
        The total amount of memory known to be on this resource.

        Returns
        -------
        int
            The total amount of memory known to be on this resource.
        """
        return self._total_memory

    @property
    def unique_id(self) -> str:
        return self.generate_unique_id(resource_id=self.resource_id, separator=self.unique_id_separator)
