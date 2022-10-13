import asyncio
from typing import AnyStr
from dmod.client.request_clients import DatasetExternalClient


class DatasetFileWebsocketFilelike:

    def __init__(self, client: DatasetExternalClient, dataset_name: str, file_name: str):
        self._client = client
        self._dataset_name = dataset_name
        self._file_name = file_name
        self._read_index: int = 0

    def read(self, blksize: int) -> AnyStr:

        result = asyncio.get_event_loop().run_until_complete(
            self._client.download_item_block(dataset_name=self._dataset_name, item_name=self._file_name,
                                             blk_start=self._read_index, blk_size=blksize))
        self._read_index += blksize
        return result
