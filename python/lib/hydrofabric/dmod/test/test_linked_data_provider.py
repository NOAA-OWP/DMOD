import unittest

from . import hydrofabric_fixture, TESTING_DATA
from ..hydrofabric.linked_data_provider import GPKGLinkedDataProvider
from ..hydrofabric.linked_data_provider_factory import LinkedDataProviderFactory


class TestGPKGLinkedDataProvider(unittest.TestCase):
    def test_catchment_ids(self):
        with hydrofabric_fixture() as connection:
            o = GPKGLinkedDataProvider(connection=connection)
            self.assertListEqual(o.catchment_ids(), ["cat-10", "cat-1"])

    def test_factory_init(self):
        o = LinkedDataProviderFactory.factory_create(TESTING_DATA)
        self.assertIsInstance(o, GPKGLinkedDataProvider)

    def test_get_data(self):
        with hydrofabric_fixture() as connection:
            o = GPKGLinkedDataProvider(connection=connection)
            self.assertDictEqual(
                o.get_data("cat-1"),
                {
                    "cfe_noahowp_attributes": {
                        "fid": 1,
                        "id": "cat-1",
                        "gw_Coeff": None,
                        "gw_Zmax": None,
                        "gw_Expon": None,
                        "ISLTYP": 4,
                        "IVGTYP": 15,
                        "bexp_soil_layers_stag=1": 6.560212135314941,
                        "bexp_soil_layers_stag=2": 6.560212135314941,
                        "bexp_soil_layers_stag=3": 6.560212135314941,
                        "bexp_soil_layers_stag=4": 6.560212135314941,
                        "dksat_soil_layers_stag=1": 2.56973640193614e-05,
                        "dksat_soil_layers_stag=2": 2.56973640193614e-05,
                        "dksat_soil_layers_stag=3": 2.56973640193614e-05,
                        "dksat_soil_layers_stag=4": 2.56973640193614e-05,
                        "psisat_soil_layers_stag=1": 1.7560320090189956,
                        "psisat_soil_layers_stag=2": 1.7560320090189956,
                        "psisat_soil_layers_stag=3": 1.7560320090189956,
                        "psisat_soil_layers_stag=4": 1.7560320090189956,
                        "cwpvt": 0.3373601788974299,
                        "mfsno": 0.5974573737852061,
                        "mp": 9.04498447407026,
                        "refkdt": 3.191537152793719,
                        "slope": 0.05248423024313845,
                        "smcmax_soil_layers_stag=1": 0.6121046102701159,
                        "smcmax_soil_layers_stag=2": 0.6121046102701159,
                        "smcmax_soil_layers_stag=3": 0.6121046102701159,
                        "smcmax_soil_layers_stag=4": 0.6121046102701159,
                        "smcwlt_soil_layers_stag=1": 0.06185167143346698,
                        "smcwlt_soil_layers_stag=2": 0.06185167143346698,
                        "smcwlt_soil_layers_stag=3": 0.06185167143346698,
                        "smcwlt_soil_layers_stag=4": 0.06185167143346698,
                        "vcmx25": 45.39522123675415,
                    },
                    "forcing_metadata": {
                        "fid": 2,
                        "id": "cat-1",
                        "areasqkm": 4.077900667941928,
                        "cetroid_lon": -69.91710215109363,
                        "centroid_lat": 46.73093067499626,
                        "elevation": 399.56972483704885,
                        "slope_m_km": 7.832009740147621,
                        "aspect": 85.66323418358553,
                    },
                },
            )
