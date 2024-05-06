import unittest
import pandas as pd
import geopandas as gpd

from pathlib import Path
from ..modeldata.data.bmi_init_config_auto_generator import BmiInitConfigAutoGenerator, NgenRealization
from typing import Dict
from ngen.init_config.serializer_deserializer import (IniSerializerDeserializer, JsonSerializerDeserializer,
                                                      NamelistSerializerDeserializer, YamlSerializerDeserializer)


@unittest.skip
class TestBmiInitConfigAutoGenerator(unittest.TestCase):

    @staticmethod
    def _remove_dir(dir_path: Path):
        for p in dir_path.iterdir():
            if p.is_dir():
                TestBmiInitConfigAutoGenerator._remove_dir(p)
            else:
                p.unlink()
        dir_path.rmdir()

    @staticmethod
    def _prep_output_dir(output_dir: Path):
        if output_dir.is_dir():
            TestBmiInitConfigAutoGenerator._remove_dir(output_dir)
            output_dir.mkdir()
        elif not output_dir.exists():
            output_dir.mkdir()
        else:
            raise RuntimeError(f"Test output directory path {output_dir} is existing non-directory")

    def setUp(self):
        self.generators: Dict[int, BmiInitConfigAutoGenerator] = dict()
        self.output_dirs: Dict[int, Path] = dict()

        # TODO: (later) find a better way to do this
        hf_gpkg = Path.home().joinpath("Developer/noaa/data/hydrofabric/v201/nextgen_01.gpkg")
        hf_model_data = Path.home().joinpath("Developer/noaa/data/hydrofabric/v201/nextgen_01.parquet")
        real_cfg_file = Path.home().joinpath(
            "Developer/noaa/dmod/data/example_realization_configs/ex_realization_config_03.json")
        noah_params_dir = Path.home().joinpath("Developer/noaa/data/noah_owp_ex_params_dir_1")

        self.output_dirs[0] = hf_model_data.parent.joinpath(f"{self.__class__.__name__}_out_0")
        self._prep_output_dir(self.output_dirs[0])
        self.generators[0] = BmiInitConfigAutoGenerator(ngen_realization=NgenRealization.parse_file(real_cfg_file),
                                                        hydrofabric_data=gpd.read_file(hf_gpkg, layer="divides"),
                                                        hydrofabric_model_attributes=pd.read_parquet(hf_model_data),
                                                        noah_owp_params_dir=noah_params_dir)

    # TODO: (later) reactivate these after finding a way to do this well automatically
    @unittest.skip
    def test__get_module_builder_types_for_catchment_0_a(self):
        ex_idx = 0
        generator = self.generators[ex_idx]

        result = generator._get_module_builder_types_for_catchment('cat-1')
        self.assertEqual(len(result), 3)

    @unittest.skip
    def test_generate_configs_0_a(self):
        ex_idx = 0
        generator = self.generators[ex_idx]

        gen_pyobj = generator.generate_configs()

        configs = []
        cat_id, config = next(gen_pyobj)
        configs.append(config)
        while True:
            cid, config = next(gen_pyobj)
            if cid == cat_id:
                configs.append(config)
            else:
                break
        self.assertEqual(3, len(configs))

    @unittest.skip
    def test_generate_configs_0_b(self):
        ex_idx = 0
        generator = self.generators[ex_idx]

        gen_pyobj = generator.generate_configs()

        configs = []
        cat_id, config = next(gen_pyobj)
        configs.append(config)
        while True:
            cid, config = next(gen_pyobj)
            if cid == cat_id:
                configs.append(config)
            else:
                break
        for cfg in configs:
            self.assertTrue(isinstance(cfg, (IniSerializerDeserializer, JsonSerializerDeserializer,
                                             NamelistSerializerDeserializer, YamlSerializerDeserializer)))

    @unittest.skip
    def test_write_configs_0_a(self):
        ex_idx = 0
        generator = self.generators[ex_idx]

        generator.write_configs(self.output_dirs[ex_idx])
        # TODO: (later) fully implement a way to automatically test this