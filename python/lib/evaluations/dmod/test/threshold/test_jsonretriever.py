import os.path
import unittest

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from ...evaluations import specification
from ...evaluations import threshold
from ...evaluations.threshold import disk

TEST_DOCUMENT_PATH = os.path.join(os.path.dirname(__file__), "thresholds.json")


class TestJSONRetrieving(unittest.TestCase):
    def setUp(self) -> None:
        self.__threshold_specification = specification.ThresholdSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        data_format="json",
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

    def test_direct_table_json(self):
        retriever = disk.JSONThresholdRetriever(self.__threshold_specification)
        self.run_table_assertions(retriever)

    def test_implicit_table_json(self):
        retriever = threshold.get_thresholds(self.__threshold_specification)
        self.run_table_assertions(retriever)

    def run_table_assertions(self, retriever: threshold.ThresholdRetriever):
        data = retriever.get_data()

        locations = ("cat-52", "cat-27")

        for location in locations:
            self.assertIn(location, data.prediction_location.values)

        initial_date = datetime(year=2015, month=12, day=1, tzinfo=timezone.utc)
        earliest_date = data.value_date.min()
        self.assertEqual(initial_date, earliest_date)

        value_per_location = 720
        time_offset = timedelta(hours=1)

        for location_name, subset in data.groupby(by="prediction_location"):
            self.assertEqual(subset.value_date.min(), earliest_date)
            self.assertEqual(len(subset), value_per_location)

            for row_number, row in subset.iterrows():
                expected_offset_value_date = earliest_date + (time_offset * row_number)
                self.assertEqual(row.value_date, expected_offset_value_date)


if __name__ == '__main__':
    unittest.main()
