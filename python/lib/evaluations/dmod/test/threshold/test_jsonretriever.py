import os.path
import unittest

from ...evaluations import specification
from ...evaluations import threshold
from ...evaluations.threshold import disk
from ...evaluations.retrieval import Retriever

from ..common import get_resource_path

TEST_DOCUMENT_PATH = str(get_resource_path("thresholds.json"))


class TestJSONRetrieving(unittest.TestCase):
    @classmethod
    def get_retriever_config(cls) -> specification.ThresholdSpecification:
        return specification.ThresholdSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="json",
                        address=TEST_DOCUMENT_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="value",
                        pattern="metadata/usgs_site_code"
                ),
                origin="$.value_set[?(@.calc_flow_values.rating_curve.id_type == 'NWS Station')]",
                definitions=[
                    specification.ThresholdDefinition(
                            name="action",
                            field="calc_flow_values/action",
                            weight=10,
                            unit=specification.UnitDefinition(
                                    path="metadata/calc_flow_units"
                            )
                    ),
                    specification.ThresholdDefinition(
                            name="flood",
                            field="calc_flow_values/flood",
                            weight=8,
                            unit=specification.UnitDefinition(
                                    path="metadata/calc_flow_units"
                            )
                    )
                ]
        )

    def setUp(self) -> None:
        self.__threshold_specification = TestJSONRetrieving.get_retriever_config()

    def test_direct_json(self):
        retriever = disk.JSONThresholdRetriever(self.__threshold_specification)
        self.run_assertions(retriever)

    def test_implicit_json(self):
        retriever = threshold.get_threshold_retriever(self.__threshold_specification)
        self.run_assertions(retriever)

    def run_assertions(self, retriever: Retriever):
        data = retriever.retrieve()

        threshold_categories = [
            {
                "location": "0214655255",
                "weight": 8,
                "category": "flood",
                "value": 9320
            },
            {
                "location": "0214657975",
                "weight": 8,
                "category": "flood",
                "value": 5440
            },
            {
                "location": "0214655255",
                "weight": 10,
                "category": "action",
                "value": 6310
            },
            {
                "location": "0214657975",
                "weight": 10,
                "category": "action",
                "value": 3730
            },
        ]

        self.assertEqual(len(data), len(threshold_categories))

        location_column_name = retriever.definition.locations.pattern[-1]

        for category in threshold_categories:
            row = data[
                (data[location_column_name] == category['location'])
                & (data.weight == category['weight'])
                & (data.name == category['category'])
                & (data.value == data.value)
            ]
            self.assertEqual(len(row), 1)


if __name__ == '__main__':
    unittest.main()
