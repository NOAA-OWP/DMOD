from datetime import datetime

from .enum import PydanticEnum
from .serializable import Serializable
from .common.helper_functions import get_subclasses
from numbers import Number
from typing import Any, Dict, List, Literal, Optional, Set, Type, Union
from collections.abc import Iterable
from collections import OrderedDict
from pydantic import root_validator, validator, PyObject, Field, StrictStr, StrictFloat, StrictInt


class StandardDatasetIndex(str, PydanticEnum):

    #         (index value, expected type, name)
    UNKNOWN = (-1, Any, "UNKNOWN")
    TIME = (0, datetime, "TIME")
    CATCHMENT_ID = (1, str, "CATCHMENT_ID")
    """ A specialized index for catchment id, since that will be so commonly needed. """
    DATA_ID = (2, str, "DATA_ID")
    """ An index for the data_id of the dataset itself. """
    HYDROFABRIC_ID = (3, str, "HYDROFABRIC_ID")
    """ A specialized index for the unique id of a hydrofabric itself. """
    LENGTH = (4, int, "LENGTH")
    """ Index to represent the number of records within a dataset (important in particular for partition configs). """
    GLOBAL_CHECKSUM = (5, str, "GLOBAL_CHECKSUM")
    """ Index for some type of dataset-scope checksum. """
    ELEMENT_ID = (6, str, "ELEMENT_ID")
    """ A general-purpose index for the applicable data element unique identifier. """
    REALIZATION_CONFIG_DATA_ID = (7, str, "REALIZATION_CONFIG_DATA_ID")
    """ A specialized index for the unique data id of an associated realization config dataset. """

    def __new__(cls, index: int, ty: type, name: str):
        o = str.__new__(cls, name)
        o._value_ = (index, ty, name)
        return o

    @classmethod
    def get_for_name(cls, name_str: str) -> 'StandardDatasetIndex':
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return StandardDatasetIndex.UNKNOWN

def _validate_variable_is_known(cls, variable: StandardDatasetIndex) -> StandardDatasetIndex:
    if variable == StandardDatasetIndex.UNKNOWN:
        raise ValueError("Invalid value for {} variable: {}".format(cls.__name__, variable))
    return variable


