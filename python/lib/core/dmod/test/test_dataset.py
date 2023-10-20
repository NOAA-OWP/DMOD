import unittest
from uuid import uuid4
from ..core.dataset import Dataset, DatasetType
from ..core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, TimeRange, StandardDatasetIndex
from datetime import datetime, timedelta
from typing import Optional, Union


class TestDataset(unittest.TestCase):
    @classmethod
    def generate_testing_time_range(cls, begin: Union[str, datetime], length: Optional[timedelta] = None,
                                    pattern: Optional[str] = None) -> TimeRange:
        pattern = TimeRange.get_datetime_str_format() if pattern is None else pattern
        begin = begin if isinstance(begin, datetime) else datetime.strptime(begin, pattern)
        end = begin + (timedelta(days=30) if length is None else length)
        return TimeRange(begin=begin, end=end, datetime_pattern=pattern)

    def gen_dataset_name(self, ex_indx: int):
        return 'test-dataset-{}'.format(ex_indx)

    def _init_dataset_example(self, ex_indx: int, **kwargs):
        return Dataset(name=self.gen_dataset_name(ex_indx), category=self.example_categories[ex_indx],
                       dataset_type=self.example_types[ex_indx], data_domain=self.example_domains[ex_indx],
                       created_on=self._created_on, access_location="location_{}".format(ex_indx), is_read_only=False,
                       **kwargs)

    def setUp(self) -> None:
        self._created_on_str = '2022-04-01 12:00:00'
        self._created_on = datetime.strptime(self._created_on_str, TimeRange.get_datetime_str_format())

        self.example_types = []
        self.example_time_ranges = []
        self.example_catchment_restrictions = []
        self.example_domains = []
        self.example_categories = []
        self.example_formats = []
        self.example_data = []
        self.example_datasets = []

        # Prep example 0
        indx_val = 0
        self.example_types.append(DatasetType.OBJECT_STORE)
        self.example_time_ranges.append(self.generate_testing_time_range(begin='2022-01-01 00:00:00'))
        self.example_catchment_restrictions.append(DiscreteRestriction("CATCHMENT_ID", ['cat-1', 'cat-2', 'cat-3']))
        self.example_categories.append(DataCategory.FORCING)
        self.example_formats.append(DataFormat.AORC_CSV)

        # Prep example 1
        indx_val += 1
        self.example_types.append(DatasetType.OBJECT_STORE)
        self.example_time_ranges.append(self.generate_testing_time_range(begin='2022-01-01 00:00:00'))
        self.example_catchment_restrictions.append(DiscreteRestriction("CATCHMENT_ID", ['cat-1', 'cat-2', 'cat-3']))
        self.example_categories.append(DataCategory.CONFIG)
        self.example_formats.append(DataFormat.NGEN_REALIZATION_CONFIG)

        # Then finally generate the example dataset serialized dicts and objects
        for i in range(len(self.example_categories)):
            self.example_domains.append(DataDomain(data_format=self.example_formats[i],
                                                   continuous_restrictions=[self.example_time_ranges[i]],
                                                   discrete_restrictions=[self.example_catchment_restrictions[i]]))
            self.example_datasets.append(self._init_dataset_example(i))
            date_fmt = Dataset.get_datetime_str_format()
            self.example_data.append({"name": self.gen_dataset_name(i),
                                      "data_domain": self.example_domains[i].to_dict(),
                                      "data_category": self.example_categories[i].name,
                                      "type": self.example_types[i].name,
                                      "uuid": str(self.example_datasets[i].uuid),
                                      "access_location": 'location_{}'.format(i),
                                      "is_read_only": False,
                                      "created_on": datetime.strftime(self._created_on, Dataset._SERIAL_DATETIME_STR_FORMAT),
                                      })

    def test_schema_generation(self):
        try:
            schema = Dataset.schema()
            schema_json = Dataset.schema_json()
        except Exception as e:
            self.fail(f"Dataset object schema cannot be generated - {str(e)}")

    def test_factory_init_from_deserialized_json_0_a(self):
        """ Test basic operation of function on example 0. """
        ex_indx = 0
        data_dict = self.example_data[ex_indx]
        expected_dataset = self.example_datasets[ex_indx]

        dataset = Dataset.factory_init_from_deserialized_json(data_dict)

        self.assertEqual(expected_dataset, dataset)

    # TODO: need unit tests for deserializing that ensure all properties are maintained as expected

    # TODO: need unit tests for all properties after normal init

    def test_factory_init_from_deserialized_json_1_a(self):
        """ Test basic operation of function on example 1. """
        ex_indx = 1
        data_dict = self.example_data[ex_indx]
        expected_dataset = self.example_datasets[ex_indx]

        dataset = Dataset.factory_init_from_deserialized_json(data_dict)

        self.assertEqual(expected_dataset, dataset)

    # TODO: need unit tests for serializing (followed by re-deserializing) ensuring all properties maintained

    def test_to_dict_0_a(self):
        """ Test basic operation of function on example 0. """
        ex_indx = 0
        expected_data_dict = self.example_data[ex_indx]

        data_dict = self.example_datasets[ex_indx].to_dict()

        self.assertEqual(expected_data_dict, data_dict)

    def test_to_dict_1_a(self):
        """ Test basic operation of function on example 1. """
        ex_indx = 1
        expected_data_dict = self.example_data[ex_indx]

        data_dict = self.example_datasets[ex_indx].to_dict()

        self.assertEqual(expected_data_dict, data_dict)

    def test_fixes_377(self):
        """Verify fields with field_serializers are serialized to correct type."""

        some_id = uuid4()
        now = datetime.now()
        m = Dataset(
            name="fix-377",
            data_category=DataCategory.CONFIG,
            data_domain=DataDomain(
                data_format=DataFormat.BMI_CONFIG,
                discrete=[
                    DiscreteRestriction(
                        variable=StandardDatasetIndex.DATA_ID, values=["42"]
                    )
                ],
            ),
            access_location="test_fixes_377",
            uuid=some_id,
            is_read_only=True,
            created_on=now,
            expires=now,
            last_updated=now,
            dataset_type=DatasetType.OBJECT_STORE,
            manager_uuid=some_id,
        )
        serialized = m.dict()

        self.assertTrue(isinstance(serialized["uuid"], str))
        self.assertTrue(isinstance(serialized["manager_uuid"], str))
        self.assertTrue(isinstance(serialized["created_on"], str))
        self.assertTrue(isinstance(serialized["expires"], str))
        self.assertTrue(isinstance(serialized["last_updated"], str))
