import os.path
import unittest

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pandas

from ...evaluations import specification
from ...evaluations import threshold
from ...evaluations.threshold import disk

TEST_CSV_PATH = os.path.join(os.path.dirname(__file__), "thresholds.csv")
TEST_RDB_PATH = os.path.join(os.path.dirname(__file__), "thresholds.rdb")


class TestFrameRetrieving(unittest.TestCase):
    @classmethod
    def get_standard_retriever_config(cls) -> specification.ThresholdSpecification:
        return specification.ThresholdSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        data_format="csv",
                        address=TEST_CSV_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="column",
                        pattern="location"
                ),
                definitions=[
                    specification.ThresholdDefinition(
                            name="name",
                            field="value",
                            weight="weight",
                            unit=specification.UnitDefinition(
                                    path="unit"
                            )
                    )
                ]
        )

    @classmethod
    def get_rdb_retriever_config(cls) -> specification.ThresholdSpecification:
        return specification.ThresholdSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        data_format="rdb",
                        address=TEST_RDB_PATH
                ),
                locations=specification.LocationSpecification(
                        identify=True,
                        from_field="column",
                        pattern="site_no"
                ),
                application_rules=specification.ThresholdApplicationRules(
                        threshold_field=specification.AssociatedField(
                                name="threshold_day",
                                path=["month_nu", "day_nu"],
                                datatype="day"
                        ),
                        observation_field=specification.AssociatedField(
                                name="threshold_day",
                                path=["value_date"],
                                datatype="day"
                        )
                ),
                definitions=[
                    specification.ThresholdDefinition(
                            name="p75_va",
                            field="p75_va",
                            weight=10,
                            unit=specification.UnitDefinition(
                                    path="unit"
                            )
                    )
                ]
        )

    def setUp(self) -> None:
        self.__csv_threshold_specification = TestFrameRetrieving.get_standard_retriever_config()
        self.__rdb_threshold_specification = TestFrameRetrieving.get_rdb_retriever_config()

    def test_direct_rdb(self) -> None:
        retriever = threshold.disk.RDBThresholdRetriever(self.__rdb_threshold_specification)
        self.run_rdb_assertions(self, retriever)

    def test_implicit_rdb(self) -> None:
        retriever = threshold.get_threshold_retriever(self.__rdb_threshold_specification)
        self.run_rdb_assertions(self, retriever)

    def test_direct_csv(self):
        retriever = disk.JSONThresholdRetriever(self.__csv_threshold_specification)
        self.run_csv_assertions(retriever)

    def test_implicit_csv(self):
        retriever = threshold.get_threshold_retriever(self.__csv_threshold_specification)
        self.run_csv_assertions(retriever)

    @classmethod
    def run_rdb_assertions(cls, test_case: unittest.TestCase, retriever: threshold.ThresholdRetriever):
        test_case.assertIsInstance(retriever, threshold.disk.RDBThresholdRetriever)

        data: pandas.DataFrame = retriever.get_data()

        test_case.assertEqual(sorted([column for column in data.keys()]), ['p75_va', 'site_no'])
        test_case.assertEqual(len(data.site_no.unique()), 2)
        test_case.assertEqual(len(data.index.unique()), 366)
        test_case.assertEqual(data.index.name, 'threshold_day')
        print("data loaded")

    def run_csv_assertions(self, retriever: threshold.ThresholdRetriever):
        data = retriever.get_data()

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

        for category in threshold_categories:
            row = data[
                (data.location == category['location'])
                & (data.weight == category['weight'])
                & (data.name == category['category'])
                & (data.value == data.value)
            ]
            self.assertEqual(len(row), 1)


if __name__ == '__main__':
    unittest.main()
