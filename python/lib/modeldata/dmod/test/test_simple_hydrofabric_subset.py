import git
import json
import unittest

from pathlib import Path
from typing import Optional, Union
from ..modeldata.subset import SimpleHydrofabricSubset, SubsetHandlerImpl


class TestSimpleHydrofabricSubset(unittest.TestCase):

    @classmethod
    def find_project_root(cls, path: Optional[Path] = None, as_path_obj: bool = False) -> Union[Path, str, None]:
        """
        Get the project root of the repo containing the given path.

        Given a path (with ``None`` implying the current directory) assumed to be at or under a Git project's root,
        find the project root directory.

        By default, with ``as_path_obj`` taking the default value of ``False``, the method returns the project root as a
        string.  The ``as_path_obj`` can be set to ``True`` to return the root as a full ::class:`Path` object

        Parameters
        ----------
        path : Path
            A file path, or ``None`` to imply use the current directory.

        as_path_obj : bool
            Whether return type should be ::class:`Path` instead of ``str`` (``False`` by default).

        Returns
        -------
        Optional[Path, str, None]
            The project root directory, or ``None`` if the path is not within a Git repo or otherwise could not be
            determined.
        """
        if path is None:
            path = Path('.')
        try:
            git_repo = git.Repo(path, search_parent_directories=True)
            git_root: str = git_repo.git.rev_parse("--show-toplevel")
            return Path(git_root) if as_path_obj else git_root
        except:
            return None

    def setUp(self) -> None:
        proj_root = Path(self.find_project_root())
        test_data_dir = proj_root.joinpath('data', 'example_hydrofabric_1')

        self.subset_handler = SubsetHandlerImpl(catchment_data=test_data_dir.joinpath('catchment_data.geojson'),
                                                nexus_data=test_data_dir.joinpath('nexus_data.geojson'),
                                                cross_walk=test_data_dir.joinpath('crosswalk.json'))
        self.hydrofabric_list = list()
        for k in self.subset_handler._hydrofabric_graph:
            self.hydrofabric_list.append(self.subset_handler._hydrofabric_graph[k])

        self.subset_examples = list()
        ss = self.subset_handler.get_subset_for('cat-27')
        self.subset_examples.append(ss)

    def tearDown(self) -> None:
        pass

    # Simple test to make sure factory method (and __init__) work.
    def test_factory_create_from_base_and_hydrofabric_1_a(self):
        ex = 0
        hy_subset = SimpleHydrofabricSubset.factory_create_from_base_and_hydrofabric(self.subset_examples[ex],
                                                                                     self.hydrofabric_list)
        self.assertIsInstance(hy_subset, SimpleHydrofabricSubset)


