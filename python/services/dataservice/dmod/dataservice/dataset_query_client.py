import io
from urllib3.response import HTTPResponse
from minio import Minio, S3Error
from minio.datatypes import Object as MinioObject, Bucket
from typing import cast, Dict, Iterable, Iterator, Optional
from pydantic import BaseModel, UUID4
from dataclasses import dataclass
from contextlib import contextmanager

from .dataset import Dataset
from .result import Result, Ok, Err, as_result
from .utils import buffered_md5


class DatasetID(BaseModel):
    name: str
    uuid: UUID4


@dataclass
class DatasetCacheItem:
    dataset: Dataset
    hash: str


class DatasetQueryClient:
    _SERIALIZED_OBJ_NAME_TEMPLATE = "{}_serialized.json"

    def __init__(self, client: Minio) -> None:
        self._client = client
        self._ds_cache: Dict[str, DatasetCacheItem] = dict()

    def _gen_dataset_serial_obj_name(self, name: str) -> str:
        return self._SERIALIZED_OBJ_NAME_TEMPLATE.format(name)

    @as_result
    def _load_dataset_from_cache(self, name: str) -> Dataset:
        # load dataset from cache
        ds = self._ds_cache.get(name, None)

        metadata_file_name = self._gen_dataset_serial_obj_name(name)

        # cache miss
        if ds is None:
            with self.get_dataset_object(name, metadata_file_name) as result:
                # fail fast, may want return and backoff here in the future
                if result.is_err():
                    return result

                raw_body = result.value.read()
            deserialized = Dataset.parse_raw(raw_body)
            ds = DatasetCacheItem(deserialized, buffered_md5(io.BytesIO(raw_body)))

        # get object metadata from object store. this includes md5 hash (etag)
        result = self.get_dataset_object_info(name, metadata_file_name)
        # failed to get metadata from object store
        if result.is_err():
            # if the bucket or object does not exist, purge from cache
            # see s3 error codes: https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#ErrorCodeList
            if type(result.value) == S3Error and result.value.code in (
                "NoSuchBucket",
                "NoSuchKey",
            ):
                self._ds_cache.pop(name, None)

            return result

        remote_ds_hash: str = result.value.etag

        # invalidate cache and retry
        if ds.hash != remote_ds_hash:
            self._ds_cache.pop(name, None)
            return self._load_dataset_from_cache(name)

        # cache dataset
        self._ds_cache[name] = ds

        return ds.dataset

    def dataset_exists(self, name: str) -> Result[bool, Exception]:
        with self.get_dataset(name) as result:
            if result.is_ok():
                return Ok(True)

            # failed to get dataset; check if bucket or object does not exist
            # see s3 error codes: https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#ErrorCodeList
            if type(result.value) == S3Error and result.value.code in (
                "NoSuchBucket",
                "NoSuchKey",
            ):
                return Ok(False)

            return result

    @contextmanager
    def _get_raw_dataset(self, name: str) -> Iterator[Result[bytes, Exception]]:
        """"""
        try:
            response: HTTPResponse = self._client.get_object(
                name, self._gen_dataset_serial_obj_name(name)
            )
            yield Ok(response.read())
        except Exception as e:
            yield Err(e)
        finally:
            response.close()
            response.release_conn()

    @contextmanager
    def get_dataset(self, name: str) -> Iterator[Result[Dataset, Exception]]:
        # try load from cache
        result = self._load_dataset_from_cache(name)
        if result.is_ok():
            yield result
            return

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

    def get_dataset_id(self, name: str) -> Result[UUID4, Exception]:
        with self.get_dataset(name) as result:
            if result.is_err():
                return result
            return Ok(result.value.uuid)

    @contextmanager
    def get_dataset_object(
        self, name: str, object_name: str
    ) -> Iterator[Result[HTTPResponse, Exception]]:
        response_bound = False
        try:
            response: HTTPResponse = self._client.get_object(
                bucket_name=name, object_name=object_name
            )
            response_bound = True
            yield Ok(response)
        except Exception as e:
            yield Err(e)
        finally:
            if response_bound:
                response.close()
                response.release_conn()

    @as_result
    def get_dataset_object_info(self, name: str, object_name: str) -> MinioObject:
        return self._client.stat_object(bucket_name=name, object_name=object_name)

    def get_all_datasets(
        self,
    ) -> Result[Iterator[Result[Dataset, Exception]], Exception]:
        try:
            buckets: Iterable[Bucket] = self._client.list_buckets()
        except Exception as e:
            return Err(e)

        def iterator():
            for b in buckets:
                with self.get_dataset(b.name) as result:
                    yield result

        return Ok(iterator())

    @as_result
    def list_dataset_objects(
        self, name: str, prefix: Optional[str] = None, recursive: bool = False
    ) -> Iterator[MinioObject]:
        yield from self._client.list_objects(name, prefix=prefix, recursive=recursive)

    @property
    def datasets(self) -> Result[Iterator[Result[DatasetID, Exception]], Exception]:
        result = self.get_all_datasets()
        if result.is_err():
            result = cast(Err[Exception], result)
            return result

        result = cast(Ok[Iterator[Result[Dataset, Exception]]], result)

        def iterator() -> Iterator[Result[DatasetID, Exception]]:
            for ds in result.value:
                if ds.is_ok():
                    ds = cast(Ok[Dataset], ds)
                    yield Ok(DatasetID(name=ds.value.name, uuid=ds.value.uuid))
                else:
                    ds = cast(Err[Exception], ds)
                    yield ds

        return Ok(iterator())
