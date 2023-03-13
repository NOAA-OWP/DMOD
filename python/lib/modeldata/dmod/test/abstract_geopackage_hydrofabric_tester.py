import git
import hashlib
import unittest
from abc import ABC
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import numpy as np

from ..modeldata.hydrofabric import GeoPackageHydrofabric
from ..modeldata.hydrofabric.geopackage_hydrofabric import GeoPackageCatchment, GeoPackageNexus


class AbstractGeoPackageHydrofabricTester(ABC, unittest.TestCase):

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
