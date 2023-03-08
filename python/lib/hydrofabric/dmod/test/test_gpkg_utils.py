import unittest
from . import hydrofabric_fixture

from ..hydrofabric.gpkg_utils import table_info, attribute_table_names


class TestGPKGUtils(unittest.TestCase):
    def test_table_info(self):
        with hydrofabric_fixture() as connection:
            info = table_info("nexus", connection)
            self.assertListEqual(
                [field.name for field in info], ["fid", "geom", "id", "type", "toid"]
            )

    def test_attribute_table_names(self):
        with hydrofabric_fixture() as connection:
            names = attribute_table_names(connection)
            self.assertEqual(
                names,
                [
                    "cfe_noahowp_attributes",
                    "crosswalk",
                    "flowpath_attributes",
                    "flowpath_edge_list",
                    "forcing_metadata",
                ],
            )
