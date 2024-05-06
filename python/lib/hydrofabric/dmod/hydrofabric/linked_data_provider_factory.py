import sqlite3
from pathlib import Path

from .linked_data_provider import LinkedDataProvider, GPKGLinkedDataProvider


class LinkedDataProviderFactory:
    @staticmethod
    def factory_create(p: Path) -> LinkedDataProvider:
        if not p.exists() or not p.is_file():
            raise RuntimeError

        if p.suffix.lower() == ".gpkg" or p.suffix.lower() == ".db":
            # open connection in read only mode
            uri = f"{p.as_uri()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True)
            return GPKGLinkedDataProvider(connection=connection)
        raise NotImplementedError
