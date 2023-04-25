import io
import re
import datetime
import mimetypes
from minio import S3Error
from minio.datatypes import Bucket, Object
from minio.deleteobjects import DeleteObject, DeleteError
from minio.helpers import BaseURL
from pathlib import Path
from dataclasses import dataclass
from tempfile import TemporaryDirectory

from ..dataservice.utils import buffered_md5
from ..dataservice.reader import Reader

from typing import Any, Dict, Optional, List, Iterable


@dataclass
class HTTPResponseMock:
    data: Reader

    def __post_init__(self):
        self._open = True

    def read(self, amt=None, decode_content=None, cache_content=False):
        if self._open:
            return self.data.read(amt)
        return b""

    def close(self):
        self._open = False

    def release_conn(self):
        self.data = None


class MinioMock:
    """
    A mostly complete Minio's api that stores buckets and objects in a self managed temporary
    directory.
    """

    _BUCKET_NAME_RE = re.compile(
        "(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
    )

    def __init__(
        self,
        endpoint: str,
        access_key=None,
        secret_key=None,
        session_token=None,
        secure=True,
        region=None,
        http_client=None,
        credentials=None,
    ):
        self._base_url = BaseURL(
            ("https://" if secure else "http://") + endpoint,
            region,
        )
        self._temp_dir = TemporaryDirectory()

    def __del__(self):
        self._temp_dir.cleanup()

    @property
    def _temp_dir_path(self) -> Path:
        return Path(self._temp_dir.name)

    @staticmethod
    def _timestamp_as_utc_dt(t: float) -> datetime.datetime:
        creation_date = datetime.datetime.utcfromtimestamp(t)
        return creation_date.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def _build_s3_error(
        code: str,
        message: str,
        bucket_name: Optional[str] = None,
        object_name: Optional[str] = None,
    ) -> S3Error:
        return S3Error(
            code=code,
            message=message,
            resource="",
            request_id="",
            host_id="",
            response="",
            bucket_name=bucket_name,
            object_name=object_name,
        )

    def _object_exists(self, bucket_name: str, object_name: str) -> bool:
        o = self._temp_dir_path / bucket_name / object_name
        return o.exists() and not o.is_dir()

    def make_bucket(self, bucket_name: str, location=None, object_lock=False):
        if self._BUCKET_NAME_RE.fullmatch(bucket_name) is None:
            # TODO
            raise ValueError

        (self._temp_dir_path / bucket_name).mkdir()

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: Reader,
        length: int,
        content_type="application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
        sse=None,
        progress=None,
        part_size=0,
        num_parallel_uploads=3,
        tags=None,
        retention=None,
        legal_hold=False,
    ):
        if not self.bucket_exists(bucket_name):
            raise self._build_s3_error(
                "NoSuchBucket", "Bucket does not exist", bucket_name=bucket_name
            )

        with open(self._temp_dir_path / bucket_name / object_name, "wb") as fp:
            fp.write(data.read())

    def bucket_exists(self, bucket_name: str) -> bool:
        return (self._temp_dir_path / bucket_name).exists()

    def list_buckets(self) -> List[Bucket]:
        buckets: List[Bucket] = []
        for dir in filter(lambda p: p.is_dir(), self._temp_dir_path.glob("*")):
            dir_stat = dir.stat()
            creation_date = datetime.datetime.utcfromtimestamp(dir_stat.st_ctime)
            creation_date = creation_date.replace(tzinfo=datetime.timezone.utc)
            buckets.append(Bucket(name=dir.name, creation_date=creation_date))

        return buckets

    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        recursive: bool = False,
        start_after=None,
        include_user_meta=False,
        include_version=False,
        use_api_v1=False,
        use_url_encoding_type=True,
        fetch_owner=False,
    ):
        if prefix is not None:
            raise NotImplemented

        gen = (
            self._temp_dir_path.glob("**/*")
            if recursive
            else self._temp_dir_path.glob("*")
        )

        for file in gen:
            if file.is_dir():
                continue
            object_name = file.name
            file_stat = file.stat()
            last_modified = self._timestamp_as_utc_dt(file_stat.st_mtime)
            size = file_stat.st_size
            with open(file, "rb") as fp:
                etag = buffered_md5(fp)

            yield Object(
                bucket_name,
                object_name,
                last_modified=last_modified,
                etag=etag,
                size=size,
                metadata={},
                version_id=None,
                is_latest=None,
                storage_class="STANDARD",
                owner_id=None,
                owner_name="minio",
                content_type=None,
                is_delete_marker=False,
            )

    def remove_bucket(self, bucket_name: str):
        if not self.bucket_exists(bucket_name):
            raise self._build_s3_error(
                "NoSuchBucket", "Bucket does not exist", bucket_name=bucket_name
            )
        (self._temp_dir_path / bucket_name).rmdir()

    def get_object(
        self,
        bucket_name: str,
        object_name: str,
        offset: int = 0,
        length: int = 0,
        request_headers=None,
        ssec=None,
        version_id=None,
        extra_query_params=None,
    ) -> HTTPResponseMock:
        if not self.bucket_exists(bucket_name):
            raise self._build_s3_error(
                "NoSuchBucket", "Bucket does not exist", bucket_name=bucket_name
            )

        if not self._object_exists(bucket_name, object_name):
            raise self._build_s3_error(
                "NoSuchKey",
                "Object does not exist",
                bucket_name=bucket_name,
                object_name=object_name,
            )

        return HTTPResponseMock(
            io.BytesIO((self._temp_dir_path / bucket_name / object_name).read_bytes())
        )

    def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        ssec=None,
        version_id=None,
        extra_query_params=None,
    ) -> Object:
        if not self.bucket_exists(bucket_name):
            raise self._build_s3_error("NoSuchBucket", "Bucket does not exist")

        if not self._object_exists(bucket_name, object_name):
            raise self._build_s3_error("NoSuchKey", "Object does not exist")

        mt = mimetypes.MimeTypes()
        mime_type, _ = mt.guess_type(object_name)

        file = self._temp_dir_path / bucket_name / object_name
        if file.is_dir():
            # TODO
            raise ValueError

        file_stat = file.stat()
        last_modified = self._timestamp_as_utc_dt(file_stat.st_mtime)
        size = file_stat.st_size
        with open(file, "rb") as fp:
            etag = buffered_md5(fp)

        return Object(
            bucket_name,
            object_name,
            last_modified=last_modified,
            etag=etag,
            size=size,
            metadata={},
            version_id=None,
            is_latest=None,
            storage_class="STANDARD",
            owner_id=None,
            owner_name="minio",
            content_type=mime_type,
            is_delete_marker=False,
        )

    def remove_object(self, bucket_name: str, object_name: str, version_id=None):
        if not self.bucket_exists(bucket_name):
            raise self._build_s3_error("NoSuchBucket", "Bucket does not exist")

        if not self._object_exists(bucket_name, object_name):
            raise self._build_s3_error("NoSuchKey", "Object does not exist")

        o = self._temp_dir_path / bucket_name / object_name
        o.unlink()

    def remove_objects(
        self,
        bucket_name: str,
        delete_object_list: Iterable[DeleteObject],
        bypass_governance_mode: bool = False,
    ):
        errors: List[DeleteError] = []
        for object in delete_object_list:
            try:
                self.remove_object(bucket_name, object._name)

            except S3Error as e:
                errors.append(
                    DeleteError(
                        code=e.code,
                        message=e.message,
                        name=object._name,
                        version_id=None,
                    )
                )
        return errors
