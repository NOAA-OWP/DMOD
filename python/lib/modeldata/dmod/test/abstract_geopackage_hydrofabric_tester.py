import git
import unittest
from abc import ABC
from pathlib import Path
from typing import Dict, Optional
from ..modeldata.hydrofabric import GeoPackageHydrofabric


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

        # Example 1: v1.2 VPU 1
        ex_idx = 1
        file_path = proj_root.joinpath(self._HYDROFABRIC_1_RELATIVE_PATH)
        self.hydrofabric_ex[ex_idx] = GeoPackageHydrofabric.from_file(geopackage_file=file_path)
