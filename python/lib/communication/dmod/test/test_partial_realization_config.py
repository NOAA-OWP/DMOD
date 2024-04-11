from git import Repo
import unittest
from ..communication.maas_request.ngen.partial_realization_config import PartialRealizationConfig
from ngen.config.realization import NgenRealization
from typing import Any, Dict, List, Mapping, Optional
from pathlib import Path


@unittest.skip("Skipping for dependency issue; see DMOD Github issue #317")
class TestPartialRealizationConfig(unittest.TestCase):

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
        return Path(Repo(path, search_parent_directories=True).git.rev_parse("--show-toplevel"))

    @classmethod
    def read_example_realization_config_sources(cls) -> List[NgenRealization]:
        """
        Find and read realization configs on which to base test examples, sourcing data from actual files.

        At present, two example configs are loaded from files within ``<proj_root>/data/example_realization_configs/``.

        The config in ``ex_realization_config_01.json`` has only a global formulation config, uses CSV per-feature
        forcings, and does not have routing configured.

        The config in ``ex_realization_config_02.json`` has a global formulation config, multiple individual catchment
        formulation configs, uses NetCDF forcings, and does have routing configured.

        Returns
        -------
        List[NgenRealization]
            A list of example realization config objects read from files in the local repo tree.
        """
        config_files_dir = cls.find_project_root() / "data" / "example_realization_configs"
        if not config_files_dir.is_dir():
            msg = "Expected dir with example realization configs for {} setup not found at {}"
            raise RuntimeError(msg.format(cls.__name__, config_files_dir))

        # See docstring for the basic makeup of each of the contained configs
        files = ["ex_realization_config_01.json", "ex_realization_config_02.json"]

        return [NgenRealization.parse_file(config_files_dir.joinpath(f)) for f in files]

    def setUp(self) -> None:
        # Base examples on data sourced from some actual realization config files; start by reading those
        # Note that, unlike some other things, there may not be one of these for every test example
        self._base_real_configs: List[NgenRealization] = self.read_example_realization_config_sources()

        # Just using ``Any`` type in place of specific types from ngen-config right now
        # The types used may change, and this is simpler
        # But want to capture the outer layers of type hints to make sure testing setup stays sane
        self.ex_hf_uids: Dict[int, str] = dict()
        self.ex_global_form_data: Dict[int, List[Any]] = dict()
        self.ex_cat_forms_data: Dict[int, Mapping[str, Any]] = dict()
        self.ex_forcing_patterns: Dict[int, str] = dict()
        self.ex_forcing_names: Dict[int, str] = dict()
        self.ex_routing_configs: Dict[int, Any] = dict()

        #self.ex_data: List[Dict[str, Any]] = list()
        self.ex_objs: List[PartialRealizationConfig] = list()

        # Example 0: based directly on applicable parts of the first (index 0) loaded example realization config
        # This will mean global formulations: yes; per-catchment formulations: no; routing: no
        # It also will not include any of the forcing properties, and explicitly sets is_env_workaround to False
        indx = 0
        self.ex_hf_uids[indx] = '0000'
        self.ex_global_form_data[indx] = list(self._base_real_configs[0].global_config.formulations)
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     is_env_workaround=False))

        # Example 1: based directly on applicable parts of the second (index 1) loaded example realization config
        # This will mean global formulations: yes; per-catchment formulations: yes; routing: yes
        # It also will not include any of the forcing properties
        indx = 1
        self.ex_hf_uids[indx] = '0001'
        self.ex_global_form_data[indx] = list(self._base_real_configs[1].global_config.formulations)
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx]))

        # Example 2: like example 1, but with forcing_file_pattern set up to indicate the env workaround
        indx = 2
        self.ex_hf_uids[indx] = '0002'
        self.ex_global_form_data[indx] = list(self._base_real_configs[1].global_config.formulations)
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_forcing_patterns[indx] = ".*{{id}}.*..csv"
        pattern_param = "from_env:::" + self.ex_forcing_patterns[indx]
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx],
                                                     forcing_file_pattern=pattern_param))

        # Example 3: like example 2, but with forcing_file_name set up to indicate the env workaround
        indx = 3
        self.ex_hf_uids[indx] = '0003'
        self.ex_global_form_data[indx] = list(self._base_real_configs[1].global_config.formulations)
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_forcing_names[indx] = "./data/forcing/cats-27_52_67-2015_12_01-2015_12_30.nc"
        name_param = "from_env:::" + self.ex_forcing_names[indx]
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx],
                                                     forcing_file_name=name_param))

        # Example 4: like example 1, but without the global formulation config, to make sure just catchment formulations
        # is valid; and with is_env_workaround explicitly set to ``True``
        indx = 4
        self.ex_hf_uids[indx] = '0004'
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx],
                                                     is_env_workaround=True))

        # Example 5: like example 2, but with is_env_workaround explicitly set
        # to ``None``. is_env_workaround should coerce to ``True``.
        indx = 2
        self.ex_hf_uids[indx] = '0005'
        self.ex_global_form_data[indx] = list(self._base_real_configs[1].global_config.formulations)
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_forcing_patterns[indx] = ".*{{id}}.*..csv"
        pattern_param = "from_env:::" + self.ex_forcing_patterns[indx]
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx],
                                                     forcing_file_pattern=pattern_param,
                                                     is_env_workaround=None))

        # Example 6: like example 1, but with is_env_workaround explitly set to
        # ``None``. is_env_workaround should coerce to ``False``.
        indx = 1
        self.ex_hf_uids[indx] = '0001'
        self.ex_global_form_data[indx] = list(self._base_real_configs[1].global_config.formulations)
        self.ex_cat_forms_data[indx] = self._base_real_configs[1].catchments
        self.ex_routing_configs[indx] = self._base_real_configs[1].routing
        self.ex_objs.append(PartialRealizationConfig(hydrofabric_uid=self.ex_hf_uids[indx],
                                                     global_formulations=self.ex_global_form_data[indx],
                                                     catchment_formulations=self.ex_cat_forms_data[indx],
                                                     routing_config=self.ex_routing_configs[indx],
                                                     is_env_workaround=None))

    def test_catchment_formulations_0_a(self):
        """
        Test for expected catchment formulations in a case with only global formulations set.
        """
        ex_idx = 0
        obj = self.ex_objs[ex_idx]
        self.assertIsNone(obj.catchment_formulations)

    def test_catchment_formulations_1_a(self):
        """
        Test for expected catchment formulations in a case with a value set.
        """
        ex_idx = 1
        obj = self.ex_objs[ex_idx]
        self.assertEqual(obj.catchment_formulations, self.ex_cat_forms_data[ex_idx])

    def test_global_formulations_0_a(self):
        """
        Test for expected global formulations in a case with this set to non-``None`` value.
        """
        ex_idx = 1
        obj = self.ex_objs[ex_idx]
        expected = self.ex_global_form_data[ex_idx]
        self.assertEqual(obj.global_formulations, expected)

    def test_global_formulations_4_a(self):
        """
        Test for expected global formulations in a case with only catchment formulations set; i.e., ``None``.
        """
        ex_idx = 4
        obj = self.ex_objs[ex_idx]
        self.assertIsNone(obj.global_formulations)

    def test_global_formulations_4_b(self):
        """
        Test validation that one of global or catchment formulation must be provided on new object based on example 4.
        """
        ex_idx = 4
        obj = self.ex_objs[ex_idx]
        with self.assertRaises(ValueError):
            PartialRealizationConfig(hydrofabric_uid=obj.hydrofabric_uid, routing_config=obj.routing_config)

    def test_hydrofabric_uid_0_a(self):
        ex_idx = 0
        obj = self.ex_objs[ex_idx]
        expected_hydrofabric_uid = self.ex_hf_uids[ex_idx]
        self.assertEqual(obj.hydrofabric_uid, expected_hydrofabric_uid)

    def test_hydrofabric_uid_1_a(self):
        ex_idx = 1
        obj = self.ex_objs[ex_idx]
        expected_hydrofabric_uid = self.ex_hf_uids[ex_idx]
        self.assertEqual(obj.hydrofabric_uid, expected_hydrofabric_uid)

    def test_is_env_workaround_0_a(self):
        """
        Test for expected value in a case with this explicitly initialized to ``False``.
        """
        ex_idx = 0
        obj = self.ex_objs[ex_idx]
        self.assertFalse(obj.is_env_workaround)

    def test_is_env_workaround_1_a(self):
        """
        Test for expected value in a case with this not explicitly initialized.
        """
        ex_idx = 1
        obj = self.ex_objs[ex_idx]
        self.assertFalse(obj.is_env_workaround)

    def test_is_env_workaround_2_a(self):
        """
        Test for expected value in a case with this implicitly ``True`` due to the ``forcing_file_pattern`` value.
        """
        ex_idx = 2
        obj = self.ex_objs[ex_idx]
        self.assertIsNone(obj.forcing_file_name)
        self.assertTrue(obj.is_env_workaround)

    def test_is_env_workaround_3_a(self):
        """
        Test for expected value in a case with this implicitly ``True`` due to the ``forcing_file_name`` value.
        """
        ex_idx = 3
        obj = self.ex_objs[ex_idx]
        self.assertIsNone(obj.forcing_file_pattern)
        self.assertTrue(obj.is_env_workaround)

    def test_is_env_workaround_4_a(self):
        """
        Test for expected value in a case with this explicitly initialized to ``True``.
        """
        ex_idx = 4
        obj = self.ex_objs[ex_idx]
        self.assertTrue(obj.is_env_workaround)

    def test_is_env_workaround_5_a(self):
        """
        Test for expected value in a case with this explicitly initialized to ``None``.
        """
        ex_idx = 5
        obj = self.ex_objs[ex_idx]
        self.assertTrue(obj.is_env_workaround)

    def test_is_env_workaround_6_a(self):
        """
        Test for expected value in a case with this explicitly initialized to ``None``.
        """
        ex_idx = 6
        obj = self.ex_objs[ex_idx]
        self.assertFalse(obj.is_env_workaround)
