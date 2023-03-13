import git
import hashlib
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import numpy as np

from ..modeldata.hydrofabric import GeoPackageHydrofabric
from ..modeldata.hydrofabric.geopackage_hydrofabric import GeoPackageCatchment, GeoPackageNexus, SubsetDefinition


class TestGeoPackageHydrofabric(unittest.TestCase):

    _HYDROFABRIC_1_RELATIVE_PATH = 'data/example_hydrofabric_2/hydrofabric.gpkg'

    @classmethod
    def find_project_root(cls, path: Optional[Path] = None) -> Path:
        """
        Get the project root of the repo containing the given path.

        Given a path (with ``None`` implying the current directory) assumed to be at or under a Git project's root,
        find the project root directory.

        Parameters
        ----------
        path : Path
            A file path, or ``None`` to imply use the current directory.

        Returns
        -------
        Path
            The git repository root directory.
        """
        if path is None:
            path = Path('.')
        return Path(git.Repo(path, search_parent_directories=True).git.rev_parse("--show-toplevel"))

    def setUp(self) -> None:
        proj_root: Path = self.find_project_root()
        
        self.hydrofabric_ex: Dict[int, GeoPackageHydrofabric] = dict()
        self.hydrofabric_uids: Dict[int, str] = dict()
        self.cat_id_sets: Dict[int, Set[str]] = dict()
        self.nexus_id_sets: Dict[int, Set[str]] = dict()
        self.subset_id_sets: Dict[int, Set[str]] = dict()
        self.root_catchment_ids_sets: Dict[int, Set[str]] = dict()

        # Example 1: v1.2 VPU 1
        ex_idx = 1
        file_path = proj_root.joinpath(self._HYDROFABRIC_1_RELATIVE_PATH)
        #self.hydrofabric_ex[ex_idx] = GeoPackageHydrofabric.from_file(geopackage_file=Path.home().joinpath('Downloads/conus.gpkg'))
        self.hydrofabric_ex[ex_idx] = GeoPackageHydrofabric.from_file(geopackage_file=file_path)
        self.hydrofabric_uids[ex_idx] = 'a98387f704b4fbdf5a958cb1cb7797a77cdf05fb'
        self.cat_id_sets[ex_idx] = {'cat-5', 'cat-6', 'cat-7', 'cat-8', 'cat-9', 'cat-10', 'cat-11'}
        self.nexus_id_sets[ex_idx] = {'nex-7', 'nex-8', 'nex-9', 'nex-10', 'nex-11', 'nex-12', 'tnx-1000000001'}
        self.subset_id_sets[ex_idx] = {'cat-7', 'cat-8', 'cat-9', 'nex-7', 'nex-8', 'nex-9', 'nex-10'}
        self.root_catchment_ids_sets[ex_idx] = {'cat-5', 'cat-6'}

    def tearDown(self) -> None:
        pass

    # def test_subset_hydrofabric(self):
    #     subset_def = SubsetDefinition(catchment_ids=self.cat_id_sets[1], nexus_ids=self.nexus_id_sets[1])
    #     hydrofabric = self.hydrofabric_ex[1]
    #     subset_hf = hydrofabric.get_subset_hydrofabric(subset_def)
    #     subset_hf.write_file(self.find_project_root().joinpath(self._HYDROFABRIC_1_RELATIVE_PATH), overwrite_existing=True)

    def test_get_all_catchment_ids_1_a(self):
        """
        Test that this function gets all expected catchment ids for the hydrofabric.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        expected_cat_id_set = self.cat_id_sets[ex_index]

        cat_ids = set(hydrofabric.get_all_catchment_ids())

        self.assertEqual(cat_ids, expected_cat_id_set)

    def test_get_all_nexus_ids_1_a(self):
        """
        Test that this function gets all expected nexus ids for the hydrofabric.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        expected_nexus_id_set = self.nexus_id_sets[ex_index]

        nex_ids = set(hydrofabric.get_all_nexus_ids())

        self.assertEqual(nex_ids, expected_nexus_id_set)

    def test_get_catchment_by_id_1_a(self):
        """
        Test that this function gets a test catchment by id, checking it gets a valid object back.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        catchment = hydrofabric.get_catchment_by_id(catchment_id='cat-10')
        self.assertTrue(isinstance(catchment, GeoPackageCatchment))

    def test_get_catchment_by_id_1_b(self):
        """
        Test that this function gets a test catchment by id, checking it has the expected known nexus downstream.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        catchment = hydrofabric.get_catchment_by_id(catchment_id='cat-10')
        expected_downstream_id = 'nex-11'
        self.assertEqual(catchment.outflow.id, expected_downstream_id)

    def test_get_catchment_by_id_1_c(self):
        """
        Test that this function gets a test catchment by id, checking it has the expected known nexus upstream.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        catchment = hydrofabric.get_catchment_by_id(catchment_id='cat-10')
        expected_upstream_id = 'nex-10'
        self.assertEqual(catchment.inflow.id, expected_upstream_id)

    def test_get_catchment_by_id_1_d(self):
        """
        Test that this function gets ``None`` for an unrecognized catchment id.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        catchment = hydrofabric.get_catchment_by_id(catchment_id='cat-85')
        self.assertIsNone(catchment)

    def test_get_nexus_by_id_1_a(self):
        """
        Test that this function gets a test nexus by id, checking it gets a valid object back.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        nexus = hydrofabric.get_nexus_by_id(nexus_id='nex-7')
        self.assertTrue(isinstance(nexus, GeoPackageNexus))

    def test_get_nexus_by_id_1_b(self):
        """
        Test that this function gets a test nexus by id, checking it has the expected known catchment downstream.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        nexus = hydrofabric.get_nexus_by_id(nexus_id='nex-7')
        expected_downstream_id = 'cat-7'
        self.assertEqual(nexus.receiving_catchments[0].id, expected_downstream_id)

    def test_get_nexus_by_id_1_c(self):
        """
        Test that this function gets a test nexus by id, checking it has the expected known catchment upstream.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        nexus = hydrofabric.get_nexus_by_id(nexus_id='nex-7')
        expected_upstream_id = 'cat-7'
        self.assertEqual(nexus.receiving_catchments[0].id, expected_upstream_id)

    def test_get_nexus_by_id_1_d(self):
        """
        Test that this function gets ``None`` for an unrecognized nexus id.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        nexus = hydrofabric.get_nexus_by_id(nexus_id='nex-68')
        self.assertIsNone(nexus)

    def test_subset_hydrofabric_1_a(self):
        """
        Test that all expected catchments are in a subset hydrofabric.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        subset_cat_ids = self.cat_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_nex_ids = self.nexus_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_def = SubsetDefinition(catchment_ids=subset_cat_ids, nexus_ids=subset_nex_ids)
        subset_hydrofabric = hydrofabric.get_subset_hydrofabric(subset_def)

        actual_cat_ids_in_subset = subset_hydrofabric.get_all_catchment_ids()

        self.assertEqual(subset_cat_ids, set(actual_cat_ids_in_subset))

    def test_subset_hydrofabric_1_b(self):
        """
        Test that all catchments in generated subset hydrofabric have catchment objects.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        subset_cat_ids = self.cat_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_nex_ids = self.nexus_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_def = SubsetDefinition(catchment_ids=subset_cat_ids, nexus_ids=subset_nex_ids)
        subset_hydrofabric = hydrofabric.get_subset_hydrofabric(subset_def)

        self.assertTrue(all([isinstance(subset_hydrofabric.get_catchment_by_id(cid), GeoPackageCatchment) for cid in
                             subset_hydrofabric.get_all_catchment_ids()]))

    def test_subset_hydrofabric_1_c(self):
        """
        Test that all expected nexuses are in a subset hydrofabric.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        subset_cat_ids = self.cat_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_nex_ids = self.nexus_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_def = SubsetDefinition(catchment_ids=subset_cat_ids, nexus_ids=subset_nex_ids)
        subset_hydrofabric = hydrofabric.get_subset_hydrofabric(subset_def)

        actual_nex_ids_in_subset = subset_hydrofabric.get_all_nexus_ids()

        self.assertEqual(subset_nex_ids, set(actual_nex_ids_in_subset))

    def test_subset_hydrofabric_1_d(self):
        """
        Test that all nexuses in generated subset hydrofabric have nexus objects.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        subset_cat_ids = self.cat_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_nex_ids = self.nexus_id_sets[ex_index].intersection(self.subset_id_sets[ex_index])
        subset_def = SubsetDefinition(catchment_ids=subset_cat_ids, nexus_ids=subset_nex_ids)
        subset_hydrofabric = hydrofabric.get_subset_hydrofabric(subset_def)

        self.assertTrue(all([isinstance(subset_hydrofabric.get_nexus_by_id(nid), GeoPackageNexus) for nid in
                             subset_hydrofabric.get_all_nexus_ids()]))

    # TODO: think about how we'd want to test get_subset_hydrofabric() and write_file() (probably the same way)
    
    def test_is_catchment_recognized_1_a(self):
        """
        Test if known catchment id ``cat-10`` is recognized.
        """
        ex_index = 1
        cat_id = 'cat-10'

        hydrofabric = self.hydrofabric_ex[ex_index]
        
        self.assertTrue(hydrofabric.is_catchment_recognized(catchment_id=cat_id))

    def test_is_catchment_recognized_1_b(self):
        """
        Test if known catchment id ``cat-6`` is recognized.
        """
        ex_index = 1
        cat_id = 'cat-6'

        hydrofabric = self.hydrofabric_ex[ex_index]

        self.assertTrue(hydrofabric.is_catchment_recognized(catchment_id=cat_id))

    def test_is_catchment_recognized_1_c(self):
        """
        Test if unknown catchment id ``cat-67`` is not recognized.
        """
        ex_index = 1
        cat_id = 'cat-67'

        hydrofabric = self.hydrofabric_ex[ex_index]

        self.assertFalse(hydrofabric.is_catchment_recognized(catchment_id=cat_id))

    def test_is_catchment_recognized_1_d(self):
        """
        Test if all catchment from the hydrofabric ids are recognized.
        """
        ex_index = 1
        hydrofabric = self.hydrofabric_ex[ex_index]
        self.assertTrue(all([hydrofabric.is_catchment_recognized(cid) for cid in hydrofabric.get_all_catchment_ids()]))

    def test_is_nexus_recognized_1_a(self):
        """
        Test if known nexus id ``nex-12`` is recognized.
        """
        ex_index = 1
        nex_id = 'nex-12'

        hydrofabric = self.hydrofabric_ex[ex_index]

        self.assertTrue(hydrofabric.is_nexus_recognized(nexus_id=nex_id))

    def test_is_nexus_recognized_1_b(self):
        """
        Test if unknown nexus id ``nex-65`` is not recognized.
        """
        ex_index = 1
        nex_id = 'nex-65'

        hydrofabric = self.hydrofabric_ex[ex_index]

        self.assertFalse(hydrofabric.is_nexus_recognized(nexus_id=nex_id))

    def test_is_nexus_recognized_1_c(self):
        """
        Test if all nexus from the hydrofabric ids are recognized.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]

        self.assertTrue(all([hydrofabric.is_nexus_recognized(nid) for nid in hydrofabric.get_all_nexus_ids()]))

    def test_roots_1_a(self):
        """
        Test that function gets expected root catchment ids for the hydrofabric, by comparing to a known hash value.
        """
        ex_index = 1

        hydrofabric = self.hydrofabric_ex[ex_index]
        expected_root_cat_ids = self.root_catchment_ids_sets[ex_index]

        root_cat_ids = set(hydrofabric.roots)

        self.assertEqual(root_cat_ids, expected_root_cat_ids)

    def test_uid_1_a(self):
        """
        Test that the hydrofabric instance for example one has the expected unique id.
        """
        ex_index = 1
        hydrofabric = self.hydrofabric_ex[ex_index]
        expected_uid = self.hydrofabric_uids[ex_index]
        self.assertEqual(hydrofabric.uid, expected_uid)

    def test_vpu_1_a(self):
        """
        Test that the hydrofabric instance for example one returns ``None`` for the VPU value.
        """
        ex_index = 1
        hydrofabric = self.hydrofabric_ex[ex_index]
        self.assertIsNone(hydrofabric.vpu)
