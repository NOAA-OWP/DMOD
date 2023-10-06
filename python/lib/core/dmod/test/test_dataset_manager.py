import unittest
from uuid import uuid4
from ..core.dataset import Dataset, DatasetManager, DatasetType, InitialDataAdder
from ..core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, StandardDatasetIndex
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class MockDatasetManager(DatasetManager):

    ACCESS_LOC = "location_0"

    def add_data(self, dataset_name: str, dest: str, data: Optional[bytes] = None, source: Optional[str] = None,
                 is_temp: bool = False, **kwargs) -> bool:
        pass

    def combine_partials_into_composite(self, dataset_name: str, item_name: str, combined_list: List[str]) -> bool:
        pass

    def create(self, name: str, category: DataCategory, domain: DataDomain, is_read_only: bool,
               initial_data: Optional[InitialDataAdder] = None, expires_on: Optional[datetime] = None) -> Dataset:
        """
        A trivial implementation, intended just to test that the convenience method ::method:`create_temporary` works.

        Parameters
        ----------
        name
        category
        domain
        is_read_only
        initial_data
        expires_on

        Returns
        -------

        """
        return Dataset(name=name, category=category, data_domain=domain, is_read_only=is_read_only, expires=expires_on,
                       access_location=self.ACCESS_LOC)

    def delete(self, dataset: Dataset, **kwargs) -> bool:
        pass

    @property
    def data_chunking_params(self) -> Optional[Tuple[str, str]]:
        pass

    def get_data(self, dataset_name: str, item_name: str, **kwargs) -> Union[bytes, Any]:
        pass

    def list_files(self, dataset_name: str, **kwargs) -> List[str]:
        pass

    def reload(self, reload_from: str, serialized_item: Optional[str] = None) -> Dataset:
        pass

    @property
    def supported_dataset_types(self) -> Set[DatasetType]:
        pass


class TestDatasetManager(unittest.TestCase):

    def setUp(self):
        self._manager = MockDatasetManager()

        self._ex_datasets: Dict[int, Dataset] = dict()

        # Ex dataset 1
        ex_idx = 1
        disc_rest = DiscreteRestriction(StandardDatasetIndex.CATCHMENT_ID, values=['cat-1', 'cat-2', 'cat-3'])
        domain = DataDomain(data_format=DataFormat.NGEN_REALIZATION_CONFIG, discrete_restrictions=[disc_rest])
        self._ex_datasets[ex_idx] = Dataset(name="test_ds_1", category=DataCategory.CONFIG, data_domain=domain,
                                            access_location=self._manager.ACCESS_LOC, is_read_only=False)

    def tearDown(self):
        pass

    def test_create_temporary_1_a(self):
        """ Test that creating with implied expire gives a temporary dataset. """
        ex_idx = 1
        base_dataset = self._ex_datasets[ex_idx]

        dataset_w_create_temp = self._manager.create_temporary(name=base_dataset.name, category=base_dataset.category,
                                                               domain=base_dataset.data_domain,
                                                               is_read_only=base_dataset.is_read_only)
        self.assertTrue(dataset_w_create_temp.is_temporary)

    def test_create_temporary_1_b(self):
        """ Test that creating with implied expire gives a temporary dataset with expected (roughly) expires_on. """
        ex_idx = 1
        base_dataset = self._ex_datasets[ex_idx]

        # We don't get direct access to ``now()`` in advance, so track times and make sure we are within some bounds
        pre_create_time = datetime.now()
        created_dataset = self._manager.create_temporary(name=base_dataset.name, category=base_dataset.category,
                                                         domain=base_dataset.data_domain,
                                                         is_read_only=base_dataset.is_read_only)
        post_create_time = datetime.now()

        self.assertLessEqual(created_dataset.expires, (post_create_time+timedelta(days=1)))
        # Drop amounts less than a second, as the expires attribute does this
        self.assertGreaterEqual(created_dataset.expires, (pre_create_time.replace(microsecond=0)+timedelta(days=1)))

    def test_create_temporary_1_c(self):
        """ Test that creating with implied expire (a 1-day-from-now) gives equivalent to regular (explicit) create. """
        ex_idx = 1
        base_dataset = self._ex_datasets[ex_idx]

        dataset_w_create_temp = self._manager.create_temporary(name=base_dataset.name, category=base_dataset.category,
                                                               domain=base_dataset.data_domain,
                                                               is_read_only=base_dataset.is_read_only)
        dataset_w_create = self._manager.create(name=base_dataset.name, category=base_dataset.category,
                                                domain=base_dataset.data_domain, is_read_only=base_dataset.is_read_only,
                                                expires_on=dataset_w_create_temp.expires)
        # Have to manipulate a bit here to make sure the UUIDs match, as create itself doesn't account for them directly
        dataset_w_create.uuid = dataset_w_create_temp.uuid

        self.assertEqual(dataset_w_create, dataset_w_create_temp)

    def test_create_temporary_2_a(self):
        """ Test that creating with explicit expire gives equivalent to regular explicit create. """
        ex_idx = 1
        base_dataset = self._ex_datasets[ex_idx]

        expire_time = datetime.now() + timedelta(days=1, hours=3, minutes=5)

        dataset_w_create = self._manager.create(name=base_dataset.name, category=base_dataset.category,
                                                domain=base_dataset.data_domain, is_read_only=base_dataset.is_read_only,
                                                expires_on=expire_time)
        dataset_w_create_temp = self._manager.create_temporary(name=base_dataset.name, category=base_dataset.category,
                                                               domain=base_dataset.data_domain,
                                                               is_read_only=base_dataset.is_read_only,
                                                               expires_on=expire_time)

        # Have to manipulate a bit here to make sure the UUIDs match, as create itself doesn't account for them directly
        dataset_w_create_temp.uuid = dataset_w_create.uuid

        self.assertEqual(dataset_w_create, dataset_w_create_temp)