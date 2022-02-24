from enum import Enum
from datetime import datetime

from dmod.communication.serializeable import Serializable
from numbers import Number
from typing import Any, Dict, List, Optional, Set, Type, Union


class DataFormat(Enum):
    AORC_CSV = (0,
                ["catchment-id", ""],
                {"": datetime, "APCP_surface": float, "DLWRF_surface": float, "DSWRF_surface": float,
                 "PRES_surface": float, "SPFH_2maboveground": float, "TMP_2maboveground": float,
                 "UGRD_10maboveground": float, "VGRD_10maboveground": float, "precip_rate": float},
                {"catchment-id": str}
                )
    """ The CSV data format the Nextgen framework originally used during its early development. """
    NETCDF_FORCING_CANONICAL = (1,
                                ["ids", "Time"],
                                {"Time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float,
                                 "U2D": float, "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float,
                                 "offset": int},
                                {"ids": str}
                                )
    """ The Nextgen framework "canonical" NetCDF forcing data format. """
    NETCDF_AORC_DEFAULT = (2,
                           ["ids", "Time"],
                           {"ids": str, "Time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float, "U2D": float,
                            "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float, "offset": int}
                           )
    """ The default format for "raw" AORC forcing data. """
    # TODO: consider whether a datetime format string is necessary for each type value
    # TODO: consider whether something to indicate the time step size is necessary
    # TODO: need format specifically for Nextgen model output (i.e., for evaluations)

    @classmethod
    def get_for_name(cls, name_str: str) -> Optional['DataFormat']:
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return None

    def __init__(self, uid: int, indices: List[str], data_fields: Optional[Union[Dict[str, Type], Set[str]]] = None,
                 implicit_indices_types: Optional[Dict[str, Type]] = None):
        self._uid = uid
        self._indices = indices
        # If only the field names were provided, infer a type value of 'Any'
        if isinstance(data_fields, set):
            self._data_fields = dict()
            for f in data_fields:
                self._data_fields[f] = Any
        # Create an empty dictionary if None was passed
        elif data_fields is None:
            self._data_fields = dict()
        # And otherwise, use what was provided
        else:
            self._data_fields = data_fields
        self._implicit_indices_types = implicit_indices_types

    # TODO: consider later also adding the ability for some fields to be treated as optional
    @property
    def data_fields(self) -> Dict[str, Type]:
        """
        The name and type of data fields specified for this format

        This property will be an empty dictionary if no field specification is available.

        A type value of ::class:`Any` indicates that no specification for the field's type is known.

        Returns
        -------
        Optional[Dict[str, Type]]
            The data fields for this format, if the format value specifies its fields, or ``None``.
        """
        return self._data_fields

    @property
    def indices(self) -> List[str]:
        """
        List of the indices properties for this format.

        Returns
        -------
        List[str]
            List of the indices properties for this format.
        """
        return self._indices

    @property
    def is_time_series(self) -> bool:
        """
        Whether this type is a format of time series data.

        This is determined by whether any index from ::attribute:`indices` is of type ::class:`datetime`.

        Returns
        -------
        bool
            Whether this type is a format of time series data.
        """
        for i in self.indices:
            if i in self.data_fields:
                if self.data_fields[i] == datetime:
                    return True
            elif self._implicit_indices_types[i] == datetime:
                return True
        return False


class ContinuousRestriction(Serializable):
    """
    A filtering component, typical applied as a restriction on a domain, by a continuous range of values of a variable.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        datetime_ptr = json_obj["datetime_pattern"] if "datetime_pattern" in json_obj else None
        try:
            # Handle simple case, which currently means non-datetime item (i.e., no pattern included)
            if datetime_ptr is None:
                return cls(variable=json_obj["variable"], begin=json_obj["begin"], end=json_obj["end"])

            # If there is a datetime pattern, then expect begin and end to parse properly to datetime objects
            begin = datetime.strptime(json_obj["begin"], datetime_ptr)
            end = datetime.strptime(json_obj["end"], datetime_ptr)

            # Try to initialize the right subclass type, or fall back if appropriate to the base type
            # TODO: consider adding something for recursive search for subclass, not just immediate children types
            # Use nested try, because we want to fall back to cls type if no subclass attempt or subclass attempt fails
            try:
                for subclass in cls.__subclasses__():
                    if subclass.__name__ == json_obj["subclass"]:
                        return subclass(variable=json_obj["variable"], begin=begin, end=end, datetime_pattern=datetime_ptr)
            except:
                pass

            # Fall back if needed
            return cls(variable=json_obj["variable"], begin=begin, end=end, datetime_pattern=datetime_ptr)
        except:
            return None

    def __init__(self, variable: str, begin, end, datetime_pattern: Optional[str] = None):
        self.variable: str = variable
        if begin > end:
            raise RuntimeError("Cannot have {} with begin value larger than end.".format(self.__class__.__name__))
        self.begin = begin
        self.end = end
        self._datetime_pattern = datetime_pattern

    def contains(self, other: 'ContinuousRestriction') -> bool:
        """
        Whether this object contains all the values of the given object and the two are of the same index.

        For this type, equal begin or end values are considered contained.

        Parameters
        ----------
        other : ContinuousRestriction

        Returns
        -------
        bool
            Whether this object contains all the values of the given object and the two are of the same index.
        """
        if not isinstance(other, ContinuousRestriction):
            return False
        elif self.variable != other.variable:
            return False
        else:
           return self.begin <= other.begin and self.end >= other.end

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = dict()
        serial["variable"] = self.variable
        serial["subclass"] = self.__class__.__name__
        if self._datetime_pattern is not None:
            serial["datetime_pattern"] = self._datetime_pattern
            serial["begin"] = self.begin.strftime(self._datetime_pattern)
            serial["end"] = self.end.strftime(self._datetime_pattern)
        else:
            serial["begin"] = self.begin
            serial["end"] = self.end
        return serial


class DiscreteRestriction(Serializable):
    """
    A filtering component, typical applied as a restriction on a domain, by a discrete set of values of a variable.
    """
    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return cls(variable=json_obj["variable"], values=json_obj["values"])
        except:
            return None

    def __init__(self, variable: str, values: Union[List[str], List[Number]]):
        self.variable: str = variable
        self.values: Union[List[str], List[Number]] = values

    def contains(self, other: 'DiscreteRestriction') -> bool:
        """
        Whether this object contains all the values of the given object and the two are of the same index.

        Parameters
        ----------
        other : DiscreteRestriction

        Returns
        -------
        bool
            Whether this object contains all the values of the given object and the two are of the same index.
        """
        if not isinstance(other, DiscreteRestriction):
            return False
        elif self.variable != other.variable:
            return False
        else:
            value_set = set(self.values)
            for v in other.values:
                if v not in value_set:
                    return False
        return True

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        return {"variable": self.variable, "values": self.values}


class DataDomain(Serializable):
    """
    A domain for a dataset, with domain-defining values contained by one or more discrete and/or continuous components.
    """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            data_format = DataFormat.get_for_name(json_obj["data_format"])
            continuous = [ContinuousRestriction.factory_init_from_deserialized_json(c) for c in json_obj["continuous"]]
            discrete = [DiscreteRestriction.factory_init_from_deserialized_json(d) for d in json_obj["discrete"]]
            return cls(data_format=data_format, continuous_restrictions=continuous, discrete_restrictions=discrete)
        except:
            return None

    def __init__(self, data_format: DataFormat, continuous_restrictions: Optional[List[ContinuousRestriction]] = None,
                 discrete_restrictions: Optional[List[DiscreteRestriction]] = None):
        self._data_format = data_format
        self._continuous_restrictions = dict()
        self._discrete_restrictions = dict()

        if continuous_restrictions is not None:
            for c in continuous_restrictions:
                self._continuous_restrictions[c.variable] = c

        if discrete_restrictions is not None:
            for d in discrete_restrictions:
                self._discrete_restrictions[d.variable] = d

        if len(self._continuous_restrictions) + len(self._discrete_restrictions) == 0:
            msg = "Cannot create {} without at least one finite continuous or discrete restriction"
            raise RuntimeError(msg.format(self.__class__.__name__))

    def _extends_continuous_restriction(self, continuous_restriction: ContinuousRestriction) -> bool:
        idx = continuous_restriction.variable
        return idx in self.continuous_restrictions and self.continuous_restrictions[idx].contains(continuous_restriction)

    def _extends_discrete_restriction(self, discrete_restriction: DiscreteRestriction) -> bool:
        idx = discrete_restriction.variable
        return idx in self.discrete_restrictions and self.discrete_restrictions[idx].contains(discrete_restriction)

    def contains(self, other: Union[ContinuousRestriction, DiscreteRestriction, 'DataDomain']) -> bool:
        """
        Whether this domain contains the given domain or collection of domain index values.

        Parameters
        ----------
        other : Union[ContinuousRestriction, DiscreteRestriction, 'DataDomain']
            Another domain, or a group of continuous or discrete values for particular domain index.

        Returns
        -------
        bool
            Whether this domain contains the given domain or collection of domain index values.
        """
        if isinstance(other, ContinuousRestriction):
            return self._extends_continuous_restriction(other)
        elif isinstance(other, DiscreteRestriction):
            return self._extends_discrete_restriction(other)
        else:
            for index in other.continuous_restrictions:
                if not self._extends_continuous_restriction(other.continuous_restrictions[index]):
                    return False
            for index in other.discrete_restrictions:
                if not self._extends_discrete_restriction(other.discrete_restrictions[index]):
                    return False
            return True

    @property
    def continuous_restrictions(self) -> Dict[str, ContinuousRestriction]:
        """
        Map of the continuous restrictions defining this domain, keyed by variable name.

        Returns
        -------
        Dict[str, ContinuousRestriction]
            Map of the continuous restrictions defining this domain, keyed by variable name.
        """
        return self._continuous_restrictions

    @property
    def discrete_restrictions(self) -> Dict[str, DiscreteRestriction]:
        """
        Map of the discrete restrictions defining this domain, keyed by variable name.

        Returns
        -------
        Dict[str, DiscreteRestriction]
            Map of the discrete restrictions defining this domain, keyed by variable name.
        """
        return self._discrete_restrictions

    @property
    def data_format(self) -> DataFormat:
        """
        The format for data in this domain.

        The format for the data in this domain, which contains details like the indices and other data fields.

        Returns
        -------
        DataFormat
            The format for data in this domain.
        """
        return self._data_format

    @property
    def indices(self) -> List[str]:
        """
        List of the names of indices that define the data domain.

        This list contains the names of indices (i.e., in the context of some ::class:`DataFormat`) that are used to
        define this data domain.

        Returns
        -------
        List[str]
            List of the names of indices that define the data domain.
        """
        return self._data_format.indices

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        """
        Serialize to a dictionary.

        Serialize this instance to a dictionary, with there being two top-level list items.  These are made from the
        the contained ::class:`ContinuousRestriction` and ::class:`DiscreteRestriction` objects

        Returns
        -------

        """
        return {"data_format": self._data_format.name,
                "continuous": [component.to_dict() for idx, component in self.continuous_restrictions.items()],
                "discrete": [component.to_dict() for idx, component in self.discrete_restrictions.items()]}


class DataCategory(Enum):
    """
    The general category values for different data.
    """
    FORCING = 0
    HYDROFABRIC = 1
    OUTPUT = 2
    OBSERVATION = 3

    @classmethod
    def get_for_name(cls, name_str: str) -> Optional['DataCategory']:
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return None


class TimeRange(ContinuousRestriction):
    """
    Encapsulated representation of a time range.
    """

    def __init__(self, begin: datetime, end: datetime, variable: Optional[str] = None):
        super(TimeRange, self).__init__(variable="Time" if variable is None else variable, begin=begin, end=end,
                                        datetime_pattern=self.get_datetime_str_format())


# TODO: ***** fix DataDomain to include a data format value, then refactor this type to just use that as the domain
class DataRequirement(Serializable):
    """
    A definition of a particular data requirement needed for an execution task.
    """

    _KEY_CATEGORY = 'category'
    """ Serialization dictionary JSON key for ::attribute:`category` property value. """
    _KEY_DOMAIN = 'domain'
    """ Serialization dictionary JSON key for ::attribute:`domain_params` property value. """
    _KEY_FULFILLED_BY = 'fulfilled_by'
    """ Serialization dictionary JSON key for ::attribute:`fulfilled_by` property value. """
    _KEY_IS_INPUT = 'is_input'
    """ Serialization dictionary JSON key for ::attribute:`is_input` property value. """
    _KEY_SIZE = 'size'
    """ Serialization dictionary JSON key for ::attribute:`size` property value. """

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['DataRequirement']:
        """
        Deserialize the given JSON to a ::class:`DataRequirement` instance, or return ``None`` if it is not valid.

        Parameters
        ----------
        json_obj : dict
            The JSON to be deserialized.

        Returns
        -------
        Optional[DataRequirement]
            A deserialized ::class:`DataRequirement` instance, or return ``None`` if the JSON is not valid.
        """
        try:
            category = DataCategory.get_for_name(json_obj[cls._KEY_CATEGORY])
            is_input = json_obj[cls._KEY_IS_INPUT]
            fulfilled_by = json_obj[cls._KEY_FULFILLED_BY] if cls._KEY_FULFILLED_BY in json_obj else None
            size = json_obj[cls._KEY_SIZE] if cls._KEY_SIZE in json_obj else None
            domain = DataDomain.factory_init_from_deserialized_json(json_obj[cls._KEY_DOMAIN])
            return cls(domain=domain, is_input=is_input, category=category, size=size, fulfilled_by=fulfilled_by)
        except:
            return None

    def __init__(self, domain: DataDomain, is_input: bool, category: DataCategory, size: Optional[int] = None,
                 fulfilled_by: Optional[str] = None):
        self._domain = domain
        self._is_input = is_input
        self._category = category
        self._size = size
        self._fulfilled_by = fulfilled_by

    @property
    def category(self) -> DataCategory:
        """
        The ::class:`DataCategory` of data required.

        Returns
        -------
        DataCategory
            The category of data required.
        """
        return self._category

    @property
    def domain(self) -> DataDomain:
        """
        The (restricted) domain of the data that is required.

        Returns
        -------
        DataDomain
            The (restricted) domain of the data that is required.
        """
        return self._domain

    @property
    def fulfilled_by(self) -> Optional[str]:
        """
        The name of the dataset that will fulfill this, if it is known.

        Returns
        -------
        Optional[str]
            The name of the dataset that will fulfill this, if it is known; ``None`` otherwise.
        """
        return self._fulfilled_by

    @fulfilled_by.setter
    def fulfilled_by(self, name: str):
        self._fulfilled_by = name

    @property
    def is_input(self) -> bool:
        """
        Whether this represents required input data, as opposed to a requirement for storing output data.

        Returns
        -------
        bool
            Whether this represents required input data.
        """
        return self._is_input

    @property
    def size(self) -> Optional[int]:
        """
        The size of the required data, if it is known.

        This is particularly important (though still not strictly required) for an output data requirement; i.e., a
        requirement to store output data somewhere.

        Returns
        -------
        Optional[int]
            he size of the required data, if it is known, or ``None`` otherwise.
        """
        return self._size

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = {self._KEY_DOMAIN: self.domain.to_dict(), self._KEY_IS_INPUT: self.is_input,
                  self._KEY_CATEGORY: self.category.name}
        if self.size is not None:
            serial[self._KEY_SIZE] = self.size
        if self.fulfilled_by is not None:
            serial[self._KEY_FULFILLED_BY] = self.fulfilled_by
        return serial
