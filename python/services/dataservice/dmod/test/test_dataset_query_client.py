import json
import io
import unittest
import os
from minio import Minio, S3Error
from typing import Optional

from ..dataservice.dataset import Dataset
from ..dataservice.models import (
    StandardDatasetIndex,
    DataCategory,
    DataDomain,
    DataFormat,
    DiscreteRestriction,
)
from ..dataservice.dataset_query_client import DatasetQueryClient
from ..dataservice.dataset_client import DatasetClient
from ..dataservice.utils import buffered_md5

from .minio_mock import MinioMock


class TestDatasetQueryClient(unittest.TestCase):
    def setUp(self, minio_client: Optional[Minio] = None) -> None:
        if minio_client is None:
            self.minio_client = MinioMock(endpoint="127.0.0.1:9000")
        else:
            self.minio_client = minio_client

        self.client = DatasetQueryClient(self.minio_client)
        self.dataset = self.create_test_dataset("test-dataset")

    def tearDown(self) -> None:
        self.clean_up_test_dataset("test-dataset")

    def create_test_dataset(self, name: str) -> Dataset:
        ds_client = DatasetClient(self.minio_client)
        result = ds_client.create(
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
        ds_client = DatasetClient(self.minio_client)
        result = ds_client.delete(name)
        if result.is_ok():
            return

        # see s3 error codes: https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#ErrorCodeList
        if type(result.value) == S3Error and result.value.code in (
            "NoSuchBucket",
            "NoSuchKey",
        ):
            return

        raise result.value

    def test_cache(self):
        name = self.dataset.name
        assert len(self.client._ds_cache) == 0, "cache should be empty"
        result = self.client._load_dataset_from_cache(name)
        assert result.is_ok(), result.unwrap()
        assert (
            name in self.client._ds_cache
        ), f"dataset name: {name!r} should be in cache"
        assert self.dataset == result.value, "cached dataset should match"

        ds_client = DatasetClient(self.minio_client)
        # delete dataset
        result = ds_client.delete(name)
        assert (
            result.is_ok() and result.value
        ), f"dataset {name!r} was not successfully deleted"

        result = self.client._load_dataset_from_cache(name)
        assert result.is_err(), "dataset has been deleted, so it should not be present"
        assert (
            name not in self.client._ds_cache
        ), f"dataset name: {name!r} should not be in cache"
        assert type(result.value) == S3Error
        assert result.value.code == "NoSuchBucket"

    def test_dataset_exists_is_true(self):
        result = self.client.dataset_exists(self.dataset.name)
        assert result.is_ok()
        assert result.value is True

    def test_dataset_exists_is_false(self):
        result = self.client.dataset_exists("some-fake-dataset")
        assert result.is_ok()
        assert result.value is False

    def test_get_dataset(self):
        with self.client.get_dataset(self.dataset.name) as result:
            ds = result.unwrap()
            assert ds == self.dataset

    def test_get_dataset_id(self):
        result = self.client.get_dataset_id(self.dataset.name)
        assert result.unwrap() == self.dataset.uuid

    def test_get_dataset_object_info(self):
        result = self.client.get_dataset_object_info(
            self.dataset.name,
            self.client._gen_dataset_serial_obj_name(self.dataset.name),
        )
        info = result.unwrap()
        assert info.bucket_name == self.dataset.name
        assert info.content_type == "application/json"
        md5 = buffered_md5(
            io.BytesIO(self.dataset.json(by_alias=True, exclude_none=True).encode())
        )
        assert info.etag == md5

    def test_get_all_datasets(self):
        result = self.client.get_all_datasets()
        for ds in result.unwrap():
            if ds.unwrap() == self.dataset:
                return

        raise ValueError(f"dataset: {self.dataset} should be in list of all datasets.")

    def test_datasets(self):
        for ds in self.client.datasets.unwrap():
            if ds.unwrap().uuid == self.dataset.uuid:
                return

        raise ValueError(
            f"dataset uuid: {self.dataset} should be in list of all dataset's uuid's"
        )

    def test_get_dataset_object(self):
        # extra setup
        data = {"topic": "testing", "payload": "success"}
        raw_data = json.dumps(data).encode()
        reader = io.BytesIO(raw_data)
        object_name = "test.json"

        ds_client = DatasetClient(self.minio_client)
        result = ds_client.add_object(
            content_type="application/json",
            name=self.dataset.name,
            object_name=object_name,
            reader=reader,
            size=len(raw_data),
        )
        if result.is_err():
            raise result.value

        # actual testing
        with self.client.get_dataset_object(self.dataset.name, object_name) as result:
            result_data = json.loads(result.unwrap().read().decode())
        assert result_data == data
