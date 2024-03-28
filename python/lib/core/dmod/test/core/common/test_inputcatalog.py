"""
Tests for dmod.core.common.collections.InputCatalog and dmod.core.common.collections.CacheEntry
"""
from __future__ import annotations

import typing
import unittest

from uuid import uuid1
from dataclasses import dataclass
from dataclasses import field

from dmod.core.common import CatalogEntry
from dmod.core.common import CollectionEvent
from dmod.core.common import InputCatalog
from dmod.core.common.collections.catalog import hash_hashable_map_sequence

GLOBAL_ACCESS_RECORD = []
GLOBAL_REMOVAL_RECORD = []
GLOBAL_ADDITION_RECORD = []

GLOBAL_ASYNC_ACCESS_RECORD = []
GLOBAL_ASYNC_REMOVAL_RECORD = []
GLOBAL_ASYNC_ADDITION_RECORD = []

TEST_DATA_COUNT = 8


def generate_data() -> str:
    """
    A simple function used to generate random data to store

    Returns:
        A unique string
    """
    return str(uuid1())


@dataclass
class DataToAdd:
    """
    A simple object to add to a map
    """
    identifier: str
    data: typing.Optional[str] = field(default_factory=generate_data)


@dataclass
class ActionRecord:
    """
    A record that something happened
    """
    event: str
    id: str
    data: str

    def __hash__(self):
        return hash((self.event, self.id, self.data))

    def __eq__(self, other):
        return hash(self) == hash(other)


@dataclass
class AccessRecord:
    """
    A record that something was accessed
    """
    event: str
    id: str

    def __hash__(self):
        return hash((self.event, self.id))

    def __eq__(self, other):
        return hash(self) == hash(other)


SYNC_TEST_DATA = [
    DataToAdd(identifier=f"TEST-DATA-{index}")
    for index in range(TEST_DATA_COUNT)
]
"""
A collection of data that will be used within the unit tests for synchronous operations
"""

ASYNC_TEST_DATA = [
    DataToAdd(identifier=f"ASYNC-TEST-DATA-{index}")
    for index in range(TEST_DATA_COUNT)
]
"""
A collection of data that will be used within the unit tests for asynchronous operations
"""


def add_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_ADDITION_RECORD.append(ActionRecord(
        event=CollectionEvent.SET,
        id=key,
        data=value
    ))


async def async_add_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_ASYNC_ADDITION_RECORD.append(ActionRecord(
        event=CollectionEvent.SET,
        id=key,
        data=value
    ))


def remove_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_REMOVAL_RECORD.append(ActionRecord(
        event=CollectionEvent.DELETE,
        id=key,
        data=value
    ))


async def async_remove_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_ASYNC_REMOVAL_RECORD.append(ActionRecord(
        event=CollectionEvent.DELETE,
        id=key,
        data=value
    ))


def update_access_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_ACCESS_RECORD.append(AccessRecord(
        event=CollectionEvent.GET,
        id=key
    ))


def async_update_access_record(mapping: typing.MutableMapping[str, CatalogEntry], key, value):
    GLOBAL_ASYNC_ACCESS_RECORD.append(AccessRecord(
        event=CollectionEvent.GET,
        id=key
    ))


