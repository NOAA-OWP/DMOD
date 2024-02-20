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

from ...core.common import CacheEntry
from ...core.common import AccessCache
from ...core.common.collections.cache import hash_hashable_map_sequence
from ...core.events import Event

from ...core.common.collections.constants import ValueType

GLOBAL_ACCESS_RECORD = []
GLOBAL_REMOVAL_RECORD = []
GLOBAL_ADDITION_RECORD = []

GLOBAL_ASYNC_ACCESS_RECORD = []
GLOBAL_ASYNC_REMOVAL_RECORD = []
GLOBAL_ASYNC_ADDITION_RECORD = []

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


def add_record(event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
    GLOBAL_ADDITION_RECORD.append(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=entry.data,
        last_accessed=entry.last_accessed
    ))


async def async_add_record(event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
    GLOBAL_ASYNC_ADDITION_RECORD.append(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=await entry.async_data,
        last_accessed=entry.last_accessed
    ))


def remove_record(event: Event, entry: CacheEntry[ValueType],  *args, **kwargs):
    GLOBAL_REMOVAL_RECORD.append(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=entry.data,
        last_accessed=entry.last_accessed
    ))


async def async_remove_record(event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
    GLOBAL_ASYNC_REMOVAL_RECORD.append(ActionRecord(
        event=event.event_name,
        id=entry.identifier,
        data=await entry.async_data,
        last_accessed=entry.last_accessed
    ))


def update_access_record(event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
    GLOBAL_ACCESS_RECORD.append(AccessRecord(
        event=event.event_name,
        id=entry.identifier,
        last_accessed=entry.last_accessed
    ))


def async_update_access_record(event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
    GLOBAL_ASYNC_ACCESS_RECORD.append(AccessRecord(
        event=event.event_name,
        id=entry.identifier,
        last_accessed=entry.last_accessed
    ))


class TestAccessCache(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.access_record = []
        self.removal_record = []
        self.addition_record = []

        self.async_access_record = []
        self.async_removal_record = []
        self.async_addition_record = []

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
        entry: CacheEntry[ValueType],
        *args,
        **kwargs
    ):
        self.addition_record.append(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=entry.data,
            last_accessed=entry.last_accessed
        ))

    async def async_add_record_method(self, event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
        self.async_addition_record.append(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=await entry.async_data,
            last_accessed=entry.last_accessed
        ))


    def remove_record_method(self, event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
        self.removal_record.append(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=entry.data,
            last_accessed=entry.last_accessed
        ))


    async def async_remove_record_method(self, event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
        self.async_removal_record.append(ActionRecord(
            event=event.event_name,
            id=entry.identifier,
            data=await entry.async_data,
            last_accessed=entry.last_accessed
        ))

    def update_access_record(self, event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
        self.access_record.append(AccessRecord(
            event=event.event_name,
            id=entry.identifier,
            last_accessed=entry.last_accessed
        ))

    def async_update_access_record(self, event: Event, entry: CacheEntry[ValueType], *args, **kwargs):
        self.async_access_record.append(AccessRecord(
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

    def test_hash_hashable_map_sequence(self):
        input_1 = [{'one': 48}, {'two': 2}, {'three': 3}]
        input_2 = {object(): 42, object(): 0}

        input_1_hash = hash_hashable_map_sequence(input_1)
        input_2_hash = hash_hashable_map_sequence(input_2)

        self.assertNotEqual(input_1_hash, input_2_hash)

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
