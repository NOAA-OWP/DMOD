import git
import unittest
from hypy import Catchment
from pathlib import Path
from typing import Dict, Optional, Union
from ..modeldata.subset import SubsetHandler
from ..modeldata.subset.subset_handler import GeoJsonBackedSubsetHandler


class TestSubsetHandler(unittest.TestCase):

    CAT_KEY = 'catchment_geojson_file'
    FLOW_KEY = 'flowpath_geojson_file'
    NEX_KEY = 'nexus_geojson_file'
    CROSS_KEY = 'crosswalk_json_file'

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
        data_dir = self.find_project_root(as_path_obj=True).joinpath('data')
        ex_1_dir = data_dir.joinpath('example_hydrofabric_1')

        self.hf_examples = dict()

        ex_1: Dict[str, Path] = dict()
        ex_1[self.CAT_KEY] = ex_1_dir.joinpath('catchment_data.geojson')
        ex_1[self.FLOW_KEY] = ex_1_dir.joinpath('flowpath_data.geojson')
        ex_1[self.NEX_KEY] = ex_1_dir.joinpath('nexus_data.geojson')
        ex_1[self.CROSS_KEY] = ex_1_dir.joinpath('crosswalk.json')

        self.hf_examples[1] = ex_1

        # Validate that everything expected exists
        for example_key in self.hf_examples:
            example = self.hf_examples[example_key]
            for k in example:
                if not example[k].exists() or not example[k].is_file():
                    raise RuntimeError('Invalid example {} hydrofabric files for {}'.format(str(example_key),
                                                                                            self.__class__.__name__))

    def tearDown(self) -> None:
        pass

    # Test that the function can initialize a new subset handler via the GeoJSON factory method
    def test_geojson_init_1_a(self):
        ex_ind = 1
        cf = str(self.hf_examples[ex_ind][self.CAT_KEY])
        nf = str(self.hf_examples[ex_ind][self.NEX_KEY])
        xf = str(self.hf_examples[ex_ind][self.CROSS_KEY])

        handler = GeoJsonBackedSubsetHandler(catchment_data=cf, nexus_data=nf, cross_walk=xf)
        self.assertIsInstance(handler, SubsetHandler)

    # Test that catchment can be retrieved by id
    def test_get_catchment_by_id_1_a(self):
        ex_ind = 1
        cf = str(self.hf_examples[ex_ind][self.CAT_KEY])
        nf = str(self.hf_examples[ex_ind][self.NEX_KEY])
        xf = str(self.hf_examples[ex_ind][self.CROSS_KEY])

        ex_cat_id = 'cat-67'

        handler = GeoJsonBackedSubsetHandler(catchment_data=cf, nexus_data=nf, cross_walk=xf)
        catchment = handler.get_catchment_by_id(ex_cat_id)

        self.assertIsInstance(catchment, Catchment)

    # Test that expected catchment can be retrieved by id
    def test_get_catchment_by_id_1_b(self):
        ex_ind = 1
        cf = str(self.hf_examples[ex_ind][self.CAT_KEY])
        nf = str(self.hf_examples[ex_ind][self.NEX_KEY])
        xf = str(self.hf_examples[ex_ind][self.CROSS_KEY])

        ex_cat_id = 'cat-67'

        handler = GeoJsonBackedSubsetHandler(catchment_data=cf, nexus_data=nf, cross_walk=xf)
        catchment = handler.get_catchment_by_id(ex_cat_id)

        self.assertEqual(catchment.id, ex_cat_id)

    # Test that catchment can be retrieved by id
    def test_get_catchment_by_id_2_a(self):
        ex_ind = 1
        cf = str(self.hf_examples[ex_ind][self.CAT_KEY])
        nf = str(self.hf_examples[ex_ind][self.NEX_KEY])
        xf = str(self.hf_examples[ex_ind][self.CROSS_KEY])

        ex_cat_id = 'cat-27'

        handler = GeoJsonBackedSubsetHandler(catchment_data=cf, nexus_data=nf, cross_walk=xf)
        catchment = handler.get_catchment_by_id(ex_cat_id)

        self.assertIsInstance(catchment, Catchment)

    # Test that expected catchment can be retrieved by id
    def test_get_catchment_by_id_2_b(self):
        ex_ind = 1
        cf = str(self.hf_examples[ex_ind][self.CAT_KEY])
        nf = str(self.hf_examples[ex_ind][self.NEX_KEY])
        xf = str(self.hf_examples[ex_ind][self.CROSS_KEY])

        ex_cat_id = 'cat-27'

        handler = GeoJsonBackedSubsetHandler(catchment_data=cf, nexus_data=nf, cross_walk=xf)
        catchment = handler.get_catchment_by_id(ex_cat_id)

        self.assertEqual(catchment.id, ex_cat_id)
