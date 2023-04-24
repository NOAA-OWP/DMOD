import re
from pydantic import BaseModel, Field, UUID4, validator
from datetime import datetime
from uuid import uuid4
from typing import Annotated, ClassVar, Optional, List, Union
from enum import Enum

from .models import DataCategory, DataDomain


class DatasetType(Enum):
    UNKNOWN = "UNKNOWN"
    OBJECT_STORE = "OBJECT_STORE"
    FILESYSTEM = "FILESYSTEM"


class Dataset(BaseModel):
    """
    Rrepresentation of the descriptive metadata for a grouped collection of data.
    """

    _SERIAL_DATETIME_STR_FORMAT: ClassVar = "%Y-%m-%d %H:%M:%S"
    _NAME_RE: ClassVar = re.compile(
        "(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
    )

    name: Annotated[
        str,
        Field(
            description=(
                "The name for this dataset, which also should be a unique identifier.\n"
                "Max size is 63 characters. See https://min.io/docs/minio/container/operations/checklists/thresholds.html#id1 for details"
            ),
            min_length=3,
            max_length=63,
        ),
    ]
    category: Annotated[
        DataCategory,
        Field(
            alias="data_category",
            description="The ::class:`DataCategory` type value for this instance.",
        ),
    ]
    data_domain: DataDomain
    dataset_type: Annotated[DatasetType, Field(alias="type")] = DatasetType.OBJECT_STORE
    access_location: Annotated[
        str,
        Field(
            description="String representation of the location at which this dataset is accessible."
        ),
    ]
    uuid: UUID4 = Field(default_factory=uuid4)
    manager_uuid: Optional[UUID4] = None
    is_read_only: Annotated[
        bool, Field(description="Whether this is a dataset that can only be read from.")
    ] = True
    description: Optional[str] = None
    expires: Annotated[
        Optional[datetime],
        Field(
            description='The time after which a dataset may "expire" and be removed, or ``None`` if the dataset is not temporary.',
        ),
    ] = None
    derived_from: Annotated[
        Optional[str],
        Field(
            description="The name of the dataset from which this dataset was derived, if it is known to have been derived.",
        ),
    ] = None
    derivations: Optional[List[str]] = Field(
        default_factory=list,
        description="""List of names of datasets which were derived from this dataset.\n
    Note that it is not guaranteed that any such dataset still exist and/or are still available.""",
    )
    created_on: Annotated[
        datetime,
        Field(
            description="When this dataset was created, or ``None`` if that is not known.",
            alias="create_on",
        ),
    ]
    last_updated: datetime

    @validator("name")
    def _validate_name(cls, value: str) -> str:
        """
        source: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html

        The following rules apply for naming buckets in Amazon S3:
            _ Bucket names must be between 3 (min) and 63 (max) characters long.
            _ Bucket names can consist only of lowercase letters, numbers, dots (.), and hyphens (-).
            _ Bucket names must begin and end with a letter or number.
            _ Bucket names must not contain two adjacent periods.
            _ Bucket names must not be formatted as an IP address (for example, 192.168.5.4).
            - Bucket names must not start with the prefix xn--.
            - Bucket names must not end with the suffix -s3alias. This suffix is reserved for access
            point alias names. For more information, see Using a bucket-style alias for your S3
            bucket access point.
            - Bucket names must not end with the suffix --ol-s3. This suffix is reserved for Object
            Lambda Access Point alias names. For more information, see How to use a bucket-style
            alias for your S3 bucket Object Lambda Access Point.
            - Bucket names must be unique across all AWS accounts in all the AWS Regions within a
            partition. A partition is a grouping of Regions. AWS currently has three partitions: aws
            (Standard Regions), aws-cn (China Regions), and aws-us-gov (AWS GovCloud (US)).
            - A bucket name cannot be used by another AWS account in the same partition until the
            bucket is deleted.
            - Buckets used with Amazon S3 Transfer Acceleration can't have dots (.) in their names.
            For more information about Transfer Acceleration, see Configuring fast, secure file
            transfers using Amazon S3 Transfer Acceleration.
        """
        if cls._NAME_RE.fullmatch(value) is None:
            raise ValueError(
                "Invalid name. See https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html for naming rules."
            )
        return value

    @validator("created_on", "last_updated", "expires", pre=True)
    def _coerce_datetime(cls, value: Union[None, datetime, str]) -> Optional[datetime]:
        if value is None:
            return value

        if isinstance(value, datetime):
            return value

        return datetime.strptime(value, cls._SERIAL_DATETIME_STR_FORMAT)

    @validator("created_on", "last_updated", "expires")
    def _drop_microseconds(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return value
        return value.replace(microsecond=0)

    class Config(BaseModel.Config):
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda d: d.strftime(Dataset._SERIAL_DATETIME_STR_FORMAT)
        }
