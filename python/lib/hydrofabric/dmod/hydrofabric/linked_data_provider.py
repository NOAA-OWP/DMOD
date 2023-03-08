import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from .gpkg_utils import catchment_ids, hydrofabric_linked_data


class LinkedDataProvider(Protocol):
    def get_data(self, catchment_id: str) -> Dict[str, Dict[str, Any]]:
        ...

    def catchment_ids(self) -> List[str]:
        ...


@dataclass
class GPKGLinkedDataProvider:
    connection: sqlite3.Connection

    def get_data(self, catchment_id: str) -> Dict[str, Dict[str, Any]]:
        return hydrofabric_linked_data(catchment_id, self.connection)

    def catchment_ids(self) -> List[str]:
        return catchment_ids(self.connection)

    def __del__(self):
        self.connection.close()
