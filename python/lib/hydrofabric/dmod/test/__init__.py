import contextlib
import sqlite3
from pathlib import Path

from typing import Iterator


TESTING_DATA = Path(__file__).parent / "data/hydrofabric.gpkg"


@contextlib.contextmanager
def hydrofabric_fixture() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(TESTING_DATA)
    yield connection
    connection.close()
    return
