import git
import hashlib
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import numpy as np

from ..modeldata.hydrofabric import GeoPackageHydrofabric
from ..modeldata.hydrofabric.geopackage_hydrofabric import GeoPackageCatchment, GeoPackageNexus
from ..test.abstract_geopackage_hydrofabric_tester import AbstractGeoPackageHydrofabricTester


class TestGeoPackageNexus(AbstractGeoPackageHydrofabricTester):

    def setUp(self) -> None:
        super().setUp()

        self.example_nex_ids = list()
        self.example_nexuses = list()
        self.example_contributing = list()
        self.example_receiving = list()

        # Example 0: nex-8 from hydrofabric example 1
        hydrofabric = self.hydrofabric_ex[1]
        nex_id = 'nex-8'
        contrib = 'cat-7'
        receiv = 'cat-8'
        self.example_nex_ids.append(nex_id)
        self.example_nexuses.append(hydrofabric.get_nexus_by_id(nex_id))
        self.example_contributing.append(hydrofabric.get_catchment_by_id(contrib))
        self.example_receiving.append(hydrofabric.get_catchment_by_id(receiv))

    def test_contributing_catchments_0_a(self):
        """
        Test that the contributing catchment is a valid object.
        """
        ex_num = 0

        nexus = self.example_nexuses[ex_num]
        all_contributing = nexus.contributing_catchments
        actual_contrib = all_contributing[0]

        self.assertIsInstance(actual_contrib, GeoPackageCatchment)

    def test_contributing_catchments_0_b(self):
        """
        Test that the contributing catchment is the expected object.
        """
        ex_num = 0

        nexus = self.example_nexuses[ex_num]
        expected_contrib = self.example_contributing[ex_num]
        all_contributing = nexus.contributing_catchments
        actual_contrib = all_contributing[0]

        self.assertEqual(expected_contrib, actual_contrib)

    def test_receiving_catchments_0_a(self):
        """
        Test that the receiving catchment is a valid object.
        """
        ex_num = 0

        nexus = self.example_nexuses[ex_num]
        all_receiv = nexus.receiving_catchments
        actual_receiv = all_receiv[0]

        self.assertIsInstance(actual_receiv, GeoPackageCatchment)

    def test_receiving_catchments_0_b(self):
        """
        Test that the receiving catchment is the expected object.
        """
        ex_num = 0

        nexus = self.example_nexuses[ex_num]
        expected_receiv = self.example_receiving[ex_num]
        all_receiv = nexus.receiving_catchments
        actual_receiv = all_receiv[0]

        self.assertEqual(expected_receiv, actual_receiv)

