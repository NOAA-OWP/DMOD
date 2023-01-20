from abc import ABC
from django.views.generic.base import View
from dmod.client.request_clients import DatasetExternalClient
import logging
logger = logging.getLogger("gui_log")
from .DMODProxy import DMODMixin, GUI_STATIC_SSL_DIR
from typing import Dict, Optional
from pathlib import Path
from django.conf import settings
import minio

MINIO_HOST_STRING = settings.MINIO_HOST_STRING
MINIO_ACCESS = Path(settings.MINIO_ACCESS_FILE).read_text().strip()
MINIO_SECRET = Path(settings.MINIO_SECRET_FILE).read_text().strip()
MINIO_SECURE_CONNECT = settings.MINIO_SECURE_CONNECT


class AbstractDatasetView(View, DMODMixin, ABC):

    @classmethod
    def factory_minio_client(cls, endpoint: Optional[str] = None, access: Optional[str] = None,
                             secret: Optional[str] = None, is_secure: Optional[bool] = False) -> minio.Minio:
        client = minio.Minio(endpoint=MINIO_HOST_STRING if endpoint is None else endpoint,
                             access_key=MINIO_ACCESS if access is None else access,
                             secret_key=MINIO_SECRET if secret is None else secret,
                             secure=MINIO_SECURE_CONNECT if is_secure is None else is_secure)

        return client

    def __init__(self, *args, **kwargs):
        super(AbstractDatasetView, self).__init__(*args, **kwargs)
        self._dataset_client = None

    async def get_dataset(self, dataset_name: str) -> Dict[str, dict]:
        serial_dataset = await self.dataset_client.get_serialized_datasets(dataset_name=dataset_name)
        return serial_dataset

    async def get_datasets(self) -> Dict[str, dict]:
        serial_datasets = await self.dataset_client.get_serialized_datasets()
        return serial_datasets

    @property
    def dataset_client(self) -> DatasetExternalClient:
        if self._dataset_client is None:
            self._dataset_client = DatasetExternalClient(endpoint_uri=self.maas_endpoint_uri,
                                                         ssl_directory=GUI_STATIC_SSL_DIR)
        return self._dataset_client
