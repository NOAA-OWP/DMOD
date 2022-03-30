import os.path
import unittest

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from ...evaluations import specification
from ...evaluations import data_retriever
from ...evaluations.data_retriever import disk

TEST_FILE_PATH = os.path.join(os.path.dirname(__file__), "cat-\d\d.json")
TEST_RESPONSE_PATH = os.path.join(os.path.dirname(__file__), "observations.json")


class TestJSONRetrieving(unittest.TestCase):
    def setUp(self) -> None:
        self.__table_data_specification = specification.DataSourceSpecification(
                name="Predictions",
                backend=specification.BackendSpecification(
                        backend_type="file",
                        data_format="json",
                        address=TEST_FILE_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="filename",
                        pattern="cat-\d\d"
                ),
                field_mapping=[
                    specification.FieldMappingSpecification(
                            field="prediction_location",
                            map_type="column",
                            value="location"
                    )
                ],
                value_selectors=[
                    specification.ValueSelector(
                            name="prediction",
                            where="value",
                            path="'Total Discharge'.*",
                            origin="$",
                            associated_fields=[
                                specification.AssociatedField(
                                        name="value_date",
                                        path="Time.*",
                                        datatype="datetime"
                                )
                            ]
                    )
                ]
        )
        self.__response_data_specification = specification.DataSourceSpecification(
                name="Observations",
                backend=specification.BackendSpecification(
                        backend_type="file",
                        data_format="json",
                        address=TEST_RESPONSE_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="value"
                ),
                value_selectors=[
                    specification.ValueSelector(
                            name="observation",
                            where="value",
                            path=["values[*]", "value[*]", "value"],
                            datatype="float",
                            origin=["$", "value", "timeSeries[*]"],
                            associated_fields=[
                                specification.AssociatedField(
                                        name="value_date",
                                        path=["values[*]", "value[*]", "dateTime"],
                                        datatype="datetime"
                                ),
                                specification.AssociatedField(
                                        name="observation_location",
                                        path=["sourceInfo", "siteCode", "[0]", "value"],
                                        datatype="string"
                                ),
                                specification.AssociatedField(
                                        name="unit",
                                        path=["variable", "unit", "unitCode"],
                                        datatype="string"
                                )
                            ]
                    )
                ]
        )

    def test_direct_table_json(self):
        retriever = disk.JSONDataRetriever(self.__table_data_specification)
        self.run_table_assertions(retriever)

    def test_implicit_table_json(self):
        retriever = data_retriever.get_datasource(self.__table_data_specification)
        self.run_table_assertions(retriever)

    def test_direct_response_json(self):
        retriever = disk.JSONDataRetriever(self.__response_data_specification)
        TestJSONRetrieving.run_response_assertions(self, retriever)

    def test_implicit_response_json(self):
        retriever = data_retriever.get_datasource(self.__response_data_specification)
        TestJSONRetrieving.run_response_assertions(self, retriever)

    def run_table_assertions(self, retriever: data_retriever.DataRetriever):
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

    @classmethod
    def run_response_assertions(
            cls,
            test: unittest.TestCase,
            retriever: data_retriever.DataRetriever
    ):
        data = retriever.get_data()

        expected_locations = ("0214655255", "0214657975")

        unique_loaded_locations = data.observation_location.unique()

        for location in expected_locations:
            test.assertIn(location, unique_loaded_locations)

        earliest_possible_date = datetime(year=2015, month=12, day=1, tzinfo=timezone.utc)
        latest_possible_date = datetime(year=2016, month=1, day=2, tzinfo=timezone.utc)
        earliest_date = data.value_date.min()
        latest_date = data.value_date.max()
        test.assertGreater(earliest_date, earliest_possible_date)
        test.assertLess(latest_date, latest_possible_date)

        for location_name, subset in data.groupby(by="observation_location"):
            test.assertGreater(subset.value_date.min(), earliest_possible_date)
            test.assertLess(subset.value_date.max(), latest_possible_date)

            current_date = earliest_date.date()
            present_days = subset.value_date.apply(lambda d: d.date()).unique()
            missing_days = list()

            while current_date <= latest_date:
                if current_date not in present_days:
                    missing_days.append(current_date)
                else:
                    missing_days.clear()

                test.assertLess(len(missing_days), 5)

                current_date += timedelta(days=1)

        print("data retrieved")


if __name__ == '__main__':
    unittest.main()
