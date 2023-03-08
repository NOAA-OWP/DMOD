import sqlite3
from typing import Any, Dict, List, Optional, Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class TableInfo:
    """Table schema of sqlite PRAGMA table_info(<table_name>)"""

    cid: int
    name: str
    type: str
    notnull: bool
    dflt_value: Optional[Any]
    pk: bool


# walk the crosswalk to get the flow path id and query for the flow path attribute id's too


@contextmanager
def cursor_context(conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    """Yield a cursor instance with a lifetime of the context manager."""
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def attribute_table_names(conn: sqlite3.Connection) -> List[str]:
    """table names of geopackage 'attributes' type tables"""
    with cursor_context(conn) as cursor:
        result = cursor.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type = 'attributes'"
        )
        # index 0 is `table_name` column
        return [t[0] for t in result.fetchall()]


def table_info(table_name: str, conn: sqlite3.Connection) -> List[TableInfo]:
    """PRAGMA table_info(<table_name>) wrapper"""
    assert type(table_name) == str
    with cursor_context(conn) as cursor:
        result = cursor.execute(f"PRAGMA table_info({table_name})")
        results = result.fetchall()
    return [TableInfo(*result) for result in results]


def catchment_ids(conn: sqlite3.Connection) -> List[str]:
    """catchment id's in a given hydrofabric topology. guarantees uniqueness."""
    with cursor_context(conn) as cursor:
        query = cursor.execute("SELECT DISTINCT(id) as id FROM divides")
        return [record[0] for record in query.fetchall()]


def hydrofabric_linked_data(
    catchment_id: str, connection: sqlite3.Connection
) -> Dict[str, Dict[str, Any]]:
    """Return all associated _linked_ (not topological) hydrofabric data for a given catchment_id
    (e.g. `cat-1`) and a nested mapping of table name to table columns to table value(s).
    """
    attr_table_names = attribute_table_names(connection)

    attr_table_records_map: Dict[str, Dict[str, Any]] = {}
    for table_name in attr_table_names:
        table_field_info = table_info(table_name, connection)

        with cursor_context(connection) as cursor:
            records = cursor.execute(
                f"SELECT * FROM {table_name} WHERE id = ?", (catchment_id,)
            ).fetchall()

        if not records:
            continue

        if len(records) == 1:
            table_records = {
                table_field_info[idx].name: record
                for idx, record in enumerate(records[0])
            }
        else:
            table_records = {
                table_field_info[idx].name: record
                for idx, record in enumerate(zip(*records))
            }
        attr_table_records_map[table_name] = table_records

    return attr_table_records_map
