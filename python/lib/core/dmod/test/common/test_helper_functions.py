"""
Provides unit tests for functions that originated within the 'helper_functions' module
"""
import unittest
from ...core.common import merge_dictionaries
from ...core.common.merge import ConflictStrategy

BOTTOM_HALF = {
    "thresholds": [
        {
            "name": "NWIS Stat Percentiles",
            "backend": {
                "name": "NWIS Stat Thresholds",
                "backend_type": "file",
                "data_format": "rdb",
                "address": "resources/nwis_stat_thresholds.rdb"
            },
            "locations": {
                "identify": True,
                "from_field": "column",
                "pattern": "site_no"
            },
            "application_rules": {
                "name": "Date to Day",
                "threshold_field": {
                    "name": "threshold_day",
                    "path": [
                        "month_nu",
                        "day_nu"
                    ],
                    "datatype": "Day"
                },
                "observation_field": {
                    "name": "threshold_day",
                    "path": [
                        "value_date"
                    ],
                    "datatype": "Day"
                }
            },
            "definitions": [
                {
                    "name": "75th Percentile",
                    "field": "p75_va",
                    "weight": 10,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "80th Percentile",
                    "field": "p80_va",
                    "weight": 5,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "Median",
                    "field": "p50_va",
                    "weight": 1,
                    "unit": {
                        "value": "ft^3/s"
                    }
                }
            ]
        }
    ],
    "scheme": {
        "name": "Prefer Pearson, then Nash and Kling, then POD and FAR",
        "metrics": [
            {
                "name": "False Alarm Ratio",
                "weight": 10
            },
            {
                "name": "Probability of Detection",
                "weight": 10
            },
            {
                "name": "Kling-Gupta Efficiency",
                "weight": 15
            },
            {
                "name": "Normalized Nash-Sutcliffe Efficiency",
                "weight": 15
            },
            {
                "name": "Pearson Correlation Coefficient",
                "weight": 18
            }
        ]
    }
}
TOP_HALF = {
    "observations": [
        {
            "name": "Observations",
            "value_field": "observation",
            "value_selectors": [
                {
                    "name": "observation",
                    "where": "value",
                    "path": ["values[*]", "value[*]", "value"],
                    "datatype": "float",
                    "origin": ["$", "value", "timeSeries[*]"],
                    "associated_fields": [
                        {
                            "name":"value_date",
                            "path": ["values[*]", "value[*]", "dateTime"],
                            "datatype": "datetime"
                        },
                        {
                            "name":"observation_location",
                            "path": ["sourceInfo", "siteCode", "[0]", "value"],
                            "datatype": "string"
                        },
                        {
                            "name":"unit",
                            "path": ["variable", "unit", "unitCode"],
                            "datatype": "string"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "data_format": "json",
                "address": "resources/observations.json"
            },
            "locations": {
                "identify": True,
                "from_field": "value"
            },
            "unit": {
                "field": "unit"
            },
            "x_axis": "value_date"
        }
    ],
    "predictions": [
        {
            "name": "Predictions",
            "value_field": "prediction",
            "value_selectors": [
                {
                    "name": "predicted",
                    "where": "column",
                    "associated_fields": [
                        {
                            "name": "date",
                            "datatype": "datetime"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "data_format": "csv",
                "address": "resources/cat.*cfs.csv",
                "parse_dates": ["date"]
            },
            "locations": {
                "identify": True,
                "from_field": "filename",
                "pattern": "cat-\\d\\d"
            },
            "field_mapping": [
                {
                    "field": "prediction",
                    "map_type": "column",
                    "value": "predicted"
                },
                {
                    "field": "prediction_location",
                    "map_type": "column",
                    "value": "location"
                },
                {
                    "field": "value_date",
                    "map_type": "column",
                    "value": "date"
                }
            ],
            "unit": {
                "value": "ft^3/s"
            },
            "x_axis": "value_date"
        }
    ],
    "crosswalks": [
        {
            "name": "Crosswalk",
            "backend": {
                "backend_type": "file",
                "address": "resources/crosswalk.json",
                "data_format": "json"
            },
            "observation_field_name": "observation_location",
            "prediction_field_name": "prediction_location",
            "field": {
                "name": "prediction_location",
                "where": "key",
                "path": ["* where site_no"],
                "origin": "$",
                "datatype": "string",
                "associated_fields": [
                    {
                        "name": "observation_location",
                        "path": "site_no",
                        "datatype": "string"
                    }
                ]
            }
        }
    ]
}
EXPECTED_ENTIRETY = {
    "observations": [
        {
            "name": "Observations",
            "value_field": "observation",
            "value_selectors": [
                {
                    "name": "observation",
                    "where": "value",
                    "path": ["values[*]", "value[*]", "value"],
                    "datatype": "float",
                    "origin": ["$", "value", "timeSeries[*]"],
                    "associated_fields": [
                        {
                            "name":"value_date",
                            "path": ["values[*]", "value[*]", "dateTime"],
                            "datatype": "datetime"
                        },
                        {
                            "name":"observation_location",
                            "path": ["sourceInfo", "siteCode", "[0]", "value"],
                            "datatype": "string"
                        },
                        {
                            "name":"unit",
                            "path": ["variable", "unit", "unitCode"],
                            "datatype": "string"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "data_format": "json",
                "address": "resources/observations.json"
            },
            "locations": {
                "identify": True,
                "from_field": "value"
            },
            "unit": {
                "field": "unit"
            },
            "x_axis": "value_date"
        }
    ],
    "predictions": [
        {
            "name": "Predictions",
            "value_field": "prediction",
            "value_selectors": [
                {
                    "name": "predicted",
                    "where": "column",
                    "associated_fields": [
                        {
                            "name": "date",
                            "datatype": "datetime"
                        }
                    ]
                }
            ],
            "backend": {
                "backend_type": "file",
                "data_format": "csv",
                "address": "resources/cat.*cfs.csv",
                "parse_dates": ["date"]
            },
            "locations": {
                "identify": True,
                "from_field": "filename",
                "pattern": "cat-\\d\\d"
            },
            "field_mapping": [
                {
                    "field": "prediction",
                    "map_type": "column",
                    "value": "predicted"
                },
                {
                    "field": "prediction_location",
                    "map_type": "column",
                    "value": "location"
                },
                {
                    "field": "value_date",
                    "map_type": "column",
                    "value": "date"
                }
            ],
            "unit": {
                "value": "ft^3/s"
            },
            "x_axis": "value_date"
        }
    ],
    "crosswalks": [
        {
            "name": "Crosswalk",
            "backend": {
                "backend_type": "file",
                "address": "resources/crosswalk.json",
                "data_format": "json"
            },
            "observation_field_name": "observation_location",
            "prediction_field_name": "prediction_location",
            "field": {
                "name": "prediction_location",
                "where": "key",
                "path": ["* where site_no"],
                "origin": "$",
                "datatype": "string",
                "associated_fields": [
                    {
                        "name": "observation_location",
                        "path": "site_no",
                        "datatype": "string"
                    }
                ]
            }
        }
    ],
    "thresholds": [
        {
            "name": "NWIS Stat Percentiles",
            "backend": {
                "name": "NWIS Stat Thresholds",
                "backend_type": "file",
                "data_format": "rdb",
                "address": "resources/nwis_stat_thresholds.rdb"
            },
            "locations": {
                "identify": True,
                "from_field": "column",
                "pattern": "site_no"
            },
            "application_rules": {
                "name": "Date to Day",
                "threshold_field": {
                    "name": "threshold_day",
                    "path": [
                        "month_nu",
                        "day_nu"
                    ],
                    "datatype": "Day"
                },
                "observation_field": {
                    "name": "threshold_day",
                    "path": [
                        "value_date"
                    ],
                    "datatype": "Day"
                }
            },
            "definitions": [
                {
                    "name": "75th Percentile",
                    "field": "p75_va",
                    "weight": 10,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "80th Percentile",
                    "field": "p80_va",
                    "weight": 5,
                    "unit": {
                        "value": "ft^3/s"
                    }
                },
                {
                    "name": "Median",
                    "field": "p50_va",
                    "weight": 1,
                    "unit": {
                        "value": "ft^3/s"
                    }
                }
            ]
        }
    ],
    "scheme": {
        "name": "Prefer Pearson, then Nash and Kling, then POD and FAR",
        "metrics": [
            {
                "name": "False Alarm Ratio",
                "weight": 10
            },
            {
                "name": "Probability of Detection",
                "weight": 10
            },
            {
                "name": "Kling-Gupta Efficiency",
                "weight": 15
            },
            {
                "name": "Normalized Nash-Sutcliffe Efficiency",
                "weight": 15
            },
            {
                "name": "Pearson Correlation Coefficient",
                "weight": 18
            }
        ]
    }
}


class TestHelperFunctions(unittest.TestCase):
    def test_simple_merge_dictionaries(self):
        first_data = {"one": 1, "two": 2}
        second_data = {"two": 3, "three": 3}
        third_data = {"one": 1, "two": 2, "three": {3, 5, 6}}
        fourth_data = {"one": {"a": "a", "b": "b"}, "two": 3, "three": 3}
        fifth_data = {"one": {"a": 1, "c": "c"}, "two": 2}
        """
        >>> first_map = {"one": 1, "two": 2}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": 2}
        >>> second_map = {"two": 3, "three": 3}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": 3}
        >>> first_map = {"one": 1, "two": 2, "three": {3, 5, 6}}
        >>> merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": {3, 5, 6}}
        >>> second_map = {"one": {"a": "a", "b": "b"}, "two": 3, "three": 3}
        >>> merge_dictionaries(first_map, second_map)
        {"one": [1, {"a": "a", "b": "b"}], "two": [2, 3], "three": {3, 5, 6}}
        >>> first_map = {"one": {"a": 1, "c": "c"}, "two": 2}
        >>> merge_dictionaries(first_map, second_map)
        {"one": {"a": ["a", 1], "b": "b", "c": "c"}, "two": [2, 3], "three": 3}}
        >>> merge_dictionaries(first=first_map, second=second_map)
        {"one": {"a": "a", "b": "b", "c": "c"}, "two": 3, "three": 3}"""

        self.assertIsNone(merge_dictionaries(None, None))
        self.assertEqual(merge_dictionaries({}, {}), {})

        self.assertEqual(merge_dictionaries(first_data, {}), first_data)
        self.assertEqual(merge_dictionaries({}, first_data), first_data)
        self.assertEqual(merge_dictionaries(first_data, None), first_data)
        self.assertEqual(merge_dictionaries(None, first_data), first_data)

        self.assertEqual(
            merge_dictionaries(first_data, second_data, strategy=ConflictStrategy.COMBINE),
            {"one": 1, "two": [2, 3], "three": 3}
        )
        self.assertEqual(
            merge_dictionaries(second_data, first_data, strategy=ConflictStrategy.COMBINE),
            {"one": 1, "two": [3, 2], "three": 3}
        )
        self.assertEqual(
            merge_dictionaries(first_data, second_data),
            {
                "one": 1,
                "two": 3,
                "three": 3
            }
        )
        self.assertEqual(
            merge_dictionaries(second_data, first_data),
            {
                "one": 1,
                "two": 2,
                "three": 3
            }
        )

        self.assertEqual(
            merge_dictionaries(first_data, third_data),
            {
                "one": 1,
                "two": 2,
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge_dictionaries(second_data, third_data, strategy=ConflictStrategy.COMBINE),
            {
                "one": 1,
                "two": [3, 2],
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge_dictionaries(second_data, third_data),
            {
                "one": 1,
                "two": 2,
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge_dictionaries(third_data, second_data, strategy=ConflictStrategy.OVERWRITE),
            {
                "one": 1,
                "two": 3,
                "three": 3
            }
        )

        self.assertEqual(
            merge_dictionaries(first_data, fourth_data, strategy=ConflictStrategy.COMBINE),
            {
                "one": [1, {"a": "a", "b": "b"}],
                "two": [2, 3],
                "three": 3
            }
        )
        self.assertEqual(
            merge_dictionaries(fourth_data, first_data, strategy=ConflictStrategy.COMBINE),
            {
                "one": [
                    {"a": "a", "b": "b"},
                    1
                ],
                "two": [3, 2],
                "three": 3
            }
        )

    def test_complex_merge_dictionaries(self):
        combined_data = merge_dictionaries(TOP_HALF, BOTTOM_HALF)
        self.assertEqual(combined_data, EXPECTED_ENTIRETY)