class DataFormat(PydanticEnum):
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
                {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: ""},
                {"": datetime, "APCP_surface": float, "DLWRF_surface": float, "DSWRF_surface": float,
                 "PRES_surface": float, "SPFH_2maboveground": float, "TMP_2maboveground": float,
                 "UGRD_10maboveground": float, "VGRD_10maboveground": float, "precip_rate": float},
                True
                )
    """ The CSV data format the Nextgen framework originally used during its early development. """
    NETCDF_FORCING_CANONICAL = (1,
                                {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: "time"},
                                {"time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float,
                                 "U2D": float, "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float,
                                 "offset": int},
                                True
                                )
    """ The Nextgen framework "canonical" NetCDF forcing data format. """
    # TODO: need to look at actual format and fix this
    NETCDF_AORC_DEFAULT = (2,
                           {StandardDatasetIndex.CATCHMENT_ID: "ids", StandardDatasetIndex.TIME: "Time"},
                           {"ids": str, "Time": datetime, "RAINRATE": float, "T2D": float, "Q2D": float, "U2D": float,
                            "V2D": float, "PSFC": float, "SWDOWN": float, "LWDOWN": float, "offset": int},
                           True
                           )
    """ The default format for "raw" AORC forcing data. """
    NGEN_OUTPUT = (3,
                   {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None, StandardDatasetIndex.DATA_ID: None},
                   None,
                   True)
    """ Representation of the format for Nextgen output, with unknown/unspecified configuration of output fields. """
    NGEN_REALIZATION_CONFIG = (
        4, {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None, StandardDatasetIndex.DATA_ID: None}, None, True)
    """ Representation of the format of realization configs, which covers catchments (id) has a time period (time). """
    NGEN_GEOJSON_HYDROFABRIC = (5,
                                {StandardDatasetIndex.CATCHMENT_ID: "id", StandardDatasetIndex.HYDROFABRIC_ID: None, StandardDatasetIndex.DATA_ID: None},
                                {"id": str, "properties": Any, "geometry": Any},
                                )
    """ GeoJSON hydrofabric format used by Nextgen (id is catchment id). """
    NGEN_PARTITION_CONFIG = (6,
                             {StandardDatasetIndex.DATA_ID: None, StandardDatasetIndex.HYDROFABRIC_ID: None, StandardDatasetIndex.LENGTH: None},
                             {"id": int, "cat-ids": List[str], "nex-id": List[str], "remote-connections": List[Dict[str, int]]},
                             )
    """ GeoJSON hydrofabric format used by Nextgen. """
    BMI_CONFIG = (7, {StandardDatasetIndex.GLOBAL_CHECKSUM: None, StandardDatasetIndex.DATA_ID: None}, None)
    """ Format for BMI init configs, of which (in general) there is implied comma-joined filename string checksum. """
    NWM_OUTPUT = (8, {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: "Time", StandardDatasetIndex.DATA_ID: None}, {"Time": datetime, "streamflow": float}, True)
    """ Format for NWM 2.0/2.1/2.2 output. """
    NWM_CONFIG = (9, {StandardDatasetIndex.ELEMENT_ID: None, StandardDatasetIndex.TIME: None, StandardDatasetIndex.DATA_ID: None}, None)
    """ Format for initial config for NWM 2.0/2.1/2.2. """
    NGEN_CAL_OUTPUT = (10,
                       {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None,
                        StandardDatasetIndex.DATA_ID: None},
                       None,
                       False)
    """ Representation of the format for ngen-cal calibration tool output. """
    # TODO: come back later and fill in details of fields
    NGEN_CAL_CONFIG = (11,
                       {StandardDatasetIndex.DATA_ID: None, StandardDatasetIndex.TIME: None,
                        StandardDatasetIndex.REALIZATION_CONFIG_DATA_ID: None,
                        StandardDatasetIndex.HYDROFABRIC_ID: None},
                       None,
                       False)
    """ Format representing ngen-cal configurations. """
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

    def __init__(self, uid: int, indices_to_fields: Dict[StandardDatasetIndex, Optional[str]],
                 data_fields: Optional[Union[Dict[str, Type], Set[str]]] = None, is_time_series: bool = False):
        self._uid = uid
        self._indices_to_fields = indices_to_fields
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
        self._is_time_series_index = is_time_series

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
        List of the string forms of the applicable ::class:`StandardDataIndex` properties for this format.

        Returns
        -------
        List[str]
            List of the string forms of the applicable standard indices properties for this format.
        """
        return [std_idx.name for std_idx in self.indices_to_fields().keys()]

    def indices_to_fields(self) -> Dict[StandardDatasetIndex, Optional[str]]:
        """
        The mapping of the indices properties for this format, to the names of the corresponding fields within the data.

        Note that when an index is an implicit or metadata value, and not within the data itself, the index maps to
        ``None``.  An example of this is in the ``AORC_CSV`` format with its ``CATCHMENT_ID`` index, because datasets
        with this format contain their data in individual, catchment-specific CSV files (named based on the catchment
        id) that do not explicitly contain the catchment id within individual data records.

        Returns
        -------
        Dict[StandardDatasetIndex, Optional[str]]
            Mapping of the indices properties for this format to data field names (when in the data) or ``None``.
        """
        return self._indices_to_fields

    @property
    def is_time_series(self) -> bool:
        """
        Whether this type is a format of time series data.

        Returns
        -------
        bool
            Whether this type is a format of time series data.
        """
        return self._is_time_series_index


class ContinuousRestriction(Serializable):
    """
    A filtering component, typically applied as a restriction on a domain, by a continuous range of values of a variable.
    """
    variable: StandardDatasetIndex
    begin: datetime
    end: datetime
    datetime_pattern: Optional[str]
    subclass: PyObject

    @root_validator(pre=True)
    def coerce_times_if_datetime_pattern(cls, values):
        subclass_str = values.get("subclass")

        if subclass_str is None:
            values["subclass"] = cls

        if isinstance(subclass_str, str):
            if subclass_str == cls.__name__:
                values["subclass"] = cls

            for subclass in get_subclasses(cls):
                if subclass_str == subclass.__name__:
                    values["subclass"] = subclass

        datetime_ptr = values.get("datetime_pattern")

        if datetime_ptr is not None:
            # If there is a datetime pattern, then expect begin and end to parse properly to datetime objects
            begin = values["begin"]
            end = values["end"]

            if not isinstance(begin, datetime):
                values["begin"] = datetime.strptime(begin, datetime_ptr)

            if not isinstance(end, datetime):
                values["end"] = datetime.strptime(end, datetime_ptr)
        return values

    @root_validator()
    def validate_start_before_end(cls, values):
        if values["begin"] > values["end"]:
            raise RuntimeError("Cannot have {} with begin value larger than end.".format(cls.__name__))

        return values

    # validate variable is not UNKNOWN variant
    _validate_variable = validator("variable", allow_reuse=True)(_validate_variable_is_known)

    class Config:
        def _serialize_datetime(self: "ContinuousRestriction", value: datetime) -> str:
            if self.datetime_pattern is not None:
                return value.strftime(self.datetime_pattern)
            return str(value)

        field_serializers = {
            "begin": _serialize_datetime,
            "end": _serialize_datetime,
            "subclass": lambda value: value.__name__
            }

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ContinuousRestriction):
            return False
        return self.variable == o.variable and self.begin == o.begin and self.end == o.end and self.datetime_pattern == o.datetime_pattern

    def __hash__(self) -> int:
        return hash((self.variable, self.begin, self.end, self.datetime_pattern))

    @classmethod
    def convert_truncated_serial_form(cls, truncated_json_obj: dict, datetime_format: Optional[str] = None) -> dict:
        """
        Take the JSON in a truncated format and generated a converted copy in the valid serialized form of this type.

        Parameters
        ----------
        truncated_json_obj : dict
            The simplified JSON representation that can be used, with some intelligence, to derive an instance.
        datetime_format : str
            An optional datetime format string to test ``begin`` and ``end`` for times (replaced with the default from
            ::method:`get_datetime_str_format` if not included or ``None``).

        Returns
        -------
        dict
            A new dictionary object, based on the arg, but with extra items added to it in order to make it consistent
            with the format required by the standard ::method:`factory_init_from_deserialized_json` of this type.
        """
        json_copy = truncated_json_obj.copy()
        try:
            format_str = cls.get_datetime_str_format() if datetime_format is None else datetime_format
            begin_time = datetime.strptime(truncated_json_obj['begin'], format_str)
            end_time = datetime.strptime(truncated_json_obj['end'], format_str)
            if isinstance(begin_time, datetime) and isinstance(end_time, datetime):
                json_copy['datetime_pattern'] = format_str
                json_copy['subclass'] = 'TimeRange'
        except:
            if 'subclass' not in json_copy:
                json_copy['subclass'] = cls.__name__

        return json_copy

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict):
        if "subclass" in json_obj:
            try:
                subclass_str = json_obj["subclass"]

                if subclass_str == cls.__name__:
                    json_obj["subclass"] = cls
                    return cls(**json_obj)

                for subclass in cls.__subclasses__():
                    if subclass.__name__ == subclass_str:
                        json_obj["subclass"] = subclass
                        return subclass(**json_obj)
            except:
                pass

        try:
            return cls(**json_obj)
        except:
            return None

    def __hash__(self) -> int:
        return hash((self.variable.name, self.begin, self.end))

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


class DiscreteRestriction(Serializable):
    """
    A filtering component, typically applied as a restriction on a domain, by a discrete set of values of a variable.

    Note that an empty list for the ::attribute:`values` property implies a restriction of all possible values being
    required.  This is reflected by the :method:`is_all_possible_values` property.
    """
    variable: StandardDatasetIndex
    values: Union[List[StrictStr], List[StrictFloat], List[StrictInt]]

    # validate variable is not UNKNOWN variant
    _validate_variable = validator("variable", allow_reuse=True)(_validate_variable_is_known)

    def __init__(
        self,
        variable: Union[str, StandardDatasetIndex],
        values: Union[List[StrictStr], List[StrictFloat], List[StrictInt]],
        allow_reorder: bool = True,
        remove_duplicates: bool = True,
        **kwargs
    ):
        super().__init__(variable=variable, values=values, **kwargs)
        if remove_duplicates:
            self.values = list(OrderedDict.fromkeys(self.values))
        if allow_reorder:
            self.values.sort()

    def __hash__(self) -> int:
        return hash((self.variable.name, *self.values))

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


class DataDomain(Serializable):
    """
    A domain for a dataset, with domain-defining values contained by one or more discrete and/or continuous components.
    """
    data_format: DataFormat = Field(
    description="The format for the data in this domain, which contains details like the indices and other data fields."
    )
    continuous_restrictions: Optional[Dict[StandardDatasetIndex, ContinuousRestriction]] = Field(
        description="Map of the continuous restrictions defining this domain, keyed by variable name.",
        alias="continuous",
        default_factory=dict
    )
    discrete_restrictions: Optional[Dict[StandardDatasetIndex, DiscreteRestriction]] = Field(
        description="Map of the discrete restrictions defining this domain, keyed by variable name.",
        alias="discrete",
        default_factory=dict
    )
    # NOTE: remove this field after #239 is merged. will close #245.
    custom_data_fields: Optional[Dict[str, Union[str, int, float, Any]]] = Field(
        description=("This will either be directly from the format, if its format specifies any fields, or from a custom fields"
                     "attribute that may be set during initialization (but is ignored when the format specifies fields)."),
        alias="data_fields"
    )

    @validator("continuous_restrictions", pre=True, always=True)
    def _validate_continuous_restriction_default(cls, value):
        if value is None:
            return dict()
        elif isinstance(value, list):
            values = {}
            for restriction in value:
                if not isinstance(restriction, ContinuousRestriction):
                    restriction = ContinuousRestriction.factory_init_from_deserialized_json(restriction)
                values[restriction.variable] = restriction
            return values
        return value

    @validator("discrete_restrictions", pre=True, always=True)
    def _validate_discrete_restriction_default(cls, value):
        if value is None:
            return dict()
        elif isinstance(value, list):
            values = {}
            for restriction in value:
                if not isinstance(restriction, DiscreteRestriction):
                    restriction = DiscreteRestriction.parse_obj(restriction)
                values[restriction.variable] = restriction
            return values
        return value

    @validator("custom_data_fields")
    def validate_data_fields(cls, values):
        def handle_type_map(t):
            if t == "str" or t == str:
                return str
            elif t == "int" or t == int:
                return int
            elif t == "float" or t == float:
                return float
            elif t == "bool" or t == bool:
                return bool
            # maintain reference to a passed in python type or subtype
            elif isinstance(t, type):
                return t
            return Any

        if values is None:
            return None

        return {k: handle_type_map(v) for k, v in values.items()}

    @root_validator()
    def validate_sufficient_restrictions(cls, values):
        continuous_restrictions = values.get("continuous_restrictions", {})
        discrete_restrictions = values.get("discrete_restrictions", {})
        if len(continuous_restrictions) + len(discrete_restrictions) == 0:
            msg = "Cannot create {} without at least one finite continuous or discrete restriction"
            raise RuntimeError(msg.format(cls.__name__))
        return values

    @classmethod
    def factory_init_from_restriction_collections(cls, data_format: DataFormat, **kwargs) -> 'DataDomain':
        """
        Create and return a data domain object of the given format and keyword args containing restriction properties.

        The key for each restriction determines the appropriate ::class:`StandardDatasetIndex` for the restriction's
        ``variable`` property via ::method:`StandardDatasetIndex.get_for_name``.

        The restriction property values should either be a single value, a list, or a dictionary with exactly two inner
        keys.  Single values are converted to one-items lists, then otherwise treated as lists. Lists represent
        discrete restrictions and may be of arbitrary length. Dictionaries represent continuous restrictions and must
        have exactly two elements (see below for valid inner keys and their meaning).  There is also the special case
        when the (keyword args) key translates to ``StandardDatasetIndex.TIME``, which results in use of the
        ::class:`TimeRange` subtype and must be continuous.

        For list values, the value is used directly for ::attribute:`DiscreteRestriction.values`. For dictionary values,
        the inner keys of each dictionary must be either ``begin`` or ``start`` for the beginning of
        the range, and ``end`` or ``finish`` for the end.

        Parameters
        ----------
        data_format
        kwargs

        Returns
        -------
        DataDomain
        """
        continuous = []
        discrete = []

        for k, v in kwargs.items():
            # First convert string values to one-item lists (will get caught by the Iterable test otherwise)
            if isinstance(v, str):
                v = [v]
            # Also convert anything else that is not an Iterable to a one-item list
            elif not isinstance(v, Iterable):
                v = [v]

            linked_index = StandardDatasetIndex.get_for_name(k)
            if linked_index == StandardDatasetIndex.UNKNOWN:
                msg = "Unrecognized domain property {} when creating domain with {} format".format(k, data_format.name)
                raise RuntimeError(msg)
            elif linked_index not in data_format.indices_to_fields().keys():
                msg = "Unexpected index {} when creating domain with {} format".format(k, data_format.name)
                raise RuntimeError(msg)
            elif isinstance(v, list):
                discrete.append(DiscreteRestriction(variable=linked_index, values=v))
            elif not isinstance(v, dict):
                msg = "Invalid value type {} for {} restriction when creating domain".format(v.__class__.__name__, k)
                raise ValueError(msg)
            elif len(v.keys()) != 2:
                msg = "Invalid value dict of size {} for {} restriction when creating domain".format(v.keys(), k)
                raise ValueError(msg)
            elif isinstance(v, dict) and ('begin' in v or 'start' in v) and ('end' in v or 'finish' in v):
                begin = v['begin'] if 'begin' in v else v['start']
                end = v['end'] if 'end' in v else v['finish']
                if linked_index == StandardDatasetIndex.TIME:
                    continuous.append(TimeRange(begin=begin, end=end))
                else:
                    continuous.append(ContinuousRestriction(variable=linked_index, begin=begin, end=end))
            else:
                msg = "Invalid value dict (missing required keys) for {} restriction when creating domain".format(k)
                raise ValueError(msg)

        return DataDomain(data_format=data_format,
                          continuous_restrictions=None if len(continuous) == 0 else continuous,
                          discrete_restrictions=None if len(discrete) == 0 else discrete)

    def __hash__(self) -> int:
        cu = [] if self.custom_data_fields is None else [tup for tup in sorted(self.custom_data_fields.items())]
        return hash((self.data_format.name,
                     *[v for _, v in sorted(self.continuous_restrictions.items(), key=lambda dt: dt[0].name)],
                     *[v for _, v in sorted(self.discrete_restrictions.items(), key=lambda dt: dt[0].name)],
                     *cu
                     ))

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
        elif self.data_format != other.data_format:
            return False
        else:
            for index in other.continuous_restrictions:
                if not self._extends_continuous_restriction(other.continuous_restrictions[index]):
                    return False
            for index in other.discrete_restrictions:
                if not self._extends_discrete_restriction(other.discrete_restrictions[index]):
                    return False
            return True

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
            return self.custom_data_fields
        else:
            return self.data_format.data_fields

    @property
    def indices(self) -> List[str]:
        """
        List of the string forms of the ::class:`StandardDataIndex` indices that define this domain.

        This list contains the names of indices (i.e., in the context of some ::class:`DataFormat`) that are used to
        define this data domain.

        Returns
        -------
        List[str]
            List of the string forms of the ::class:`StandardDataIndex` indices that define this domain.
        """
        return self.data_format.indices

    @staticmethod
    def _encode_py_type(o: type) -> str:
        """Return string representation of a built in type (e.g. 'int') or 'Any'."""
        if o in {str, int, float, bool}:
            return o.__name__
        return "Any"

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = True, # Note this follows Serializable convention
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> Dict[str, Union[str, int]]:
        """
        `data_fields` is excluded from dict if `self.data_format.data_fields` is None.

        called by `to_dict` and `to_json`.
        """
        DATA_FIELDS_KEY = "custom_data_fields"
        DATA_FIELDS_ALIAS_KEY = "data_fields"

        exclude = exclude or set()

        exclude_data_fields = DATA_FIELDS_KEY in exclude
        exclude.add(DATA_FIELDS_KEY)

        serial = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        # NOTE: `custom_data_fields` is excluded if it is a empty T variant. This breaks with
        # Serializable's convention to only exclude `None` value fields.
        if exclude_data_fields or self.data_format.data_fields or not self.custom_data_fields:
            return serial

        # serialize "custom_data_fields" python types
        custom_data_fields = (
            {k: self._encode_py_type(v) for k, v in self.custom_data_fields.items()}
            if self.custom_data_fields is not None
            else dict()
        )

        if by_alias:
            serial[DATA_FIELDS_ALIAS_KEY] = custom_data_fields
            return serial

        serial[DATA_FIELDS_KEY] = custom_data_fields
        return serial


class DataCategory(PydanticEnum):
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
    variable: StandardDatasetIndex = Field(StandardDatasetIndex.TIME, const=True)

    @classmethod
    def parse_from_string(cls, as_string: str, dt_format: Optional[str] = None, dt_str_length: int = 19) -> 'TimeRange':
        """
        Parse a colloquial string representation of a time range to an object.

        Parse a string representation to an instance.  Any string that begins and ends with independent, valid date+time
        substrings qualifies; e.g., "<datetime> to <datetime>" or "<datetime> - <datetime>".

        Parameters
        ----------
        as_string: str
            The representation of an instance in the form of a begin and end datetime string.
        dt_format: Optional[str]
            The optional datetime parsing format pattern, ``None`` by default, which is replaced with the pattern
            returned by ::method:`get_datetime_str_format`.
        dt_str_length: int
            The length of a valid date+time substring, needed for individually parsing it, which should correspond to
            the current ``dt_format`` (default: 19).

        Returns
        -------
        TimeRange
            The parsed instance.
        """
        if dt_format is None:
            dt_format = cls.get_datetime_str_format()

        # This can't be valid, so sanity check for it
        if dt_str_length < len(dt_format):
            raise ValueError("Invalid datetime substring length of {} for format {}".format(dt_str_length, dt_format))

        # This is an absolute min
        if len(as_string) < dt_str_length * 2:
            raise ValueError("String '{}' cannot contain two datetime substrings".format(as_string))

        try:
            return cls(begin=datetime.strptime(as_string[:dt_str_length], dt_format),
                       end=datetime.strptime(as_string[(-1 * dt_str_length):], dt_format))
        except:
            raise ValueError


class DataRequirement(Serializable):
    """
    A definition of a particular data requirement needed for an execution task.
    """
    category: DataCategory
    domain: DataDomain
    fulfilled_access_at: Optional[str] = Field(description="The location at which the fulfilling dataset for this requirement is accessible, if the dataset known.")
    fulfilled_by: Optional[str] = Field(description="The name of the dataset that will fulfill this, if it is known.")
    is_input: bool = Field(description="Whether this represents required input data, as opposed to a requirement for storing output data.")
    size: Optional[int]

    def __eq__(self, other: object) -> bool:
        return (
            self.__class__ == other.__class__
            and self.domain == other.domain
            and self.is_input == other.is_input
            and self.category == other.category
        )

    def __hash__(self):
        return hash((self.domain, self.is_input, self.category))

    def dict(self, **kwargs) -> dict:
        exclude_unset = True if kwargs.get("exclude_unset") is None else False
        kwargs["exclude_unset"] = exclude_unset
        return super().dict(**kwargs)
