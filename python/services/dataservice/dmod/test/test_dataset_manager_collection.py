from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Dict, Set

import git
from dmod.core.dataset import Dataset, DatasetType
from dmod.core.exception import DmodRuntimeError
from dmod.dataservice.dataset_manager_collection import DatasetManagerCollection

from .test_service_manager import MockDataset, MockDatasetManager


class MockDatasetManagerSupportsMultipleTypes(MockDatasetManager):
    @property
    def supported_dataset_types(self) -> Set[DatasetType]:
        return {DatasetType.FILESYSTEM, DatasetType.OBJECT_STORE}


class TestDatasetManagerCollection(unittest.TestCase):
    def setUp(self):
        self.dataset_manager_collection = DatasetManagerCollection()

    @property
    def proj_root(self) -> Path:
        return Path(git.Repo(__file__, search_parent_directories=True).working_dir)

    @property
    def datasets(self) -> Dict[str, Dataset]:
        example_serial_datasets_dir = (
            self.proj_root / "data/serialized_dataset_examples"
        )
        dataset_files = list(example_serial_datasets_dir.glob("*.json"))
        datasets: Dict[str, Dataset] = dict()
        for d_file in dataset_files:
            dataset: Dataset | None = MockDataset.factory_init_from_deserialized_json(
                json.loads(d_file.read_text())
            )
            assert (
                dataset is not None
            ), f"failed to deserialize {d_file!r} into MockDataset"
            datasets[dataset.name] = dataset
        return datasets

    def test_add_straight_and_narrow(self):
        dmc = DatasetManagerCollection()
        assert len(dict(dmc.managers())) == 0
        dm = MockDatasetManager(datasets=self.datasets)
        dmc.add(dm)
        self.assertSetEqual(
            set(self.datasets.keys()).symmetric_difference(dmc.known_datasets().keys()),
            set(),
        )
        for type_ in dm.supported_dataset_types:
            self.assertEqual(dmc.manager(type_), dm)

        for _, mng in dmc.managers():
            self.assertEqual(mng, dm)

    def test_add_twice_is_noop(self):
        dmc = DatasetManagerCollection()
        assert len(dict(dmc.managers())) == 0
        dm = MockDatasetManager(datasets=self.datasets)
        dmc.add(dm)
        assert len(dict(dmc.managers())) == 1
        dmc.add(dm)
        assert len(dict(dmc.managers())) == 1

    def test_add_cannot_have_distinct_managers_of_same_type(self):
        dmc = DatasetManagerCollection()
        assert len(dict(dmc.managers())) == 0

        dm = MockDatasetManager(datasets=self.datasets)
        dmc.add(dm)
        assert len(dict(dmc.managers())) == 1

        dm2 = MockDatasetManager(datasets=self.datasets)
        with self.assertRaises(DmodRuntimeError):
            dmc.add(dm2)

    def test_add_manager_can_be_associated_with_multiple_dataset_types(self):
        dmc = DatasetManagerCollection()
        assert len(dict(dmc.managers())) == 0
        dm = MockDatasetManagerSupportsMultipleTypes(datasets=self.datasets)
        self.assertGreater(len(dm.supported_dataset_types), 1)
        dmc.add(dm)
        for type_ in dm.supported_dataset_types:
            self.assertEqual(dmc.manager(type_), dm)
