import unittest
import io
import time
from minio import Minio, S3Error
from typing import Optional

from ..dataservice.dataset_client import DatasetClient, ObjectToAdd
from ..dataservice.dataset import Dataset
from ..dataservice.models import (
    StandardDatasetIndex,
    DataCategory,
    DataDomain,
    DataFormat,
    DiscreteRestriction,
)
from .minio_mock import MinioMock


class TestDatasetClient(unittest.TestCase):
    def setUp(self, minio_client: Optional[Minio] = None) -> None:
        if minio_client is None:
            self.minio_client = MinioMock(endpoint="127.0.0.1:9000")
        else:
            self.minio_client = minio_client

        self.client = DatasetClient(self.minio_client)
        self.dataset = self.create_test_dataset("test-dataset")

    def tearDown(self) -> None:
        self.clean_up_test_dataset("test-dataset")

    def create_test_dataset(self, name: str) -> Dataset:
        result = self.client.create(
            name,
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
            raise Exception from result.value

        return result.value

    def clean_up_test_dataset(self, name: str):
        result = self.client.delete(name)
        if result.is_ok():
            return

        # see s3 error codes: https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#ErrorCodeList
        if type(result.value) == S3Error and result.value.code in (
            "NoSuchBucket",
            "NoSuchKey",
        ):
            return

        raise result.value

    def test__bucket_exists(self):
        name = self.dataset.name
        result = self.client._bucket_exists(name)
        assert result.unwrap() == True

        result = self.client.delete(name)
        assert result.unwrap() == True

        result = self.client._bucket_exists(name)
        assert result.unwrap() == False

    def test_update_dataset(self):
        # updating a dataset entails updating its `last_updated` property. the `last_updated` property
        # stored with second precision, ergo, it's required to wait a moment to verify this case.
        time.sleep(1.1)
        result = self.client._update_dataset(self.dataset.name)
        # throw if `is_err`
        result.unwrap()
        with self.client._get_dataset(self.dataset.name) as result:
            updated_dataset = result.unwrap()
        assert updated_dataset.last_updated > self.dataset.last_updated

    def test_add_object(self):
        name = self.dataset.name
        result = self.client.add_object(
            name=name,
            object_name="test_data.txt",
            reader=io.BytesIO(b"just some test data"),
            content_type="text/plain",
            size=len(b"just some test data"),
        )
        result.unwrap()

    def test_add_objects(self):
        name = self.dataset.name
        data = [
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
        result = self.client.add_objects(name, *data)
        result.unwrap()

        for item in data:
            result = self.client.delete_object(name=name, object_name=item.name)
            assert result.is_ok()

    def test_delete(self):
        result = self.client.delete(self.dataset.name)
        result.unwrap()

        ds_exists = self.client._bucket_exists(self.dataset.name).unwrap()
        assert ds_exists is False

    def test_delete_objects(self):
        # setup
        name = self.dataset.name
        data = [
            ObjectToAdd(
                "test_data.txt",
                content_type="text/plain",
                reader=io.BytesIO(b"just some test data"),
                size=len(b"just some test data"),
            ),
            ObjectToAdd(
                "folder/more_test_data.txt",
                content_type="text/plain",
                reader=io.BytesIO(b"just some more test data"),
                size=len(b"just some more test data"),
            ),
        ]
        result = self.client.add_objects(name, *data)
        result.unwrap()

        # thing we are actually testing
        result = self.client.delete_objects(
            name, "test_data.txt", "folder/more_test_data.txt"
        )
        assert result.is_ok()
