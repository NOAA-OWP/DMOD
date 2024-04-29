import unittest

from dmod.core.meta_data import DataFormat, StandardDatasetIndex
from ..modeldata.data.item_domain_detector import GeoPackageHydrofabricDomainDetector

from . import find_git_root_dir


class TestGeoPackageHydrofabricDomainDetector(unittest.TestCase):

    def setUp(self):
        self.detector_subclass = GeoPackageHydrofabricDomainDetector
        self.expected_data_format = DataFormat.NGEN_GEOPACKAGE_HYDROFABRIC_V2
        self.hyfab_ver = "2.0.1"

        # Setup example 0
        self.example_data = {0: find_git_root_dir().joinpath("data/example_hydrofabric_2/hydrofabric.gpkg")}
        self.example_vpu = {0: "VPU09"}
        self.example_restriction_vpu = {0: "VPU09"}
        self.example_cat_ids = {0: sorted(['cat-8', 'cat-5', 'cat-9', 'cat-6', 'cat-7', 'cat-10', 'cat-11'])}

    def test_get_data_format_0_a(self):
        """ Test that we get the correct data format for this subclass type. """
        self.assertEqual(self.detector_subclass.get_data_format(), self.expected_data_format)

    def test_detect_0_a(self):
        """ Test that detect returns a domain with the right data format. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver, region=self.example_vpu[ex_idx])
        self.assertEqual(self.expected_data_format, domain.data_format)

    def test_detect_0_b(self):
        """ Test that detect returns a domain with the right catchments. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver, region=self.example_vpu[ex_idx])
        self.assertEqual(self.example_cat_ids[ex_idx],
                         sorted(domain.discrete_restrictions[StandardDatasetIndex.CATCHMENT_ID].values))

    def test_detect_0_c(self):
        """ Test that domain from detect includes version when provided. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver, region=self.example_vpu[ex_idx])
        version_restrict = domain.discrete_restrictions[StandardDatasetIndex.HYDROFABRIC_VERSION]
        self.assertEqual(1, len(version_restrict.values))
        self.assertEqual(self.hyfab_ver, version_restrict.values[0])

    def test_detect_0_d(self):
        """ Test that domain from detect doesn't include version when not provided. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(region=self.example_vpu[ex_idx])
        self.assertNotIn(StandardDatasetIndex.HYDROFABRIC_VERSION, domain.discrete_restrictions.keys())

    def test_detect_0_e(self):
        """ Test that domain from detect includes region when provided. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver, region=self.example_vpu[ex_idx])
        region_restrict = domain.discrete_restrictions[StandardDatasetIndex.HYDROFABRIC_REGION]
        self.assertEqual(1, len(region_restrict.values))
        self.assertEqual(self.example_restriction_vpu[ex_idx], region_restrict.values[0])

    def test_detect_0_f(self):
        """ Test that domain from detect includes region when provided. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver, region=self.example_restriction_vpu[ex_idx])
        region_restrict = domain.discrete_restrictions[StandardDatasetIndex.HYDROFABRIC_REGION]
        self.assertEqual(1, len(region_restrict.values))
        self.assertEqual(self.example_restriction_vpu[ex_idx], region_restrict.values[0])

    def test_detect_0_g(self):
        """ Test that domain from detect doesn't include region when not provided. """
        ex_idx = 0

        detector = self.detector_subclass(item=self.example_data[ex_idx])
        domain = detector.detect(version=self.hyfab_ver)
        self.assertNotIn(StandardDatasetIndex.HYDROFABRIC_REGION, domain.discrete_restrictions.keys())
