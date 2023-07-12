import os.path
import unittest

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pandas

from ...evaluations import specification
from ...evaluations import data_retriever
from ...evaluations.retrieval import Retriever
from ...evaluations.data_retriever import disk

from ..common import get_resource_path
from ..common import get_resource_directory

#TEST_FILE_PATH = os.path.join(os.path.dirname(__file__), "cat-\d\d.csv")
#TEST_OBSERVATION_PATH = os.path.join(os.path.dirname(__file__), "observations.csv")
TEST_FILE_PATH = os.path.join(get_resource_directory(), "cat-\d\d.csv")
TEST_OBSERVATION_PATH = str(get_resource_path("observations.csv"))


class TestCSVRetrieving(unittest.TestCase):
    @classmethod
    def create_multiple_specification(cls) -> specification.DataSourceSpecification:
        return specification.DataSourceSpecification(
                name="Predictions",
                value_field="prediction",
                unit=specification.UnitDefinition(
                        value="m3 s-1"
                ),
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="csv",
                        address=TEST_FILE_PATH,
                        parse_dates=["Time"]
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
                    ),
                    specification.FieldMappingSpecification(
                            field="prediction",
                            map_type="column",
                            value="Total Discharge"
                    ),
                    specification.FieldMappingSpecification(
                            field="value_date",
                            map_type="column",
                            value="Time"
                    )
                ],
                value_selectors=[
                    specification.ValueSelector(
                            name="Total Discharge",
                            where="column",
                            associated_fields=[
                                specification.AssociatedField(
                                        name="Time",
                                        datatype="datetime"
                                )
                            ]
                    )
                ]
        )

    @classmethod
    def create_single_data_specification(cls) -> specification.DataSourceSpecification:
        return specification.DataSourceSpecification(
                name="Observations",
                value_field="observation",
                unit=specification.UnitDefinition(
                        field="unit"
                ),
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="csv",
                        address=TEST_OBSERVATION_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="column",
                        pattern="observation_location"
                ),
                value_selectors=[
                    specification.ValueSelector(
                            name="observation",
                            where="column",
                            datatype="float",
                            associated_fields=[
                                specification.AssociatedField(
                                        name="value_date",
                                        datatype="datetime"
                                ),
                                specification.AssociatedField(
                                        name="unit",
                                        datatype="string"
                                ),
                                specification.AssociatedField(
                                        name="observation_location",
                                        datatype="string"
                                )
                            ]
                    )
                ]
        )

    def setUp(self) -> None:
        self.__multiple_specification = TestCSVRetrieving.create_multiple_specification()
        self.__single_data_specification = TestCSVRetrieving.create_single_data_specification()

    def test_uninstantiated_single_table(self):
        retriever = disk.FrameDataRetriever(self.__single_data_specification)
        TestCSVRetrieving.run_single_assertions(self, retriever)

    def test_direct_multiple_tables(self):
        retriever = disk.FrameDataRetriever(self.__multiple_specification)
        self.run_multiple_assertions(retriever)

    def test_implicit_multiple_tables(self):
        retriever = data_retriever.get_datasource_retriever(self.__multiple_specification)
        self.run_multiple_assertions(retriever)

    def test_direct_single_table(self):
        retriever = disk.FrameDataRetriever(self.__single_data_specification)
        TestCSVRetrieving.run_single_assertions(self, retriever)

    def test_implicit_single_table(self):
        retriever = data_retriever.get_datasource_retriever(self.__single_data_specification)
        TestCSVRetrieving.run_single_assertions(self, retriever)

    def run_multiple_assertions(self, retriever: Retriever):
        data = retriever.retrieve()

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

            for row_number, row in subset.iterrows():  # type: float, pandas.Series
                expected_offset_value_date = earliest_date + (time_offset * row_number)
                self.assertEqual(row.value_date, expected_offset_value_date)

    @classmethod
    def run_single_assertions(
            cls,
            test: unittest.TestCase,
            retriever: Retriever
    ):
        data = retriever.retrieve()

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

            while current_date <= latest_date.date():
                if current_date not in present_days:
                    missing_days.append(current_date)
                else:
                    missing_days.clear()

                test.assertLess(len(missing_days), 5)

                current_date += timedelta(days=1)


if __name__ == '__main__':
    unittest.main()
