import io
from minio import Minio
from minio.deleteobjects import DeleteObject, DeleteError
from typing import cast, Union, Optional, Iterable, Iterator, List
from dataclasses import dataclass
from datetime import datetime
from exceptiongroup import ExceptionGroup
from urllib3.response import HTTPResponse
from contextlib import contextmanager

from .models import DataCategory, DataDomain
from .dataset import Dataset
from .result import Result, Ok, Err, as_result
from .reader import Reader


@dataclass
class ObjectToAdd:
    name: str
    reader: Reader
    size: int
    content_type: str = "application/json"


_MEGABYTE = 2**20


class DatasetClient:
    _SERIALIZED_OBJ_NAME_TEMPLATE = "{}_serialized.json"

    def __init__(self, client: Minio) -> None:
        self._client = client

    @classmethod
    def _gen_dataset_serial_obj_name(cls, name: str) -> str:
        return cls._SERIALIZED_OBJ_NAME_TEMPLATE.format(name)

    @as_result
    def _bucket_exists(self, name: str) -> bool:
        return self._client.bucket_exists(name)

    def _update_dataset(self, name: str) -> Result[None, Exception]:
        with self._get_dataset(name) as res:
            if res.is_err():
                return res

        ds: Dataset = res.value
        ds.last_updated = datetime.now()
        serial = ds.json(by_alias=True, exclude_none=True).encode()

        return self.add_object(
            name=name,
            object_name=self._gen_dataset_serial_obj_name(name),
            content_type="application/json",
            size=len(serial),
            reader=io.BytesIO(serial),
        )

    def _access_location(self, name: str) -> str:
        return "{}://{}/{}".format(
            "https" if self._client._base_url.is_https else "http",
            self._client._base_url.host,
            name,
        )

    @contextmanager
    def _get_dataset(self, name: str) -> Iterator[Result[Dataset, Exception]]:
        response_bound = False
        try:
            response: HTTPResponse = self._client.get_object(
                name, self._gen_dataset_serial_obj_name(name)
            )
            response_bound = True
            yield Ok(Dataset.parse_raw(response.read()))
        except Exception as e:
            yield Err(e)
        finally:
            if response_bound:
                response.close()
                response.release_conn()

    def create(
        self,
        name: str,
        category: DataCategory,
        domain: DataDomain,
        objects: Optional[Iterable[ObjectToAdd]] = None,
        read_only: bool = False,
    ) -> Result[Dataset, Union[Exception, ExceptionGroup[Exception]]]:
        """
        Create a new dataset. Fails if dataset already exists.

        Dataset names are restricted to the following rules:

            - Must be between 3 (min) and 63 (max) characters long.
            - Can consist only of lowercase letters, numbers, dots (.), and hyphens (-).
            - Must begin and end with a letter or number.
            - Must not contain two adjacent periods.
            - Must not be formatted as an IP address (for example, 192.168.5.4).
            - Must not start with the prefix xn--.
            - Must not end with the suffix -s3alias. This suffix is reserved for access point alias
                names. For more information, see Using a bucket-style alias for your S3 bucket
                access point.
            - Must not end with the suffix --ol-s3. This suffix is reserved for Object Lambda Access
                Point alias names. For more information, see How to use a bucket-style alias for
                your S3 bucket Object Lambda Access Point.

            see s3 bucket naming rules for more information: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html

        Example:
        ```python
        from dmod.core.meta_data import (
            DataCategory,
            DataDomain,
            DataFormat,
            DiscreteRestriction,
            StandardDatasetIndex,
        )
        from dmod.dataservice.dataset_client import DatasetClient
        from minio import Minio

        minio_client = Minio("127.0.0.1:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
        client = DatasetClient(minio_client)

        result = client.create(
            "example-dataset",
            category=DataCategory.CONFIG,
            domain=DataDomain(
                data_format=DataFormat.BMI_CONFIG,
                discrete=[
                    DiscreteRestriction(
                        variable=StandardDatasetIndex.GLOBAL_CHECKSUM, values=["42"]
                    )
                ],
            ),
        )
        if result.is_err():
            # handle error
            raise result.value

        dataset = result.value
        ```
        """

        # NOTE: if minio-py changes their internal api this could fail in the future.
        # if that happens, we want this to raise.
        access_location = self._access_location(name)

        try:
            created_on = datetime.now()
            # NOTE: could fail here
            dataset = Dataset(
                name=name,
                category=category,
                data_domain=domain,
                access_location=access_location,
                is_read_only=read_only,
                created_on=created_on,
                last_updated=created_on,
            )

            serialized = dataset.json(by_alias=True, exclude_none=True).encode()
        except Exception as e:
            return Err(e)

        try:
            self._client.make_bucket(name)
        except Exception as e:
            return Err(e)

        try:
            result = self.add_object(
                name=name,
                object_name=self._gen_dataset_serial_obj_name(name),
                content_type="application/json",
                reader=io.BytesIO(serialized),
                size=len(serialized),
            )

            if result.is_err():
                return result

            if objects is not None:
                self.add_objects(name, *objects).unwrap()

            return Ok(dataset)

        except Exception as e:
            result = self.delete(name)
            # if deletion fails, attach prior error context
            if result.is_err():
                result.value.__context__ = e
                return result
            return Err(e)

    @as_result
    def add_object(
        self,
        name: str,
        object_name: str,
        reader: Reader,
        size: int,
        content_type: str = "application/octet-stream",
        extract: bool = False,
    ) -> None:
        """
        Add object to existing dataset. Existing objects will be overwritten.

        The object to upload is provided to the `reader` parameter and must provide a `read()`
        method. Specifically: `read(self, size: Union[int, None] = ...) -> bytes`.

        tar and tar.gz archives will be extracted by the data store post upload if `extract` flag is
        set and content-type is `application/x-gzip` or `application/x-tar`. This is useful when
        uploading large files.

        Example:
        ```python
        import io
        from dmod.dataservice.dataset_client import DatasetClient
        from minio import Minio

        minio_client = Minio("127.0.0.1:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
        client = DatasetClient(minio_client)

        result = client.add_object(
            name="example-dataset",
            object_name="test_data.txt",
            reader=io.BytesIO(b"just some test data"),
            content_type="text/plain",
            size=len(b"just some test data"),
        )
        if result.is_err():
            raise result.value
        ```
        """
        # source: https://docs.aws.amazon.com/snowball/latest/developer-guide/batching-small-files.html
        # > The auto-extract feature supports the TAR, and tar.gz formats.
        content_type = (
            content_type.lower() if content_type else "application/octet-stream"
        )

        if (
            extract
            and content_type == "application/x-gzip"
            or content_type == "application/x-tar"
        ):
            headers = {"X-Amz-Meta-Snowball-Auto-Extract": "true"}
        else:
            headers = {}

        result = self._bucket_exists(name)
        if result.is_err():
            return result

        if size > 5 * _MEGABYTE:
            # TODO: determine appropriate partition size
            partition_size = 5 * _MEGABYTE
            self._client.put_object(
                bucket_name=name,
                object_name=object_name,
                data=reader,
                length=size,
                content_type=content_type,
                part_size=partition_size,
                metadata=headers,
            )
            return

        self._client.put_object(
            bucket_name=name,
            object_name=object_name,
            data=reader,
            length=size,
            content_type=content_type,
            metadata=headers,
        )

    def add_objects(
        self, name: str, *objects: ObjectToAdd
    ) -> Result[None, ExceptionGroup[Exception]]:
        """
        Add multiple objects to an existing dataset. All objects will attempt to be uploaded, meaning
        it is possible for the first object to fail and the last to succeed.

        Example:
        ```python
        import io
        from dmod.dataservice.dataset_client import DatasetClient
        from minio import Minio

        minio_client = Minio("127.0.0.1:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
        client = DatasetClient(minio_client)

        objects = [
            ObjectToAdd(
                "test_data.txt",
                content_type="text/plain",
                reader=io.BytesIO(b"just some test data"),
                size=len(b"just some test data"),
            ),
            ObjectToAdd(
                "more_test_data.txt",
                content_type="text/plain",
                reader=io.BytesIO(b"just some more test data"),
                size=len(b"just some more test data"),
            ),
        ]
        result = self.client.add_objects("example-dataset", *data)

        if result.is_err():
            raise result.value
        ```
        """
        errors: List[Exception] = []
        for obj in objects:
            result = self.add_object(
                name=name,
                object_name=obj.name,
                reader=obj.reader,
                size=obj.size,
                content_type=obj.content_type,
            )
            if result.is_err():
                # noop: cast to make linter happy
                result = cast(Err[Exception], result)
                errors.append(result.value)

        if not errors:
            return Ok(None)

        if len(errors) == len(objects):
            return Err(ExceptionGroup("all objects failed to upload", errors))
        return Err(ExceptionGroup("some objects failed to upload", errors))

    def delete(
        self, name: str
    ) -> Result[bool, Union[Exception, ExceptionGroup[RuntimeError]]]:
        """Delete an existing dataset."""
        result = self._bucket_exists(name)
        if result.is_err():
            return result

        if result.value is False:
            return Ok(False)

        object_listing = self._client.list_objects(bucket_name=name, recursive=True)
        delete_object_list: List[str] = [x.object_name for x in object_listing]
        result = self.delete_objects(name, *delete_object_list)

        if result.is_err():
            return result

        try:
            self._client.remove_bucket(name)
        # catch, mainly, network errors
        except Exception as e:
            return Err(e)

        return Ok(True)

    @as_result
    def delete_object(self, name: str, object_name: str) -> None:
        """Delete an object from an existing dataset."""
        result = self._bucket_exists(name)
        if result.is_err():
            return result

        self._client.remove_object(bucket_name=name, object_name=object_name)

    def delete_objects(
        self, name: str, *object_names: str
    ) -> Result[None, Union[Exception, ExceptionGroup[RuntimeError]]]:
        """Delete one or more object from an existing dataset."""
        if not object_names:
            return Ok(None)

        result = self._bucket_exists(name)
        if result.is_err():
            return result
        if not result.value:
            return Ok(None)

        delete_object_list = list(map(lambda x: DeleteObject(x), object_names))
        try:
            errors: Iterable[DeleteError] = self._client.remove_objects(
                bucket_name=name, delete_object_list=delete_object_list
            )
            errors = list(errors)
        # catch, mainly, network errors
        except Exception as e:
            return Err(e)

        if errors:
            errs = [
                RuntimeError(
                    {
                        "name": name,
                        "object_name": e.name,
                        "status_code": e.code,
                        "message": e.message,
                    }
                )
                for e in errors
            ]

            if len(errs) == len(object_names):
                return Err(ExceptionGroup("error deleting all objects", errs))
            return Err(ExceptionGroup("error deleting all objects", errs))

        return Ok(None)
