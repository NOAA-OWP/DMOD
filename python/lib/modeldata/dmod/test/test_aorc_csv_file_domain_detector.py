import unittest
from datetime import datetime

from dmod.core.meta_data import DataFormat, StandardDatasetIndex
from dmod.core.data_domain_detectors import ItemDataDomainDetectorRegistry
from ..modeldata.data.item_domain_detector import AorcCsvFileDomainDetector
from . import find_git_root_dir


class TestAorcCsvFileDomainDetector(unittest.TestCase):

    def setUp(self):
        self.detector_subclass = AorcCsvFileDomainDetector
        self.expected_data_format = DataFormat.AORC_CSV
        self.registry = ItemDataDomainDetectorRegistry.get_instance()
        self.registry.register(self.detector_subclass)

        # Setup example 0
        self.example_data = {0: find_git_root_dir().joinpath("data/example_forcing_aorc_csv/cat-12.csv")}
        self.example_begins = {0: datetime.strptime("2016-01-01 00:00:00", self.detector_subclass._datetime_format)}
        self.example_ends = {0: datetime.strptime("2016-01-31 23:00:00", self.detector_subclass._datetime_format)}
        self.example_cat_id = {0: "cat-12"}

    def test_get_data_format_0_a(self):
        """ Test that we get the correct data format for this subclass type. """
        self.assertEqual(self.expected_data_format, self.detector_subclass.get_data_format())

    def test_registration_0_a(self):
        """ Test that registration added this type to superclass's registered collection. """
        self.assertTrue(self.registry.is_registered(self.detector_subclass))

    def test_detect_0_a(self):
        """ Test that detect returns a domain with the right data format. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(self.expected_data_format, domain.data_format)

    def test_detect_0_b(self):
        """ Test that detect returns a domain with the right begin time. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        time_range = domain.continuous_restrictions[StandardDatasetIndex.TIME]
        self.assertEqual(self.example_begins[ex_idx], time_range.begin)

    def test_detect_0_c(self):
        """ Test that detect returns a domain with the right end time. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        time_range = domain.continuous_restrictions[StandardDatasetIndex.TIME]
        self.assertEqual(self.example_ends[ex_idx], time_range.end)

    def test_detect_0_d(self):
        """ Test that detect returns a domain with a single catchment id restriction. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(1, len(domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values))

    def test_detect_0_e(self):
        """ Test that detect returns a domain with the right catchment id restriction. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(self.example_cat_id[ex_idx],
                         domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values[0])
