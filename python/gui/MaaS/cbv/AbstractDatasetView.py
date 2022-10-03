from abc import ABC
from django.views.generic.base import View
from dmod.client.request_clients import DatasetExternalClient
import logging
logger = logging.getLogger("gui_log")
from .DMODProxy import DMODMixin, GUI_STATIC_SSL_DIR
from typing import Dict


class AbstractDatasetView(View, DMODMixin, ABC):

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
