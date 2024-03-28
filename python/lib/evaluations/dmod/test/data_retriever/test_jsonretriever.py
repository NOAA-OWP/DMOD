import os.path
import unittest

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pandas

from dmod.core.common.collections import catalog

from ...evaluations import specification
from ...evaluations.retrieval import Retriever
from ...evaluations import data_retriever
from ...evaluations.data_retriever import disk

from ..common import get_resource_path
from ..common import get_resource_directory

TEST_FILE_PATH = str(os.path.join(get_resource_directory(), "cat-\d\d.json"))
TEST_RESPONSE_PATH = str(get_resource_path("2015_observations.json"))


class TestJSONRetrieving(unittest.TestCase):
    @classmethod
    def get_prediction_specification(cls) -> specification.DataSourceSpecification:
        return specification.DataSourceSpecification(
                name="Predictions",
                value_field="prediction",
                unit=specification.UnitDefinition(
                        value="CMS"
                ),
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="json",
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

    @classmethod
    def get_observation_specification(cls) -> specification.DataSourceSpecification:
        return specification.DataSourceSpecification(
                name="Observations",
                value_field="observation",
                unit=specification.UnitDefinition(
                        field="unit"
                ),
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="json",
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

    def setUp(self) -> None:
        self.__table_data_specification = TestJSONRetrieving.get_prediction_specification()
        self.__response_data_specification = TestJSONRetrieving.get_observation_specification()

    def test_direct_table_json(self):
        retriever = disk.JSONDataRetriever(
            self.__table_data_specification,
            input_catalog=catalog.InputCatalog()
        )
        self.run_table_assertions(retriever)

    def test_implicit_table_json(self):
        retriever = data_retriever.get_datasource_retriever(
            self.__table_data_specification,
            input_catalog=catalog.InputCatalog()
        )
        self.run_table_assertions(retriever)

    def test_direct_response_json(self):
        retriever = disk.JSONDataRetriever(self.__response_data_specification, input_catalog=catalog.InputCatalog())
        TestJSONRetrieving.run_response_assertions(self, retriever)

    def test_implicit_response_json(self):
        retriever = data_retriever.get_datasource_retriever(
            self.__response_data_specification,
            input_catalog=catalog.InputCatalog()
        )
        TestJSONRetrieving.run_response_assertions(self, retriever)

    def run_table_assertions(self, retriever: Retriever):
        data = retriever.retrieve()

        locations = ("cat-52", "cat-27")

        for location in locations:
            self.assertIn(location, data.prediction_location.values)

        initial_date = datetime(year=2015, month=12, day=1, tzinfo=timezone.utc)
        earliest_date = data.value_date.min()
        self.assertEqual(initial_date, earliest_date)

        value_per_location = 720
        time_offset = timedelta(hours=1)

        for _, subset in data.groupby(by="prediction_location"):
            self.assertEqual(subset.value_date.min(), earliest_date)
            self.assertEqual(len(subset), value_per_location)

            for row_number, row in subset.iterrows():  # type: float, pandas.Series
                expected_offset_value_date = earliest_date + (time_offset * row_number)
                self.assertEqual(row.value_date, expected_offset_value_date)

    @classmethod
    def run_response_assertions(
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

        for _, subset in data.groupby(by="observation_location"):
            test.assertGreater(subset.value_date.min(), earliest_possible_date)
            test.assertLess(subset.value_date.max(), latest_possible_date)

            current_date = earliest_date.date()
            present_days = subset.value_date.apply(lambda d: d.date()).unique()
            missing_days = []

            while current_date <= latest_date.date():
                if current_date not in present_days:
                    missing_days.append(current_date)
                else:
                    missing_days.clear()

                test.assertLess(len(missing_days), 5)

                current_date += timedelta(days=1)


if __name__ == '__main__':
    unittest.main()
