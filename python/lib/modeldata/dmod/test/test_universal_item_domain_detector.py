import unittest
from datetime import datetime

from dmod.core.meta_data import DataFormat, StandardDatasetIndex
from dmod.core.data_domain_detectors import ItemDataDomainDetectorRegistry, UniversalItemDomainDetector

from ..modeldata.data.item_domain_detector import AorcCsvFileDomainDetector, GeoPackageHydrofabricDomainDetector
from . import find_git_root_dir


class TestUniversalItemDomainDetector(unittest.TestCase):

    def setUp(self):
        self.registry = ItemDataDomainDetectorRegistry.get_instance()
        self.registry.register(AorcCsvFileDomainDetector)
        self.registry.register(GeoPackageHydrofabricDomainDetector)
        self.detector_subclass = UniversalItemDomainDetector

        # Setup example 0
        self.expected_data_format = {0: DataFormat.AORC_CSV}
        self.example_data = {0: find_git_root_dir().joinpath("data/example_forcing_aorc_csv/cat-12.csv")}
        self.example_begins = {0: datetime.strptime("2016-01-01 00:00:00", AorcCsvFileDomainDetector._datetime_format)}
        self.example_ends = {0: datetime.strptime("2016-01-31 23:00:00", AorcCsvFileDomainDetector._datetime_format)}
        self.example_cat_ids = {0: "cat-12"}

        # Setup example 1
        self.expected_data_format[1] = DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2
        self.example_data[1] = find_git_root_dir().joinpath("data/example_hydrofabric_2/hydrofabric.gpkg")
        self.example_cat_ids[1] = sorted(['cat-8', 'cat-5', 'cat-9', 'cat-6', 'cat-7', 'cat-10', 'cat-11'])

    def test_get_data_format_0_a(self):
        """ Test that we get ``None`` for the data format for this subclass type. """
        self.assertIsNone(self.detector_subclass.get_data_format())

    def test_registration_0_a(self):
        """ Test registration adds this type to superclass's registered collection. """
        self.assertTrue(self.registry.is_registered(self.detector_subclass))

    def test_registration_0_b(self):
        """ Test registration adds first imported type to superclass's registered collection. """
        self.assertTrue(self.registry.is_registered(AorcCsvFileDomainDetector))

    def test_registration_1_b(self):
        """ Test registration adds second imported type to superclass's registered collection. """
        self.assertTrue(self.registry.is_registered(GeoPackageHydrofabricDomainDetector))

    def test_detect_0_a(self):
        """ Test that detect returns a domain with the right data format. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(self.expected_data_format[ex_idx], domain.data_format)

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
        self.assertEqual(self.example_cat_ids[ex_idx],
                         domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values[0])

    def test_detect_1_a(self):
        """ Test that detect returns a domain with the right data format. """
        ex_idx = 1

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(self.expected_data_format[ex_idx], domain.data_format)

    def test_detect_1_b(self):
        """ Test that detect returns a domain with the right catchments. """
        ex_idx = 1

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect()
        self.assertEqual(self.example_cat_ids[ex_idx],
                         sorted(domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values))

