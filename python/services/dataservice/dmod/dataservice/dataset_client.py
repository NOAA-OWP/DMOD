import io
from minio import Minio
from minio.deleteobjects import DeleteObject, DeleteError
from typing import cast, Union, Iterable, Iterator, List
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
    size: Union[int, None] = None
    content_type: str = "application/json"


_MEGABYTE = 2**20


class DatasetClient:
    _SERIALIZED_OBJ_NAME_TEMPLATE = "{}_serialized.json"

    def __init__(self, client: Minio) -> None:
        self._client = client

    @as_result
    def _bucket_exists(self, name: str) -> bool:
        return self._client.bucket_exists(name)

    def _update_dataset(self, name: str) -> Result[None, Exception]:
        with self.get_dataset(name) as res:
            if res.is_err():
                return res

        ds: Dataset = res.value
        ds.last_updated = datetime.now()
        serial = ds.json(by_alias=True, exclude_none=True).encode()

        return self.add_object(
            name=name,
            object_name=self._SERIALIZED_OBJ_NAME_TEMPLATE.format(name),
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
        *objects: ObjectToAdd,
        read_only: bool = False,
    ) -> Result[Dataset, Union[Exception, ExceptionGroup[Exception]]]:
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
                object_name=self._SERIALIZED_OBJ_NAME_TEMPLATE.format(name),
                content_type="application/json",
                reader=io.BytesIO(serialized),
                size=len(serialized),
            )

            if result.is_err():
                return result

            if objects:
                self.add_objects(name=name, *objects)

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
        size: Union[int, None] = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        result = self._bucket_exists(name)
        if result.is_err():
            return result

        if size is None or size < 1:
            size = -1
        elif size > 5 * _MEGABYTE:
            # TODO: determine appropriate partition size
            partion_size = 5
            self._client.put_object(
                bucket_name=name,
                object_name=object_name,
                data=reader,
                length=size,
                content_type=content_type,
                part_size=partion_size,
            )
            return

        self._client.put_object(
            bucket_name=name,
            object_name=object_name,
            data=reader,
            length=size,
            content_type=content_type,
        )

    def add_objects(
        self, name: str, *objects: ObjectToAdd
    ) -> Result[None, ExceptionGroup[Exception]]:
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
        result = self._bucket_exists(name)
        if result.is_err():
            return result

        self._client.remove_object(bucket_name=name, object_name=object_name)

    def delete_objects(
        self, name: str, *object_names: str
    ) -> Result[None, Union[Exception, ExceptionGroup[RuntimeError]]]:
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