class TestInputCatalog(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.access_record = []
        self.removal_record = []
        self.addition_record = []

        self.async_access_record = []
        self.async_removal_record = []
        self.async_addition_record = []

        self.cache: InputCatalog[str] = InputCatalog()

        self.cache.add_handler(
            CollectionEvent.SET,
            self.add_record_method,
            self.async_add_record_method,
            add_record,
            async_add_record
        )

        self.cache.add_handler(
            CollectionEvent.DELETE,
            self.remove_record_method,
            self.async_remove_record_method,
            remove_record,
            async_remove_record
        )

        self.cache.add_handler(
            CollectionEvent.GET,
            self.update_access_record,
            self.async_update_access_record,
            update_access_record,
            async_update_access_record
        )

    def add_record_method(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.addition_record.append(ActionRecord(
            event=CollectionEvent.SET,
            id=key,
            data=value
        ))

    async def async_add_record_method(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.async_addition_record.append(ActionRecord(
            event=CollectionEvent.SET,
            id=key,
            data=value
        ))


    def remove_record_method(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.removal_record.append(ActionRecord(
            event=CollectionEvent.DELETE,
            id=key,
            data=value
        ))


    async def async_remove_record_method(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.async_removal_record.append(ActionRecord(
            event=CollectionEvent.DELETE,
            id=key,
            data=value
        ))

    def update_access_record(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.access_record.append(AccessRecord(
            event=CollectionEvent.GET,
            id=key
        ))

    def async_update_access_record(self, mapping: typing.MutableMapping[str, CatalogEntry], key, value):
        self.async_access_record.append(AccessRecord(
            event=CollectionEvent.GET,
            id=key
        ))

    def compare_records(self, records_added: int, records_removed: int):
        self.assertEqual(self.access_record, self.async_access_record)
        self.assertEqual(self.access_record, GLOBAL_ACCESS_RECORD)
        self.assertEqual(self.async_access_record, GLOBAL_ASYNC_ACCESS_RECORD)

        self.assertEqual(self.addition_record, self.async_addition_record)
        self.assertEqual(self.addition_record, GLOBAL_ADDITION_RECORD)
        self.assertEqual(self.addition_record, GLOBAL_ASYNC_ADDITION_RECORD)

        self.assertEqual(self.removal_record, self.async_removal_record)
        self.assertEqual(self.removal_record, GLOBAL_REMOVAL_RECORD)
        self.assertEqual(self.removal_record, GLOBAL_ASYNC_REMOVAL_RECORD)

        self.assertEqual(len(self.addition_record), records_added)
        self.assertEqual(len(self.removal_record), records_removed)
        #self.assertEqual(len(self.access_record), records_added * 4 + records_removed * 5)

    def test_hash_hashable_map_sequence(self):
        input_1 = [{'one': 48}, {'two': 2}, {'three': 3}]
        input_2 = {object(): 42, object(): 0}

        input_1_hash = hash_hashable_map_sequence(input_1)
        input_2_hash = hash_hashable_map_sequence(input_2)

        self.assertNotEqual(input_1_hash, input_2_hash)

    async def test_inputcatalog(self):
        records_added = 0
        records_removed = 0

        for test_data in SYNC_TEST_DATA:
            records_added += 1
            self.cache[test_data.identifier] = test_data.data
            await self.cache.commit()

            self.compare_records(records_added, records_removed)

        for test_data in ASYNC_TEST_DATA:
            records_added += 1
            await self.cache.async_set(test_data.identifier, test_data.data)

            self.compare_records(records_added, records_removed)

        for test_data in SYNC_TEST_DATA:
            data = self.cache[test_data.identifier]
            self.assertEqual(test_data.data, data)

        for test_data in ASYNC_TEST_DATA:
            data = self.cache[test_data.identifier]
            self.assertEqual(test_data.data, data)

        self.assertEqual(len(self.access_record), records_added)
        self.assertEqual(len(GLOBAL_ACCESS_RECORD), records_added)

        for test_data in SYNC_TEST_DATA:
            records_removed += 1
            del self.cache[test_data.identifier]

            await self.cache.commit()

            self.compare_records(records_added, records_removed)

        for test_data in ASYNC_TEST_DATA:
            records_removed += 1
            await self.cache.remove_async(test_data.identifier)

            self.compare_records(records_added, records_removed)

        self.assertEqual(len(self.access_record), records_added)
        self.assertEqual(len(GLOBAL_ACCESS_RECORD), records_added)

        for test_data in SYNC_TEST_DATA:
            data = self.cache.get(test_data.identifier)
            self.assertIsNone(data)

        for test_data in ASYNC_TEST_DATA:
            data = self.cache.get(test_data.identifier)
            self.assertIsNone(data)

        self.assertEqual(len(self.access_record), records_added)
        self.assertEqual(len(GLOBAL_ACCESS_RECORD), records_added)
