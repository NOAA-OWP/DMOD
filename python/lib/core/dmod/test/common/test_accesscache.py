"""
Tests for dmod.core.common.collections.AccessCache and dmod.core.common.collections.CacheEntry
"""
from __future__ import annotations

import typing
import unittest

from uuid import uuid1
from dataclasses import dataclass
from dataclasses import field

from datetime import datetime

from ...core.common.collection import CacheEntry
from ...core.common.collection import AccessCache
from ...core.events import Event

KT = typing.TypeVar("KT")
VT = typing.TypeVar("VT")

COLLECTION_KEY = "collection"
COLLECTION_TYPE = list
COLLECTION_ADD_KEY = "append"

GLOBAL_ACCESS_RECORD = COLLECTION_TYPE()
GLOBAL_REMOVAL_RECORD = COLLECTION_TYPE()
GLOBAL_ADDITION_RECORD = COLLECTION_TYPE()

GLOBAL_ASYNC_ACCESS_RECORD = COLLECTION_TYPE()
GLOBAL_ASYNC_REMOVAL_RECORD = COLLECTION_TYPE()
GLOBAL_ASYNC_ADDITION_RECORD = COLLECTION_TYPE()

TEST_DATA_COUNT = 8


def generate_data() -> str:
    return str(uuid1())


@dataclass
class DataToAdd:
    identifier: str
    data: typing.Optional[str] = field(default_factory=generate_data)

@dataclass
class ActionRecord:
    event: str
    id: str
    data: str
    last_accessed: datetime

    def __hash__(self):
        return hash((self.event, self.id, self.data))

    def __eq__(self, other):
        return hash(self) == hash(other)

@dataclass
class AccessRecord:
    event: str
    id: str
    last_accessed: datetime

    def __hash__(self):
        return hash((self.event, self.id))

    def __eq__(self, other):
        return hash(self) == hash(other)


SYNC_TEST_DATA = [
    DataToAdd(identifier=f"TEST-DATA-{index}")
    for index in range(TEST_DATA_COUNT)
]

ASYNC_TEST_DATA = [
    DataToAdd(identifier=f"ASYNC-TEST-DATA-{index}")
    for index in range(TEST_DATA_COUNT)
]


def add_record(event: Event, entry: CacheEntry[VT], *args, **kwargs):
    getattr(GLOBAL_ADDITION_RECORD, COLLECTION_ADD_KEY)(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=entry.data,
        last_accessed=entry.last_accessed
    ))


async def async_add_record(event: Event, entry: CacheEntry[VT], *args, **kwargs):
    getattr(GLOBAL_ASYNC_ADDITION_RECORD, COLLECTION_ADD_KEY)(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=await entry.async_data,
        last_accessed=entry.last_accessed
    ))


def remove_record(event: Event, entry: CacheEntry[VT],  *args, **kwargs):
    getattr(GLOBAL_REMOVAL_RECORD, COLLECTION_ADD_KEY)(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=entry.data,
        last_accessed=entry.last_accessed
    ))


async def async_remove_record(event: Event, entry: CacheEntry[VT], *args, **kwargs):
    getattr(GLOBAL_ASYNC_REMOVAL_RECORD, COLLECTION_ADD_KEY)(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=await entry.async_data,
        last_accessed=entry.last_accessed
    ))


def update_access_record(event: Event, entry: CacheEntry[VT], *args, **kwargs):
    getattr(GLOBAL_ACCESS_RECORD, COLLECTION_ADD_KEY)(AccessRecord(
        event=event.event_name,
        id=entry.identifier,
        last_accessed=entry.last_accessed
    ))


def async_update_access_record(event: Event, entry: CacheEntry[VT], *args, **kwargs):
    getattr(GLOBAL_ASYNC_ACCESS_RECORD, COLLECTION_ADD_KEY)(AccessRecord(
        event=event.event_name,
        id=entry.identifier,
        last_accessed=entry.last_accessed
    ))


class TestAccessCache(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.access_record = COLLECTION_TYPE()
        self.removal_record = COLLECTION_TYPE()
        self.addition_record = COLLECTION_TYPE()

        self.async_access_record = COLLECTION_TYPE()
        self.async_removal_record = COLLECTION_TYPE()
        self.async_addition_record = COLLECTION_TYPE()

        self.cache: AccessCache[str] = AccessCache(
            on_addition=[
                self.add_record_method,
                self.async_add_record_method,
                add_record,
                async_add_record
            ],
            on_removal=[
                self.remove_record_method,
                self.async_remove_record_method,
                remove_record,
                async_remove_record
            ],
            on_access=[
                self.update_access_record,
                self.async_update_access_record,
                update_access_record,
                async_update_access_record
            ]
        )

    def add_record_method(
        self,
        event: Event,
        entry: CacheEntry[VT],
        *args,
        **kwargs
    ):
        getattr(self.addition_record, COLLECTION_ADD_KEY)(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=entry.data,
            last_accessed=entry.last_accessed
        ))


    async def async_add_record_method(self, event: Event, entry: CacheEntry[VT], *args, **kwargs):
        getattr(self.async_addition_record, COLLECTION_ADD_KEY)(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=await entry.async_data,
            last_accessed=entry.last_accessed
        ))


    def remove_record_method(self, event: Event, entry: CacheEntry[VT], *args, **kwargs):
        getattr(self.removal_record, COLLECTION_ADD_KEY)(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=entry.data,
            last_accessed=entry.last_accessed
        ))


    async def async_remove_record_method(self, event: Event, entry: CacheEntry[VT], *args, **kwargs):
        getattr(self.async_removal_record, COLLECTION_ADD_KEY)(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=await entry.async_data,
            last_accessed=entry.last_accessed
        ))

    def update_access_record(self, event: Event, entry: CacheEntry[VT], *args, **kwargs):
        getattr(self.access_record, COLLECTION_ADD_KEY)(AccessRecord(
            event=event.event_name,
            id=entry.identifier,
            last_accessed=entry.last_accessed
        ))

    def async_update_access_record(self, event: Event, entry: CacheEntry[VT], *args, **kwargs):
        getattr(self.async_access_record, COLLECTION_ADD_KEY)(AccessRecord(
            event=event.event_name,
            id=entry.identifier,
            last_accessed=entry.last_accessed
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
        self.assertEqual(len(self.access_record), records_added * 4 + records_removed * 5)

    async def test_accesscache(self):
        records_added = 0
        records_removed = 0

        for sync_index, test_data in enumerate(SYNC_TEST_DATA):
            records_added += 1
            self.cache[test_data.identifier] = test_data.data
            await self.cache.resolve_leftover_tasks()

            self.compare_records(records_added, records_removed)

        for async_index, test_data in enumerate(ASYNC_TEST_DATA):
            records_added += 1
            await self.cache.async_set(test_data.identifier, test_data.data)

            self.compare_records(records_added, records_removed)

        for remove_sync_index, test_data in enumerate(SYNC_TEST_DATA):
            records_removed += 1
            self.cache.remove(test_data.identifier)

            # This isn't awaiting the removal functions as needed
            await self.cache.resolve_leftover_tasks()

            self.compare_records(records_added, records_removed)

        for remove_async_index, test_data in enumerate(ASYNC_TEST_DATA):
            records_removed += 1
            await self.cache.remove_async(test_data.identifier)

            self.compare_records(records_added, records_removed)
