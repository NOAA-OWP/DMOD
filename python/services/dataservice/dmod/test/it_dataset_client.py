import os
from minio import Minio
from typing import Optional

from .test_dataset_client import TestDatasetClient


def setup_minio_client() -> Minio:
    default_key = "minioadmin"
    host = os.environ.get("MINIO_HOST", "127.0.0.1")
    port = os.environ.get("MINIO_PORT", "9000")
    key = os.environ.get("MINIO_KEY", default_key)
    secret = os.environ.get("MINIO_SECRET", default_key)
    secure = bool(os.environ.get("MINIO_SECURE", False))

    return Minio(f"{host}:{port}", access_key=key, secret_key=secret, secure=secure)


class IntegrationTestDatasetQueryClient(TestDatasetClient):
    def setUp(self, minio_client: Optional[Minio] = None) -> None:
        minio_client = setup_minio_client()
        super().setUp(minio_client)
