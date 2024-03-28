import os.path
import unittest

import pandas

from dmod.core.common.collections import catalog

from ...evaluations import specification
from ...evaluations.retrieval import Retriever
from ...evaluations import threshold
from ...evaluations.threshold import disk

from ..common import get_resource_path

TEST_CSV_PATH = str(get_resource_path("thresholds.csv"))
TEST_RDB_PATH = str(get_resource_path("nwis_stat_thresholds.rdb"))


class TestFrameRetrieving(unittest.TestCase):
    @classmethod
    def get_standard_retriever_config(cls) -> specification.ThresholdSpecification:
        return specification.ThresholdSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        format="csv",
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
                            weight=8,
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
                        format="rdb",
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
                            name="75th Percentile",
                            field="p75_va",
                            weight=10,
                            unit=specification.UnitDefinition(
                                    value="ft^3/s"
                            )
                    ),
                    specification.ThresholdDefinition(
                            name="80th Percentile",
                            field="p80_va",
                            weight=5,
                            unit=specification.UnitDefinition(
                                    value="ft^3/s"
                            )
                    ),
                    specification.ThresholdDefinition(
                            name="Median",
                            field="p50_va",
                            weight=1,
                            unit=specification.UnitDefinition(
                                    value="ft^3/s"
                            )
                    )
                ]
        )

    def setUp(self) -> None:
        self.__csv_threshold_specification = TestFrameRetrieving.get_standard_retriever_config()
        self.__rdb_threshold_specification = TestFrameRetrieving.get_rdb_retriever_config()

    def test_direct_rdb(self) -> None:
        retriever = threshold.disk.RDBThresholdRetriever(self.__rdb_threshold_specification, catalog.InputCatalog())
        self.run_rdb_assertions(self, retriever, self.__rdb_threshold_specification)

    def test_implicit_rdb(self) -> None:
        retriever = threshold.get_threshold_retriever(self.__rdb_threshold_specification, catalog.InputCatalog())
        self.run_rdb_assertions(self, retriever, self.__rdb_threshold_specification)

    def test_direct_csv(self):
        retriever = disk.CSVThresholdRetriever(self.__csv_threshold_specification, catalog.InputCatalog())
        self.run_csv_assertions(retriever)

    def test_implicit_csv(self):
        retriever = threshold.get_threshold_retriever(self.__csv_threshold_specification, catalog.InputCatalog())
        self.run_csv_assertions(retriever)

    @classmethod
    def run_rdb_assertions(
            cls,
            test_case: unittest.TestCase,
            retriever: Retriever,
            definition: specification.ThresholdSpecification
    ):
        test_case.assertIsInstance(retriever, threshold.disk.RDBThresholdRetriever)

        data: pandas.DataFrame = retriever.retrieve()

        test_case.assertEqual(sorted(list(data.keys())), ['name', 'site_no', 'value'])
        test_case.assertEqual(len(data.site_no.unique()), 2)
        test_case.assertEqual(len(data.index.unique()), 366)
        test_case.assertEqual(data.index.name, 'threshold_day')

        created_thresholds = threshold.get_thresholds(definition, catalog.InputCatalog())

        test_case.assertEqual(len(data.site_no.unique()), len(created_thresholds))

        for key, thresholds in created_thresholds.items():
            test_case.assertIn(key, data.site_no.unique())
            for threshold_name, _ in data[data.site_no == key].groupby('name'):
                matching_thresholds = [
                    thresh
                    for thresh in thresholds
                    if thresh.name == threshold_name
                ]
                test_case.assertEqual(len(matching_thresholds), 1)
                matching_threshold = matching_thresholds[0]
                test_case.assertIn(threshold_name, definition)
                threshold_definition = definition[threshold_name]
                test_case.assertEqual(threshold_definition.weight, matching_threshold.weight)

    def run_csv_assertions(self, retriever: Retriever):
        data = retriever.retrieve()

        threshold_categories = [
            {
                "location": "0214655255",
                "category": "flood",
                "value": 9320
            },
            {
                "location": "0214657975",
                "category": "flood",
                "value": 5440
            },
            {
                "location": "0214655255",
                "category": "action",
                "value": 6310
            },
            {
                "location": "0214657975",
                "category": "action",
                "value": 3730
            },
        ]

        self.assertEqual(len(data), len(threshold_categories))

        for category in threshold_categories:
            row = data[
                (data.location == category['location'])
                & (data.name == category['category'])
                & (data.value == data.value)
            ]
            self.assertEqual(len(row), 1)


if __name__ == '__main__':
    unittest.main()
