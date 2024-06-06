from __future__ import annotations

from datetime import datetime

from .enum import PydanticEnum
from .serializable import Serializable
from .common.helper_functions import get_subclasses
from .exception import DmodRuntimeError
from typing import Any, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union
from typing_extensions import Self
from collections.abc import Iterable
from collections import OrderedDict
from pydantic import (
    root_validator,
    validator,
    Field,
    StrictStr,
    StrictFloat,
    StrictInt,
)
import warnings


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
    FILE_NAME = (8, str, "FILE_NAME")
    """ Index for the name of a data file within a dataset. """
    COMPOSITE_SOURCE_ID = (9, str, "COMPOSITE_SOURCE_ID")
    """ Index for DATA_ID values of source dataset(s) when dataset is composite format and derives from others. """
    HYDROFABRIC_VERSION = (10, str, "HYDROFABRIC_VERSION")
    """ Version string for version of the hydrofabric to use (e.g., 2.0.1). """
    HYDROFABRIC_REGION = (11, str, "HYDROFABRIC_REGION")
    """ Region string (e.g., conus, vpu01) for the applicable region of the hydrofabric. """

    def __new__(cls, index: int, ty: type, name: str):
        o = str.__new__(cls, name)
        o._value_ = (index, ty, name)
        return o

    @classmethod
    def get_for_name(cls, name_str: str) -> StandardDatasetIndex:
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
                {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: "Time"},
                {"Time": datetime, "RAINRATE": float, "Q2D": float, "T2D": float, "U2D": float, "V2D": float,
                 "LWDOWN": float, "SWDOWN": float, "PSFC": float},
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
    NGEN_CSV_OUTPUT = (3,
                       {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None, StandardDatasetIndex.DATA_ID: None},
                       None,
                       True)
    """ Format for output of ngen when written as CSV, with unknown/unspecified configuration of output fields. """
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
    NGEN_JOB_COMPOSITE_CONFIG = (
        12,
        {
            StandardDatasetIndex.HYDROFABRIC_ID: None,
            StandardDatasetIndex.CATCHMENT_ID: None,
            StandardDatasetIndex.TIME: None,
            StandardDatasetIndex.DATA_ID: None,
            StandardDatasetIndex.FILE_NAME: None,
            StandardDatasetIndex.COMPOSITE_SOURCE_ID: None
        },
        None,
        False
    )
    """ 
    Composite format for the different configs needed to run an ngen.
    
    A dataset in this format will include a realization config and BMI configs.  It may also include a t-route config
    and/or an ngen-cal config, depending on whether routing and/or calibration is being performed.
    
    Note such datasets won't include the hydrofabric. That provides the context under which everything else has meaning,
    including things like forcing data, so it should be kept separate.  Forcings are also excluded, largely because they
    may get large and difficult to copy, and thus should be handled on their own.  Further, partition configurations
    are also handled separately.  These affect execution at a different layer; i.e., a change in the partition config
    should not impact the output, only the execution.  As such, it may be advantageous to retry the same job using many
    different partitioning schemes, making it useful to keep it as a thing unto itself.
    """

    T_ROUTE_CONFIG = (13, {StandardDatasetIndex.DATA_ID: None, StandardDatasetIndex.HYDROFABRIC_ID: None}, None, False)
    """ Format for t-route application configuration. """

    NGEN_GEOPACKAGE_HYDROFABRIC_V2 = (14,
                                      {StandardDatasetIndex.CATCHMENT_ID: "divide_id",
                                       StandardDatasetIndex.HYDROFABRIC_ID: None,
                                       StandardDatasetIndex.HYDROFABRIC_REGION: None,
                                       StandardDatasetIndex.HYDROFABRIC_VERSION: None},
                                      {"fid": int, "divide_id": str, "geom": Any, "toid": str, "type": str,
                                       "ds_id": float, "areasqkm": float, "id": str, "lengthkm": float,
                                       "tot_drainage_areasqkm": float, "has_flowline": bool},
                                      )
    """ GeoPackage hydrofabric format v2 used by NextGen (id is catchment id). """

    EMPTY = (15, {}, None, False)
    """
    "Format" for an empty dataset that, having no data (yet), doesn't have (or need) an applicable defined structure.
    
    The intent of this is for simplicity when creating dataset.  This format represents a type of dataset that doesn't,
    and importantly, **cannot** yet truly have a more specific format that matches its contents.  A key implication is
    an expectation is that the domain of the dataset (including the format) **must** be changed as soon as any data is
    added to the dataset.
    """

    GENERIC = (16, {}, None, False)
    """ 
    Format without any indications or restrictions on the defined structure of contained data. 
    
    This value is very much like ``EMPTY`` except that it is applicable to non-empty datasets.  It represents absolutely
    nothing about the structure of any contents, and thus that absolutely anything can be contained or added.  In
    practice, the main intended difference from ``EMPTY`` is that datasets in this format will not be required to update
    their data domain at the time new data is added (while not applicable to ``EMPTY``, the same is true when any data
    is removed).
    """

    ARCHIVED_NGEN_CSV_OUTPUT = (17,
                       {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None, StandardDatasetIndex.DATA_ID: None},
                       None,
                       True)
    """ Format for output of ngen, similar to ``NGEN_CSV_OUTPUT``, but with all output archived to single tar file. """

    NGEN_NETCDF_OUTPUT = (18,
                          {StandardDatasetIndex.CATCHMENT_ID: None, StandardDatasetIndex.TIME: None,
                           StandardDatasetIndex.DATA_ID: None},
                          None,
                          True)
    """ Format for output of ngen when written to single NetCDF file, with dynamically configured output fields. """

    @classmethod
    def can_format_fulfill(cls, needed: DataFormat, alternate: DataFormat) -> bool:
        """
        Test whether a dataset and contained data in some format can satisfy requirements of a different format.

        This function indicates whether a hypothetical dataset and its data, having some particular format (the
        alternate format) is compatible with hypothical requirements specified using a different format (the needed
        format).  It is an indication of whether a dataset and its data are **potentially** capable of satisfying a
        requirement, even with a different format, due to the two formats being sufficiently similar.

        For example, the NextGen framework can support forcings in either CSV or NetCDF formats, represented as
        ``AORC_CSV`` and ``NETCDF_FORCING_CANONICAL`` respectively.  A job to execute NextGen would include a forcing
        ::class:`DataRequirement` associated (albeit indirectly) with a particular format, with that being one of the
        aforementioned values.  However, even if the ``AORC_CSV`` data format was in the requirement, data in the
        ``NETCDF_FORCING_CANONICAL`` format would be perfectly satisfactory (assuming it otherwise provided what the
        job needed).

        Note that the following **is not guaranteed** for all values of ``f_1`` and ``f_2`` (though it will often be the
        case):

            ``can_format_fulfill(needed=f_1, alternate=f_2) == can_format_fulfill(needed=f_2, alternate=f_1)``

        It is guaranteed that ``can_format_fulfill(needed=f_1, alternate=f_1)`` is ``True``.

        Parameters
        ----------
        needed : DataFormat
            The format defined by some requirement.
        alternate : DataFormat
            An alternate format for data.

        Returns
        -------
        bool
            Whether the alternate format is compatible with the needed format.
        """
        # Always return True for when the params are the same format
        if needed == alternate:
            return True
        # For these forcing formats, they will all be compatible with each other
        compatible_forcing_formats = {cls.AORC_CSV, cls.NETCDF_FORCING_CANONICAL, cls.NETCDF_AORC_DEFAULT}
        if needed in compatible_forcing_formats and alternate in compatible_forcing_formats:
            return True

        ngen_csv_output_formats = {cls.ARCHIVED_NGEN_CSV_OUTPUT, cls.NGEN_CSV_OUTPUT}
        if needed in ngen_csv_output_formats and alternate in ngen_csv_output_formats:
            return True

        # Anything else, they are not compatible
        return False

    @classmethod
    def get_for_name(cls, name_str: str) -> Optional[DataFormat]:
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

    If a subclass name is passed to the optional ``subclass`` parameter during initialization the subclass will be
    initialized and returned. For example, `ContinuousRestriction(..., subclass="TimeRange")` would return a
    ``TimeRange`` instance. Invalid ``subclass`` parameter values will return an``ContinuousRestriction`` instance and
    display a RuntimeWarning.
    """

    variable: StandardDatasetIndex
    begin: datetime
    """ An inclusive beginning value. """
    end: datetime
    """ An exclusive end value. """
    datetime_pattern: Optional[str]
    subclass: str = None
    """
    Optional field that when provided factory initializes a subclass instance. This field will _always_ be inialized as
    the instance type's class name.
    """

    def __new__(cls, *_, **kwargs) -> Self:
        """
        Factory return a subclass type if a valid ``subclass`` name is in ``kwargs``. Otherwise, return new of self.
        """
        if "subclass" not in kwargs:
            return super().__new__(cls)

        subclass_str = kwargs["subclass"]
        if not isinstance(subclass_str, str):
            msg = f"{cls.__name__!r}: 'subclass' parameter must be str type. Initializing {cls.__name__!r}"
            warnings.warn(msg, RuntimeWarning)
            return super().__new__(cls)

        if subclass_str == cls.__name__:
            return super().__new__(cls)

        for subclass in get_subclasses(cls):
            if subclass_str == subclass.__name__:
                return super().__new__(subclass)

        msg = f"{subclass_str!r} is not subclass of {cls.__name__!r}. Initializing {cls.__name__!r}."
        warnings.warn(msg, RuntimeWarning)
        return super().__new__(cls)

    @root_validator(pre=True)
    def coerce_times_if_datetime_pattern(cls, values):
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

    @validator("subclass", pre=True, always=True)
    def _validate_subclass(cls, _) -> str:
        return cls.__name__

    # validate variable is not UNKNOWN variant
    _validate_variable = validator("variable", allow_reuse=True)(_validate_variable_is_known)

    class Config:
        def _serialize_datetime(self: "ContinuousRestriction", value: datetime) -> str:
            if self.datetime_pattern is not None:
                return value.strftime(self.datetime_pattern)
            return str(value)

        field_serializers = {
            "begin": _serialize_datetime,
            "end": _serialize_datetime
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
                json_copy['subclass'] = TimeRange
        except:
            if 'subclass' not in json_copy:
                json_copy['subclass'] = cls.__name__

        return json_copy

    def _compatible_with(self, other: ContinuousRestriction) -> bool:
        """
        Whether this is compatible with another instance regarding checks for contains, extension, or subtraction.

        Parameters
        ----------
        other: ContinuousRestriction

        Returns
        -------
        bool
            Whether this is compatible with another instance regarding checks for contains, extension, or subtraction.
        """
        return isinstance(other, ContinuousRestriction) and self.variable == other.variable

    def can_expand_with(self, other: ContinuousRestriction) -> bool:
        """
        Whether another restriction is expansion-compatible with this one.

        Whether another restriction is expansion-compatible with this one.  To be compatible, they must involve the same
        variable and this instance must have a range that overlaps with but is not contained by the range of the other.

        Parameters
        ----------
        other: ContinuousRestriction
            Another restriction.

        Returns
        -------
        bool
            Whether another restriction is expansion-compatible with this one.
        """
        if not self._compatible_with(other):
            return False
        elif other.begin < self.begin:
            return self.begin <= other.end
        elif other.begin == self.begin:
            return self.end < other.end
        # Implies self.begin < other.begin
        else:
            return other.begin <= self.end

    def can_have_subtracted(self, subtrahend: ContinuousRestriction) -> bool:
        """
        Whether another restriction is subtraction-compatible with this one.

        Whether another restriction is expansion-compatible with this one.  To be compatible, the subtrahend must have
        the same variable, be fully contained by this instance, and have either the same :attribute:`begin` or the same
        :attribute:`end` value, but not both.

        Parameters
        ----------
        subtrahend: ContinuousRestriction
            The restriction to potentially be subtracted from this instance.

        Returns
        -------
        bool
            Whether this subtrahend is compatible with subtraction from this instance.

        Notes
        -----
        Equal restrictions cannot be subtracted.  Subtraction must return a restriction, but a restriction with no range
        is undefined.  Also, the domain subtraction operation treats equal restrictions as things that should not be
        changed.

        In practice this makes sense. Subtract a CSV forcing file for one catchment away from a dataset, and that
        file's individual data domain will be for the time range of the dataset and it's single catchment.  So,
        subtracting the data domain of the file from the data domain of the dataset should subtract that one catchment
        from the dataset's domain, but it shouldn't delete (or in any way alter) the time range.

        See Also
        --------
        contains
        subtract
        """
        return (self._compatible_with(subtrahend)
                and self.contains(subtrahend)
                and (self.begin == subtrahend.begin or self.end == subtrahend.end)
                and not (self.begin == subtrahend.begin and self.end == subtrahend.end))

    def contains(self, other: ContinuousRestriction) -> bool:
        """
        Whether this object contains all the values of the given object and the two are of the same variable index.

        For this type, equal begin or end values are considered contained.

        Parameters
        ----------
        other : ContinuousRestriction

        Returns
        -------
        bool
            Whether this object contains all the values of the given object and the two are of the same variable index.
        """
        return self._compatible_with(other) and self.begin <= other.begin and self.end >= other.end

    def expand(self, other: ContinuousRestriction) -> ContinuousRestriction:
        """
        Produce another instance made by combining this instance with the other, assuming they are compatible.

        Parameters
        ----------
        other: ContinuousRestriction

        Returns
        -------
        ContinuousRestriction
            A new instance representing the combined restriction defined by this and the other instance.

        Raises
        ------
        DmodRuntimeError
            Raised if the two instances are not expansion compatible as testable via :method:`can_expand_with`

        See Also
        --------
        can_expand_with
        """
        if not self.can_expand_with(other):
            raise DmodRuntimeError(f"Attempting to extend incompatible {self.__class__.__name__} objects")
        return self.__class__(variable=self.variable, begin=min(self.begin, other.begin), end=max(self.end, other.end),
                              datetime_pattern=self.datetime_pattern, subclass=self.subclass)

    def subtract(self, subtrahend: ContinuousRestriction) -> ContinuousRestriction:
        """
        Produce another instance made by subtracting the given restriction from this one, assuming they are compatible.

        Parameters
        ----------
        subtrahend

        Returns
        -------
        ContinuousRestriction
            A new instance representing the result of subtraction.

        See Also
        --------
        can_have_subtracted
        """
        if not self.can_have_subtracted(subtrahend):
            raise ValueError(f"Can't subtract given {subtrahend.__class__.__name__}")
        new_restrict = ContinuousRestriction(**self.dict())
        if subtrahend.begin == self.begin:
            new_restrict.begin = subtrahend.end
        else:
            new_restrict.end = subtrahend.begin
        return new_restrict

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

    def __eq__(self, other):
        if not isinstance(other, DiscreteRestriction):
            return False
        return self.variable == other.variable and sorted(self.values) == sorted(other.values)

    def __hash__(self) -> int:
        return hash((self.variable.name, *self.values))

    def _compatible_with(self, other: DiscreteRestriction) -> bool:
        """
        Whether this is compatible with another instance regarding checks for contains, extension, or subtraction.

        Parameters
        ----------
        other: DiscreteRestriction

        Returns
        -------
        bool
            Whether this is compatible with another instance regarding checks for contains, extension, or subtraction.
        """
        return isinstance(other, DiscreteRestriction) and self.variable == other.variable

    def can_expand_with(self, other: DiscreteRestriction) -> bool:
        """
        Whether another restriction is expansion-compatible with this one.

        Whether another restriction is expansion-compatible with this one.  To be compatible, they must involve the same
        variable and this instance must not contain the other, according to :method:`contains`.

        Parameters
        ----------
        other: DiscreteRestriction
            Another restriction.

        Returns
        -------
        bool
            Whether another restriction is expansion-compatible with this one.

        See Also
        --------
        contains
        """
        return self._compatible_with(other) and not self.contains(other)

    def can_have_subtracted(self, subtrahend: DiscreteRestriction) -> bool:
        """
        Whether another restriction is subtraction-compatible with this one.

        Whether another restriction is expansion-compatible with this one.  To be compatible, the subtrahend must have
        the same variable and be fully contained by this instance, but not equal to it.

        Parameters
        ----------
        subtrahend: DiscreteRestriction
            The restriction to potentially be subtracted from this instance.

        Returns
        -------
        bool
            Whether this subtrahend is compatible with subtraction from this instance.

        Notes
        -----
        Equal restrictions cannot be subtracted.  A restriction without any explicit values (i.e., with all subtracted)
        has a different implied meaning: "all" within some context).  This is not the desired behavior for subtraction.

        Also, the domain subtraction operation treats equal restrictions as things that should not be changed.  In
        practice this makes sense. Subtract a NetCDF forcing file with data for one hour away from a dataset, and that
        file's individual data domain will be for all catchments for the dataset and that single hour of time.
        So, subtracting the data domain of the file from the data domain of the dataset should subtract that one hour
        (assuming it doesn't split the time range in two) from the dataset's domain, but it shouldn't delete the
        catchments.

        See Also
        --------
        contains
        """
        return self._compatible_with(subtrahend) and self.contains(subtrahend) and not self == subtrahend

    def contains(self, other: DiscreteRestriction) -> bool:
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
        if not self._compatible_with(other):
            return False
        elif self.is_all_possible_values:
            return True
        else:
            value_set = set(self.values)
            for v in other.values:
                if v not in value_set:
                    return False
        return True

    def expand(self, other: DiscreteRestriction) -> DiscreteRestriction:
        """
        Produce another instance made by combining this instance with the other, assuming they are compatible.

        Parameters
        ----------
        other: DiscreteRestriction
            Another restriction object.

        Returns
        -------
        DiscreteRestriction
            A new instance representing the combined restriction defined by this and the other instance.

        Raises
        ------
        DmodRuntimeError
            Raised if the two instances are not expansion-compatible as testable via :method:`can_expand_with`

        See Also
        --------
        can_expand_with
        """
        if not self.can_expand_with(other):
            raise DmodRuntimeError(f"Attempting to extend incompatible {self.__class__.__name__} objects")
        if other.is_all_possible_values:
            return DiscreteRestriction(**other.dict())
        return DiscreteRestriction(variable=self.variable, values=self.values + other.values)

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

    def subtract(self, subtrahend: DiscreteRestriction) -> DiscreteRestriction:
        """
        Produce another instance made by subtracting the given restriction from this one, assuming they are compatible.

        Parameters
        ----------
        subtrahend

        Returns
        -------
        DiscreteRestriction
            A new instance representing the result of subtraction.

        See Also
        --------
        can_have_subtracted
        """
        if not self.can_have_subtracted(subtrahend):
            raise ValueError(f"Can't subtract given {subtrahend.__class__.__name__}")
        if self.is_all_possible_values or subtrahend.is_all_possible_values:
            raise ValueError("Can't subtract unbound restriction")

        new_restrict = DiscreteRestriction(**self.dict())
        for val in (v for v in new_restrict.values if v in subtrahend.values):
            new_restrict.values.remove(val)
        return new_restrict


R = TypeVar("R", bound=Union[ContinuousRestriction, DiscreteRestriction])


class DataDomain(Serializable):
    """
    A domain for some collection of data, with defining values contained by discrete and/or continuous components.

    A definition for the domain of some kind of collection of data.  The collection may be something more concrete, like
    a ::class:`Dataset` instance, or more abstract, like forcing data sufficient to run a requested model execution.

    The definition consists of details on the structure and content of the data within the collection.  Structure is
    represented by a ::class:`DataFormat` attribute, and contents are represented by collections of
    ::class:`ContinuousRestriction` and ::class:`DiscreteRestriction` objects.

    While a domain may have any number of continuous or discrete restrictions individually, combined it must have at
    least one, or validation will fail.

    There is a notion of whether a domain "contains" certain described data.  This described data can be a simple
    description of some data index and values it, fundamentally the definition of ::class:`ContinuousRestriction` and
    ::class:`DiscreteRestriction` objects.  The described data can also be more complex, like another fully defined
    domain.  A function is provided by the type for performing such tests.
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
        data_format = values.get("data_format")
        if data_format == DataFormat.EMPTY or data_format == DataFormat.GENERIC:
            return values
        continuous_restrictions = values.get("continuous_restrictions", {})
        discrete_restrictions = values.get("discrete_restrictions", {})
        if len(continuous_restrictions) + len(discrete_restrictions) > 0:
            return values
        raise RuntimeError(f"Cannot create {cls.__name__} without at least one finite continuous or discrete "
                           f"restriction, except when data format is {DataFormat.GENERIC.name} or "
                           f"{DataFormat.EMPTY.name} (provided value was: "
                           f"{'None' if data_format is None else data_format.name})")

    @classmethod
    def factory_init_from_restriction_collections(cls, data_format: DataFormat, **kwargs) -> DataDomain:
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

    @classmethod
    def subtract_domains(cls, minuend: DataDomain, subtrahend: DataDomain) -> DataDomain:
        """
        Subtract part of a defined data domain along a single dimension, producing a domain that is "smaller."

        Subtraction the subtrahend from the minuend along one dimension - i.e., one constraint variable.  Constraints
        only in one of the domains are ignored, as are constraints that are exactly equal across the two domains (the
        subtraction operation should make the result smaller in one dimension, not remove that dimension from it).

        Parameters
        ----------
        minuend: DataDomain
            The original, larger domain to be subtracted from.
        subtrahend: DataDomain
            The portion to be subtracted from the minuend.

        Raises
        ------
        ValueError
            If the formats or restriction constraints of the two domains do not support a subtraction to be performed.

        Returns
        -------
        DataDomain
            The new, updated domain value, as a new object.
        """
        # TODO: (later) consider exceptions to format rule (here and in merging) and perhaps other behavior, like for composites
        if minuend.data_format != subtrahend.data_format:
            raise ValueError(f"Can't subtract {subtrahend.data_format.name} domain from {minuend.data_format.name} one")

        def get_subtractables(r_minuend: Dict[StandardDatasetIndex, R],
                              r_subtrahend: Dict[StandardDatasetIndex, R]
                              ) -> Set[StandardDatasetIndex]:
            indices_in_both = {idx for idx in r_minuend if idx in r_subtrahend}
            indices_unequal = {idx for idx in indices_in_both if r_minuend[idx] != r_subtrahend[idx]}
            can_subtract = {idx for idx in indices_in_both if r_minuend[idx].can_have_subtracted(r_subtrahend[idx])}
            cannot_subtract = indices_unequal - can_subtract

            if cannot_subtract:
                raise ValueError(f"Can't subtract incompatible constraint values for "
                                 f"{[idx.name for idx in cannot_subtract]!s}")
            return can_subtract

        cont_rest_diffs = get_subtractables(minuend.continuous_restrictions, subtrahend.continuous_restrictions)
        discr_rest_diffs = get_subtractables(minuend.discrete_restrictions, subtrahend.discrete_restrictions)

        if not cont_rest_diffs and not discr_rest_diffs:
            raise ValueError(f"Nothing in domain {subtrahend!s} needs to be subtracted from {minuend!s}")
        elif len(cont_rest_diffs) + len(discr_rest_diffs) > 1:
            raise ValueError(f"Can't subtract across more than one dimension at a time.")

        # Make a copy, and we'll remove things from it
        new_dom = DataDomain(**minuend.to_dict())

        for std_idx in cont_rest_diffs:
            new_dom.continuous_restrictions[std_idx].subtract(subtrahend.continuous_restrictions[std_idx])
        for std_idx in discr_rest_diffs:
            new_dom.discrete_restrictions[std_idx].subtract(subtrahend.discrete_restrictions[std_idx])

        return new_dom

    @classmethod
    def merge_domains(cls, d1: DataDomain, d2: DataDomain) -> DataDomain:
        """
        Merge two domains into a new combined domain, combining values along a single restriction variable dimension.

        Merge the values of two compatible domain objects into a combined domain object.  In order to be compatible,
        the two domains must be of the same :class:`DataFormat` and have at most one different restriction value. Unlike
        subtraction, this includes restrictions only present on one of the two domains.

        Also unlike subtraction, strictly speaking, domains are merge-compatible if they are equal or if one contains
        the other; i.e., these cases are valid for the function.  However, the function will not have any side effects
        in those situations.

        Related to the above, the returned domain will be a new :class:`DataDomain` object, with two exceptions:
            - if one domain already fully contains the other, then the original, containing domain object is returned
            - if the domains are equal, then `d1` is returned

        Parameters
        ----------
        d1: DataDomain
            The first domain.
        d2: DataDomain
            The second domain.

        Returns
        -------
        DataDomain
            The resulting domain from the merge operation.

        Raises
        ------
        ValueError
            If the formats or restriction constraints of the two domains do not permit them to be merged.

        See Also
        --------
        subtract_domains
        """
        # TODO: (later) consider exceptions to format rule (here and in subtracting) and perhaps other behavior, like for composites
        if d1.data_format != d2.data_format:
            raise ValueError(f"Can't merge {d2.data_format.name} format domain into one of {d1.data_format.name}")

        if d1 == d2:
            return d1
        elif d1.contains(d2):
            return d1
        elif d2.contains(d1):
            return d2

        def merge_diff(d1_restricts: Dict[StandardDatasetIndex, R], d2_restricts: Dict[StandardDatasetIndex, R]
                       ) -> Optional[R]:
            all_indices = set(d1_restricts.keys()).union(d2_restricts.keys())
            only_in_1 = {idx for idx in d1_restricts if idx not in d2_restricts}
            only_in_2 = {idx for idx in d2_restricts if idx not in d1_restricts}
            in_both = {idx for idx in all_indices if idx not in only_in_1 and idx not in only_in_2}
            unequal = {idx for idx in in_both if d1_restricts[idx] != d2_restricts[idx]}
            if len(only_in_1) + len(only_in_2) + len(unequal) == 0:
                return None
            if len(only_in_1) + len(only_in_2) + len(unequal) > 1:
                raise ValueError(f"Can't support multiple different restrictions (even of one type) when merging")
            if only_in_1:
                value = d1_restricts[only_in_1.pop()]
                return value.__class__(**value.dict())
            if only_in_2:
                value = d2_restricts[only_in_2.pop()]
                return value.__class__(**value.dict())
            idx = unequal.pop()
            try:
                return d1_restricts[idx].expand(d2_restricts[idx])
            except Exception as e:
                raise ValueError(f"Failure merging restriction for domain due to {e.__class__.__name__}: {e!s}")

        cont_restrict_diff = merge_diff(d1.continuous_restrictions, d2.continuous_restrictions)
        discr_restrict_diff = merge_diff(d1.discrete_restrictions, d2.discrete_restrictions)
        new_domain = DataDomain(**d1.dict())

        if cont_restrict_diff and discr_restrict_diff:
            raise ValueError(f"Can't merge {d1!s} and {d2!s} with continuous and discrete restriction differences")
        elif not cont_restrict_diff and not discr_restrict_diff:
            raise AssertionError(f"Should not reach this condition with no different restriction in merging domains")
        elif cont_restrict_diff:
            new_domain.continuous_restrictions[cont_restrict_diff.variable] = cont_restrict_diff
        else:
            new_domain.discrete_restrictions[discr_restrict_diff.variable] = discr_restrict_diff

        return new_domain

    def __eq__(self, other):
        return isinstance(other, DataDomain) and hash(self) == hash(other)

    def __hash__(self) -> int:
        custom_fields = [] if self.custom_data_fields is None else sorted(self.custom_data_fields.items())
        return hash((self.data_format.name,
                     *[v for _, v in sorted(self.continuous_restrictions.items(), key=lambda dt: dt[0].name)],
                     *[v for _, v in sorted(self.discrete_restrictions.items(), key=lambda dt: dt[0].name)],
                     *custom_fields
                     ))

    def _extends_continuous_restriction(self, continuous_restriction: ContinuousRestriction) -> bool:
        idx = continuous_restriction.variable
        return idx in self.continuous_restrictions and self.continuous_restrictions[idx].contains(continuous_restriction)

    def _extends_discrete_restriction(self, discrete_restriction: DiscreteRestriction) -> bool:
        idx = discrete_restriction.variable
        return idx in self.discrete_restrictions and self.discrete_restrictions[idx].contains(discrete_restriction)

    def contains(self, other: Union[ContinuousRestriction, DiscreteRestriction, DataDomain]) -> bool:
        """
        Whether this domain contains the given domain or collection of domain index values.

        Parameters
        ----------
        other : Union[ContinuousRestriction, DiscreteRestriction, DataDomain]
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
        elif not DataFormat.can_format_fulfill(needed=other.data_format, alternate=self.data_format):
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
        data_fields_key = "custom_data_fields"
        data_fields_alias_key = "data_fields"

        exclude = exclude or set()

        exclude_data_fields = data_fields_key in exclude
        exclude.add(data_fields_key)

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
            serial[data_fields_alias_key] = custom_data_fields
            return serial

        serial[data_fields_key] = custom_data_fields
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
    def get_for_name(cls, name_str: str) -> Optional[DataCategory]:
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return None


class TimeRange(ContinuousRestriction):
    """
    Encapsulated representation of a time range.
    """
    variable: StandardDatasetIndex = Field(StandardDatasetIndex.TIME.name, const=True)

    @classmethod
    def parse_from_string(cls, as_string: str, dt_format: Optional[str] = None, dt_str_length: int = 19) -> TimeRange:
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
        kwargs["exclude_unset"] = kwargs.get("exclude_unset", True)
        return super().dict(**kwargs)
