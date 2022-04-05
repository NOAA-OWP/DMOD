from .request_clients import DatasetExternalClient
from .client_config import YamlClientConfig
from dmod.core.meta_data import DataCategory
from pathlib import Path
from typing import List, Optional


class DmodClient:

    def __init__(self, client_config: YamlClientConfig, *args, **kwargs):
        self._client_config = client_config
        self._dataset_handler = None

    @property
    def client_config(self):
        return self._client_config

    async def create_dataset(self, dataset_name: str, category: DataCategory) -> bool:
        """
        Create a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        category : DataCategory
            The dataset category

        Returns
        -------
        bool
            Whether creation was successful
        """
        return await self.dataset_handler.create_dataset(dataset_name, category)

    async def list_datasets(self, category: Optional[DataCategory] = None):
        return await self.dataset_handler.list_datasets(category)

    @property
    def dataset_handler(self) -> DatasetExternalClient:
        if self._dataset_handler is None:
            self._dataset_handler = DatasetExternalClient(self.requests_endpoint_uri, self.requests_ssl_dir)
        return self._dataset_handler

    @property
    def requests_endpoint_uri(self) -> str:
        return self.client_config.requests_endpoint_uri

    @property
    def requests_ssl_dir(self) -> Path:
        return self.client_config.requests_ssl_dir

    def print_config(self):
        print(self.client_config.config_file.read_text())

    async def upload_to_dataset(self, dataset_name: str, paths: List[Path]) -> bool:
        """
        Upload data a dataset.

        Parameters
        ----------
        dataset_name : str
            The name of the dataset.
        paths : List[Path]
            List of one or more paths of files to upload or directories containing files to upload.

        Returns
        -------
        bool
            Whether uploading was successful
        """
        return await self.dataset_handler.upload_to_dataset(dataset_name, paths)

    def validate_config(self):
        # TODO:
        raise NotImplementedError("Function validate_config not yet implemented")
