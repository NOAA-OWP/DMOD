from enum import Enum
from datetime import datetime

from .serializable import Serializable
from numbers import Number
from typing import Any, Dict, List, Optional, Set, Type, Union


class DataFormat(Enum):
    """
    Supported data format types for data needed or produced by workflow execution tasks.

    Enum member values are a tuple corresponding to the params in the ``__init__`` function, which in turn correspond to
    the document properties.  Assignment is based on ordering within the tuple.

    The ::attribute:`indices` property contains the indices of the data, from which it is possible to uniquely identify
    data records/object.  The ::attribute:`data_fields` property, when not ``None`` provides the data fields contained
    within the data (some of which may be indices) and, when possible, the data type.  When this property is ``None``,
    this means that data fields are not known, as opposed to there being no data fields.

    Some indices will be data fields, while others will not (e.g., for ``AORC_CSV``, data in a given file corresponds to
    a particular catchment, so the catchment itself is inferred based on the file, instead of explicitly appearing
    within the data).  While not accessible via public property, an additional (but optional) tuple element after the
    data fields is set when appropriate to provide such implicit indices and their types.

    A particularly important, common implied index is that of ``data_id``.  Collections of data of several formats may
    be observably indistinguishable (i.e., according to index values) from certain other collections of the same
    format, while being significantly functionally different.  When this is possible and it is likely to need two such
    similar collections of data to be available at the same time, the ``data_id`` implied indices is added to give users
    of the format an additional "standard" index that can provide some distinction.

    An example of the need for ``data_id`` would be a Nextgen framework realization configuration.  Two separate
    "pieces" (i.e., config files) of data may cover the exact same catchments and time period.  There must be a separate
    index that can be used to distinguish the collections, so that the right data can be identified.
    """
    AORC_CSV = (0,
                ["catchment-id", ""],
                {"": datetime, "APCP_surface": float, "DLWRF_surface": float, "DSWRF_surface": float,
                 "PRES_surface": float, "SPFH_2maboveground": float, "TMP_2maboveground": float,
                 "UGRD_10maboveground": float, "VGRD_10maboveground": float, "precip_rate": float},
                {"catchment-id": str}
                )
    """ The CSV data format the Nextgen framework originally used during its early development. """
    NETCDF_FORCING_CANONICAL = (1,
                                ["catchment-id", "time"],
                                {"time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float,
                                 "U2D": float, "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float,
                                 "offset": int},
                                {"catchment-id": str}
                                )
    """ The Nextgen framework "canonical" NetCDF forcing data format. """
    # TODO: need to look at actual format and fix this
    NETCDF_AORC_DEFAULT = (2,
                           ["ids", "Time"],
                           {"ids": str, "Time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float, "U2D": float,
                            "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float, "offset": int}
                           )
    """ The default format for "raw" AORC forcing data. """
    NGEN_OUTPUT = (3, ["id", "Time", "data_id"], None, {"id": str, "Time": datetime, "data_id": str})
    """ Representation of the format for Nextgen output, with unknown/unspecified configuration of output fields. """
    NGEN_REALIZATION_CONFIG = (4, ["id", "time", "data_id"],
                               None,
                               {"id": str, "time": datetime, "data_id": str}
                               )
    """ Representation of the format of realization configs, which covers catchments (id) has a time period (time). """
    NGEN_GEOJSON_HYDROFABRIC = (5,
                                ["id", "hydrofabric_uid", "data_id"],
                                {"id": str, "properties": Any, "geometry": Any},
                                {"hydrofabric_uid": str, "data_id": str}
                                )
    """ GeoJSON hydrofabric format used by Nextgen (id is catchment id). """
    NGEN_PARTITION_CONFIG = (6,
                             ["all_cat_ids", "data_id", "count"],
                             {"id": int, "cat-ids": List[str], "nex-id": List[str],
                              "remote-connections": List[Dict[str, int]]},
                             {"data_id": str, "all_cat_ids": List[str], "count": int}
                             )
    """ GeoJSON hydrofabric format used by Nextgen. """
    BMI_CONFIG = (7, ["file", "data_id"], None, {"file": str, "data_id": str})
    """ Format for BMI initialization config files, of which (in general) there is only implied index of file name. """
    NWM_OUTPUT = (8, ["id", "Time", "data_id"], {"Time": datetime, "streamflow": float}, {"id": str, "data_id": str})
    """ Format for NWM 2.0/2.1/2.2 output. """
    NWM_CONFIG = (9, ["id", "time", "data_id"], None, {"id": str, "time": datetime, "data_id": str})
    """ Format for initial config for NWM 2.0/2.1/2.2. """
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
        self._time_series_index = None
        self._is_time_series_index = None

    # TODO: consider later also adding the ability for some fields to be treated as optional
    @property
    def data_fields(self) -> Dict[str, Type]:
        """
        The name and type of data fields specified for this format.

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

        This is determined by whether there is a time series index according to ::method:`time_series_index`.

        This property is backed by a private attribute, but is lazily initialized via a nested get of the
        ::attribute:`time_series_index` property.

        Returns
        -------
        bool
            Whether this type is a format of time series data.

        See Also
        -------
        ::attribute:`time_series_index`
        """
        if self._is_time_series_index is None:
            # A call to this property will set self._is_time_series_index
            self.time_series_index
        return self._is_time_series_index

    @property
    def time_series_index(self) -> Optional[str]:
        """
        The index for the time component of this format, if it is for time series data.

        This is the index (implied or a data field) with type ::class:`datetime`.

        Property lazily initializes when appropriate, determining this by examining the "private" attribute
        ::attribute:`_is_time_series_index` and testing whether it is not set (i.e., it is ``None``).  The property
        using this private attribute - ::attribute:`is_time_series_index` - is lazily initialized also, and by **this**
        property getter method, hence use of the "private" attribute for the lazy initialization check.

        When lazy initialization is performed, the last step will be to set ::attribute:`is_time_series_index` to either
        ``True`` or ``False``, depending on whether this property was initialized to something other than ``None`` or
        not.

        Returns
        -------
        Optional[str]
            The index for the time component of this format, if it is for time series data; otherwise ``None``.

        See Also
        -------
        ::attribute:`is_time_series_index`
        """
        # Because this property can end up actually being None, can't use it to know if lazy init is necessary
        # Instead, check _is_time_series_index to see if lazy init still needed, and if so, lazy init both
        if self._is_time_series_index is None:
            for idx in self.indices:
                if idx in self.data_fields:
                    if self.data_fields[idx] == datetime:
                        self._time_series_index = idx
                        break
                elif self._implicit_indices_types[idx] == datetime:
                    self._time_series_index = idx
                    break
            self._is_time_series_index = self._time_series_index is not None
        return self._time_series_index


class ContinuousRestriction(Serializable):
    """
    A filtering component, typically applied as a restriction on a domain, by a continuous range of values of a variable.
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

            # Use this type if that's what the JSON specifies is the Serializable subtype
            if cls.__name__ == json_obj["subclass"]:
                return cls(variable=json_obj["variable"], begin=begin, end=end, datetime_pattern=datetime_ptr)

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

    def __eq__(self, other):
        if self.__class__ == other.__class__ or isinstance(other, self.__class__):
            return self.variable == other.variable and self.begin == other.begin and self.end == other.end \
                   and self._datetime_pattern == other._datetime_pattern
        elif isinstance(self, other.__class__):
            return other.__eq__(self)
        else:
            return False

    def __hash__(self):
        str_func = lambda x: str(x) if self._datetime_pattern is None else datetime.strptime(x, self._datetime_pattern)
        hash('{}-{}-{}'.format(self.variable, str_func(self.begin), str_func(self.end)))

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
    A filtering component, typically applied as a restriction on a domain, by a discrete set of values of a variable.

    Note that an empty list for the ::attribute:`values` property implies a restriction of all possible values being
    required.  This is reflected by the :method:`is_all_possible_values` property.
    """
    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        try:
            return cls(variable=json_obj["variable"], values=json_obj["values"])
        except:
            return None

    def __init__(self, variable: str, values: Union[List[str], List[Number]], allow_reorder: bool = True,
                 remove_duplicates: bool = True):
        self.variable: str = variable
        self.values: Union[List[str], List[Number]] = list(set(values)) if remove_duplicates else values
        if allow_reorder:
            self.values.sort()

    def __eq__(self, other):
        if self.__class__ == other.__class__ or isinstance(other, self.__class__):
            return self.variable == other.variable and self.values == other.values
        elif isinstance(self, other.__class__):
            return other.__eq__(self)
        else:
            return False

    def __hash__(self):
        hash('{}-{}'.format(self.variable, ','.join([str(v) for v in self.values])))

    def contains(self, other: 'DiscreteRestriction') -> bool:
        """
        Whether this object contains all the values of the given object and the two are of the same index.

        Note that if the ::attribute:`is_all_possible_values` property is ``True``, then the specific values in the
        ``other`` restriction are ignored, and this returns ``True`` as long as the variable values align.

        Parameters
        ----------
        other : DiscreteRestriction

        Returns
        -------
        bool
            Whether this object contains all the values of the given object and the two are of the same index.

        See Also
        -------
        ::attribute:`is_all_possible_values`
        """
        if not isinstance(other, DiscreteRestriction):
            return False
        elif self.variable != other.variable:
            return False
        elif self.is_all_possible_values:
            return True
        else:
            value_set = set(self.values)
            for v in other.values:
                if v not in value_set:
                    return False
        return True

    @property
    def is_all_possible_values(self) -> bool:
        """
        Whether this object's restriction is effectively "all possible values" of some larger context.

        This property is ``True`` IFF ::attribute:`values` is an empty list.

        Note that the value of this property has implications on the behavior of ::method:`contains`.

        Returns
        -------
        bool
            Whether this object's restriction is effectively "all possible values" of some larger context.

        See Also
        -------
        ::method:`contains`
        """
        return self.values is not None and len(self.values) == 0

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
            if 'data_fields' in json_obj:
                data_fields = dict()
                for key in json_obj['data_fields']:
                    val = json_obj['data_fields'][key]
                    if val == 'str':
                        data_fields[key] = str
                    elif val == 'int':
                        data_fields[key] = int
                    elif val == 'float':
                        data_fields[key] = float
                    else:
                        data_fields[key] = Any
            else:
                data_fields = None

            return cls(data_format=data_format, continuous_restrictions=continuous, discrete_restrictions=discrete,
                       custom_data_fields=data_fields)
        except:
            return None

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.data_format == other.data_format \
               and self.continuous_restrictions == other.continuous_restrictions \
               and self.discrete_restrictions == other.discrete_restrictions \
               and self._custom_data_fields == other._custom_data_fields

    def __hash__(self):
        if self._custom_data_fields is None:
            cu = ''
        else:
            cu = ','.join(['{}:{}'.format(f, self._custom_data_fields[f]) for f in sorted(self._custom_data_fields)])
        return hash('{}-{}-{}-{}'.format(
            self.data_format,
            ','.join([str(hash(self.continuous_restrictions[k])) for k in sorted(self.continuous_restrictions)]),
            ','.join([str(hash(self.discrete_restrictions[k])) for k in sorted(self.discrete_restrictions)]),
            cu))

    def __init__(self, data_format: DataFormat, continuous_restrictions: Optional[List[ContinuousRestriction]] = None,
                 discrete_restrictions: Optional[List[DiscreteRestriction]] = None,
                 custom_data_fields: Optional[Dict[str, Type]] = None):
        self._data_format = data_format
        self._continuous_restrictions = dict()
        self._discrete_restrictions = dict()
        self._custom_data_fields = custom_data_fields
        """ Extra attribute for custom data fields when format does not specify all data fields (ignore when format does specify). """

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
    def data_fields(self) -> Dict[str, Type]:
        """
        Get the data fields map of this domain instance.

        This will either be directly from the format, if its format specifies any fields, or from a custom fields
        attribute that may be set during initialization (but is ignored when the format specifies fields).

        Returns
        -------

        """
        if self.data_format.data_fields is None:
            return self._custom_data_fields
        else:
            return self._data_format.data_fields

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
        serial = {"data_format": self._data_format.name,
                  "continuous": [component.to_dict() for idx, component in self.continuous_restrictions.items()],
                  "discrete": [component.to_dict() for idx, component in self.discrete_restrictions.items()]}
        if self.data_format.data_fields is None:
            serial['data_fields'] = dict()
            for key in self._custom_data_fields:
                if self._custom_data_fields[key] == str:
                    serial['data_fields'][key] = 'str'
                elif self._custom_data_fields[key] == int:
                    serial['data_fields'][key] = 'int'
                elif self._custom_data_fields[key] == float:
                    serial['data_fields'][key] = 'float'
                else:
                    serial['data_fields'][key] = 'Any'
        return serial


class DataCategory(Enum):
    """
    The general category values for different data.
    """
    CONFIG = 0
    FORCING = 1
    HYDROFABRIC = 2
    OBSERVATION = 3
    OUTPUT = 4

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

    def __init__(self, begin: datetime, end: datetime, variable: Optional[str] = None,
                 datetime_pattern: Optional[str] = None):
        super(TimeRange, self).__init__(variable="Time" if variable is None else variable, begin=begin, end=end,
                                        datetime_pattern=self.get_datetime_str_format() if datetime_pattern is None else datetime_pattern)


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

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.domain == other.domain and self.is_input == other.is_input \
               and self.category == other.category

    def __hash__(self):
        return hash('{}-{}-{}'.format(hash(self.domain), self.is_input, self.category))

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
