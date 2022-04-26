import unittest
from ..modeldata.data.dataset import Dataset
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, TimeRange
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union


class MockDatasetImpl(Dataset):
    """
    A basic mock implementation for testing purposes.
    """

    def __init__(self, *args, **kwargs):
        super(MockDatasetImpl, self).__init__(*args, **kwargs)

    @classmethod
    def additional_init_param_deserialized(cls, json_obj: dict) -> Dict[str, Any]:
        """
        Deserialize any other params needed for this type's init function, returning in a map for ``kwargs`` use.

        The main ::method:`factory_init_from_deserialized_json` class method for the base ::class:`Dataset` type handles
        a large amount of the work for deserialization.  However, subtypes could have additional params they require
        in their ::method:`__init__`.  This function should do this deserialization work for any subtype, and return a
        deserialized dictionary.  The keys should be the names of the relevant ::method:`__init__` parameters.

        In the event a type's ::method:`__init__` method takes no additional params beyond the base type, its
        implementation of this function should return an empty dictionary.

        Any types with an init that does not have one or more of the params of the base type's init should fully
        override ::method:`factory_init_from_deserialized_json`.

        Parameters
        ----------
        json_obj : dict
            The serialized form of the object that is a subtype of ::class:`Dataset`.

        Returns
        -------
        Dict[str, Any]
            A dictionary of ``kwargs`` for those init params and values beyond what the base type uses.
        """
        return dict()


class TestDataset(unittest.TestCase):

    @classmethod
    def get_dataset_testing_type(cls):
        return MockDatasetImpl

    @classmethod
    def generate_testing_time_range(cls, begin: Union[str, datetime], length: Optional[timedelta] = None,
                                    pattern: Optional[str] = None) -> TimeRange:
        pattern = TimeRange.get_datetime_str_format() if pattern is None else pattern
        begin = begin if isinstance(begin, datetime) else datetime.strptime(begin, pattern)
        end = begin + (timedelta(days=30) if length is None else length)
        return TimeRange(begin=begin, end=end, variable='', datetime_pattern=pattern)

    def gen_dataset_name(self, ex_indx: int):
        return 'test-dataset-{}'.format(ex_indx)

    def _init_dataset_example(self, ex_indx: int, **kwargs):
        return self.DATASET_TYPE(name=self.gen_dataset_name(ex_indx), category=self.example_categories[ex_indx],
                                 data_domain=self.example_domains[ex_indx], created_on=self._created_on,
                                 access_location="location_{}".format(ex_indx), is_read_only=False, **kwargs)

    def setUp(self) -> None:
        self.DATASET_TYPE = self.get_dataset_testing_type()

        self._created_on_str = '2022-04-01 12:00:00'
        self._created_on = datetime.strptime(self._created_on_str, TimeRange.get_datetime_str_format())

        self.example_time_ranges = []
        self.example_catchment_restrictions = []
        self.example_domains = []
        self.example_categories = []
        self.example_formats = []
        self.example_data = []
        self.example_datasets = []

        # Prep example 0
        indx_val = 0
        self.example_time_ranges.append(self.generate_testing_time_range(begin='2022-01-01 00:00:00'))
        self.example_catchment_restrictions.append(DiscreteRestriction("catchment_id", ['cat-1', 'cat-2', 'cat-3']))
        self.example_categories.append(DataCategory.FORCING)
        self.example_formats.append(DataFormat.AORC_CSV)

        # Prep example 1
        indx_val += 1
        self.example_time_ranges.append(self.generate_testing_time_range(begin='2022-01-01 00:00:00'))
        self.example_catchment_restrictions.append(DiscreteRestriction("id", ['cat-1', 'cat-2', 'cat-3']))
        self.example_categories.append(DataCategory.CONFIG)
        self.example_formats.append(DataFormat.NGEN_REALIZATION_CONFIG)

        # Then finally generate the example dataset serialized dicts and objects
        for i in range(len(self.example_categories)):
            self.example_domains.append(DataDomain(data_format=self.example_formats[i],
                                                   continuous_restrictions=[self.example_time_ranges[i]],
                                                   discrete_restrictions=[self.example_catchment_restrictions[i]]))
            self.example_datasets.append(self._init_dataset_example(i))
            date_fmt = self.DATASET_TYPE.get_datetime_str_format()
            self.example_data.append({self.DATASET_TYPE._KEY_NAME: self.gen_dataset_name(i),
                                      self.DATASET_TYPE._KEY_DATA_DOMAIN: self.example_domains[i].to_dict(),
                                      self.DATASET_TYPE._KEY_DATA_CATEGORY: self.example_categories[i].name,
                                      self.DATASET_TYPE._KEY_UUID: str(self.example_datasets[i].uuid),
                                      self.DATASET_TYPE._KEY_ACCESS_LOCATION: 'location_{}'.format(i),
                                      self.DATASET_TYPE._KEY_IS_READ_ONLY: False,
                                      self.DATASET_TYPE._KEY_CREATED_ON: self._created_on.strftime(date_fmt),
                                      })

    def test_factory_init_from_deserialized_json_0_a(self):
        """ Test basic operation of function on example 0. """
        ex_indx = 0
        data_dict = self.example_data[ex_indx]
        expected_dataset = self.example_datasets[ex_indx]

        dataset = self.DATASET_TYPE.factory_init_from_deserialized_json(data_dict)

        self.assertEqual(expected_dataset, dataset)

    # TODO: need unit tests for deserializing that ensure all properties are maintained as expected

    # TODO: need unit tests for all properties after normal init

    def test_factory_init_from_deserialized_json_1_a(self):
        """ Test basic operation of function on example 1. """
        ex_indx = 1
        data_dict = self.example_data[ex_indx]
        expected_dataset = self.example_datasets[ex_indx]

        dataset = self.DATASET_TYPE.factory_init_from_deserialized_json(data_dict)

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


