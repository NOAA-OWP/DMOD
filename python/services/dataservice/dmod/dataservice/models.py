from enum import Enum
from datetime import datetime
from fastapi import UploadFile
from pydantic.generics import GenericModel
from pydantic import (
    BaseModel,
    root_validator,
    validator,
    StrictInt,
    StrictFloat,
    StrictStr,
    Field,
    UUID4,
)
from minio.datatypes import Object

from dmod.core import meta_data
from .errors import Error as ErrorEnum

from typing import Dict, Optional, Union, List, Generic, TypeVar
from typing_extensions import Self

T = TypeVar("T")


class Option(GenericModel, Generic[T]):
    # root_validator sets this field
    is_none: bool = True
    value: Optional[T]

    @root_validator()
    def _enforce_none_variant(
        cls, values: Dict[str, Union[bool, T]]
    ) -> Dict[str, Union[bool, T]]:
        if values["value"] is None:
            values["is_none"] = True
        else:
            values["is_none"] = False
        return values


class Error(BaseModel):
    type: str
    title: str
    status: int
    detail: str

    @classmethod
    def from_error_enum(
        cls, error_enum: ErrorEnum, detail: Optional[str] = None
    ) -> Self:
        return cls(
            title=error_enum.name,
            type=error_enum.type,
            status=error_enum.status,
            detail=detail if detail is not None else error_enum.detail,
        )


class StandardDatasetIndex(str, Enum):
    UNKNOWN = "UNKNOWN"
    TIME = "TIME"
    CATCHMENT_ID = "CATCHMENT_ID"
    DATA_ID = "DATA_ID"
    HYDROFABRIC_ID = "HYDROFABRIC_ID"
    LENGTH = "LENGTH"
    GLOBAL_CHECKSUM = "GLOBAL_CHECKSUM"
    ELEMENT_ID = "ELEMENT_ID"
    REALIZATION_CONFIG_DATA_ID = "REALIZATION_CONFIG_DATA_ID"

    def as_core_standard_dataset_index(self) -> meta_data.StandardDatasetIndex:
        return meta_data.StandardDatasetIndex.get_for_name(self.name)


class DataFormat(str, Enum):
    AORC_CSV = "AORC_CSV"
    NETCDF_FORCING_CANONICAL = "NETCDF_FORCING_CANONICAL"
    NETCDF_AORC_DEFAULT = "NETCDF_AORC_DEFAULT"
    NGEN_OUTPUT = "NGEN_OUTPUT"
    NGEN_REALIZATION_CONFIG = "NGEN_REALIZATION_CONFIG"
    NGEN_GEOJSON_HYDROFABRIC = "NGEN_GEOJSON_HYDROFABRIC"
    NGEN_PARTITION_CONFIG = "NGEN_PARTITION_CONFIG"
    BMI_CONFIG = "BMI_CONFIG"
    NWM_OUTPUT = "NWM_OUTPUT"
    NWM_CONFIG = "NWM_CONFIG"
    NGEN_CAL_OUTPUT = "NGEN_CAL_OUTPUT"
    NGEN_CAL_CONFIG = "NGEN_CAL_CONFIG"

    def as_core_data_format(self) -> meta_data.DataFormat:
        return meta_data.DataFormat.get_for_name(self.name)


class DataCategory(str, Enum):
    CONFIG = "CONFIG"
    FORCING = "FORCING"
    HYDROFABRIC = "HYDROFABRIC"
    OBSERVATION = "OBSERVATION"
    OUTPUT = "OUTPUT"

    def as_core_data_category(self) -> meta_data.DataCategory:
        return meta_data.DataCategory.get_for_name(self.name)


def _validate_is_not_unknown(value: StandardDatasetIndex):
    if value == StandardDatasetIndex.UNKNOWN:
        raise ValueError("unknown restriction variable not allowed")
    return value


class ContinuousRestriction(BaseModel):
    """
    A filtering component, typically applied as a restriction on a domain, by a continuous range of values of a variable.
    """

    variable: StandardDatasetIndex
    begin: datetime
    end: datetime

    _validate_variable_is_not_unknown = validator("variable", allow_reuse=True)(
        _validate_is_not_unknown
    )

    @root_validator()
    def _validate_start_before_end(cls, values):
        if values["begin"] > values["end"]:
            raise ValueError("end datetime is before begin datetime")
        return values

    def as_core_continuous_restriction(self) -> meta_data.ContinuousRestriction:
        return meta_data.ContinuousRestriction(
            variable=self.variable.as_core_standard_dataset_index(),
            begin=self.begin,
            end=self.end,
            datetime_pattern="%Y-%m-%d %H:%M:%S",
        )


