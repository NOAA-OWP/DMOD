import unittest
from datetime import datetime

from dmod.core.meta_data import DataFormat, StandardDatasetIndex
from ngen.config.realization import NgenRealization
from ..modeldata.data.item_domain_detector import RealizationConfigDomainDetector
from . import find_git_root_dir


class TestRealizationConfigDomainDetector(unittest.TestCase):

    def setUp(self):
        datetime_format: str = "%Y-%m-%d %H:%M:%S"

        self.detector_subclass = RealizationConfigDomainDetector
        self.expected_data_format = DataFormat.NGEN_REALIZATION_CONFIG

        # Setup example 0
        self.example_data = {0: find_git_root_dir().joinpath("data/example_realization_configs/ex_realization_config_03.json")}
        self.example_begins = {0: datetime.strptime("2016-01-01 00:00:00", datetime_format)}
        self.example_ends = {0: datetime.strptime("2016-01-31 23:00:00", datetime_format)}

    def test_get_data_format_0_a(self):
        """ Test that we get the correct data format for this subclass type. """
        self.assertEqual(self.expected_data_format, self.detector_subclass.get_data_format())

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
        """ Test that detect returns a domain with "global"" catchment id restriction. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertTrue(len(domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values) == 0)
