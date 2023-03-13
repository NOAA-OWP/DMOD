import git
import hashlib
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import numpy as np

from ..modeldata.hydrofabric import GeoPackageHydrofabric
from ..modeldata.hydrofabric.geopackage_hydrofabric import GeoPackageCatchment, GeoPackageNexus
from ..test.abstract_geopackage_hydrofabric_tester import AbstractGeoPackageHydrofabricTester


class TestGeoPackageCatchment(AbstractGeoPackageHydrofabricTester):

    def setUp(self) -> None:
        super().setUp()

        self.example_cat_ids = list()
        self.example_catchments = list()
        self.example_inflows = list()
        self.example_outflows = list()

        # Example 0: cat-7 from hydrofabric example 1
        hydrofabric = self.hydrofabric_ex[1]
        cat_id = 'cat-7'
        inflow_id = 'nex-7'
        outflow_id = 'nex-8'
        self.example_cat_ids.append(cat_id)
        self.example_catchments.append(hydrofabric.get_catchment_by_id(cat_id))
        self.example_inflows.append(hydrofabric.get_nexus_by_id(inflow_id))
        self.example_outflows.append(hydrofabric.get_nexus_by_id(outflow_id))

    def test_inflow_0_a(self):
        """
        Test that the inflow nexus is a valid object.
        """
        ex_num = 0

        catchment = self.example_catchments[ex_num]

        self.assertIsInstance(catchment.inflow, GeoPackageNexus)

    def test_inflow_0_b(self):
        """
        Test that the inflow nexus is the expected object.
        """
        ex_num = 0

        catchment = self.example_catchments[ex_num]
        expected_inflow_nexus = self.example_inflows[ex_num]
        actual_inflow = catchment.inflow

        self.assertEqual(actual_inflow, expected_inflow_nexus)

    def test_outflow_0_a(self):
        """
        Test that the outflow nexus is a valid object.
        """
        ex_num = 0

        catchment = self.example_catchments[ex_num]

        self.assertIsInstance(catchment.outflow, GeoPackageNexus)

    def test_outflow_0_b(self):
        """
        Test that the outflow nexus is the expected object.
        """
        ex_num = 0

        catchment = self.example_catchments[ex_num]
        expected_outflow_nexus = self.example_outflows[ex_num]
        actual_outflow = catchment.outflow

        self.assertEqual(actual_outflow, expected_outflow_nexus)