class DiscreteRestriction(BaseModel):
    """
    A filtering component, typically applied as a restriction on a domain, by a discrete set of values of a variable.

    Note that an empty list for the ::attribute:`values` property implies a restriction of all possible values being
    required.  This is reflected by the :method:`is_all_possible_values` property.
    """

    variable: StandardDatasetIndex
    values: Union[List[StrictStr], List[StrictFloat], List[StrictInt]]

    _validate_variable_is_not_unknown = validator("variable", allow_reuse=True)(
        _validate_is_not_unknown
    )

    def as_core_discrete_restriction(self) -> meta_data.DiscreteRestriction:
        return meta_data.DiscreteRestriction(
            variable=self.variable.as_core_standard_dataset_index(), values=self.values
        )


class DataDomain(BaseModel):
    """
    A domain for a dataset, with domain-defining values contained by one or more discrete and/or continuous components.
    """

    data_format: DataFormat = Field(
        description="The format for the data in this domain, which contains details like the indices and other data fields."
    )
    continuous_restrictions: Optional[List[ContinuousRestriction]] = Field(
        description="Map of the continuous restrictions defining this domain, keyed by variable name.",
        alias="continuous",
        default_factory=list,
    )
    discrete_restrictions: Optional[List[DiscreteRestriction]] = Field(
        description="Map of the discrete restrictions defining this domain, keyed by variable name.",
        alias="discrete",
        default_factory=list,
    )

    @validator("continuous_restrictions", "discrete_restrictions", always=True)
    def _validate_restriction_default(cls, value):
        if value is None:
            return []
        return value

    @root_validator()
    def validate_sufficient_restrictions(cls, values):
        continuous_restrictions = values.get("continuous_restrictions", [])
        discrete_restrictions = values.get("discrete_restrictions", [])
        if len(continuous_restrictions) + len(discrete_restrictions) == 0:
            msg = "Cannot create {} without at least one finite continuous or discrete restriction"
            raise ValueError(msg.format(cls.__name__))
        return values

    def as_core_data_domain(self) -> meta_data.DataDomain:
        return meta_data.DataDomain(
            data_format=self.data_format.as_core_data_format(),
            continuous_restrictions=[
                c.as_core_continuous_restriction() for c in self.continuous_restrictions
            ],
            discrete_restrictions=[
                d.as_core_discrete_restriction() for d in self.discrete_restrictions
            ],
        )


class DatasetShortInfo(BaseModel):
    dataset_name: str
    data_id: UUID4


class DatasetObject(BaseModel):
    object_name: str
    object: UploadFile


class DatasetPutObjectMultipleRequest(BaseModel):
    dataset_name: str
    objects: List[DatasetObject]


class QueryType(str, Enum):
    LIST_FILES = "LIST_FILES"
    GET_CATEGORY = "GET_CATEGORY"
    GET_FORMAT = "GET_FORMAT"
    # TODO: uncomment when these have been implemented
    # GET_INDICES = "GET_INDICES"
    # GET_DATA_FIELDS = "GET_DATA_FIELDS"
    # GET_VALUES = "GET_VALUES"
    # GET_MIN_VALUE = "GET_MIN_VALUE"
    # GET_MAX_VALUE = "GET_MAX_VALUE"


class DatasetObjectMetadata(BaseModel):
    name: str
    size: int = Field(ge=0, description="Size in bytes")
    content_type: Optional[str]
    md5: str = Field(min_length=32, max_length=32)
    is_dir: bool

    @classmethod
    def from_minio_object(cls, o: Object) -> Self:
        content_type = o.metadata.get("content-type", None) if o.metadata else None
        return cls(
            name=o.object_name,
            size=o.size,
            content_type=content_type,
            md5=o.etag,
            is_dir=o.is_dir,
        )


class DatasetQueryResponse(BaseModel):
    files: Optional[List[DatasetObjectMetadata]] = None
    data_category: Optional[DataCategory] = None
    data_format: Optional[DataFormat] = None
