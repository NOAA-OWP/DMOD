"""
Tests for the merge functionality
"""
import typing
import os
import json
import pathlib

import unittest

from ..evaluations.utilities import merge

RESOURCE_DIRECTORY = pathlib.Path(__file__).parent / "resources"

BOTTOM_HALF = {
    "thresholds": [
        {
            "name": "NWIS Stat Percentiles",
            "backend": {
                "name": "NWIS Stat Thresholds",
                "backend_type": "file",
                "format": "rdb",
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
                "format": "json",
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
                "format": "csv",
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
                "format": "json"
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
                "format": "json",
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
                "format": "csv",
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
                "format": "json"
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
                "format": "rdb",
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


class TestMerging(unittest.TestCase):
    first_dictionary: typing.Dict[str, typing.Any]
    second_dictionary: typing.Dict[str, typing.Any]
    expected_combination: typing.Dict[str, typing.Any]

    specification_part_a: dict
    specification_part_b: dict
    entire_specification: dict

    default_merger: merge.Merger
    fail_merger: merge.Merger
    combine_merger: merge.Merger
    overwrite_merger: merge.Merger

    default_conditions: merge.MergeConditions

    def setUp(self) -> None:
        self.first_dictionary = {
            "a": 1,
            "c": [1, 2, 3, 4],
            "e": {
                "f": [
                    {
                        "g": 14,
                        "h": "h",
                        "i": [
                            {
                                "j": "k"
                            }
                        ]
                    }
                ]
            },
            "q": {8, 9, 12, 2, 3},
            "r": 7,
        }

        self.second_dictionary = {
            "b": 3242,
            "c": [3, 4, 5, 6, 7],
            "d": "This is a test",
            "e": {
                "f": [
                    {
                        "g": 14,
                        "h": "sdfsds",
                        "i": [
                            {
                                "j": "k"
                            }
                        ]
                    },
                    {
                        "g": 14,
                        "h": "h",
                        "i": [
                            {
                                "s": 1231
                            }
                        ]
                    }
                ]
            },
            "q": 12,
            "r": [1, 2, 3, 7]
        }

        self.expected_combination = {
            "a": 1,
            "b": 3242,
            "c": [1, 2, 3, 4, 3, 4, 5, 6, 7],
            "d": "This is a test",
            "e": {
                "f": [
                    {
                        "g": 14,
                        "h": "h",
                        "i": [
                            {
                                "j": "k"
                            },
                            {
                                "s": 1231
                            },
                        ]
                    },
                    {
                        "g": 14,
                        "h": "sdfsds",
                        "i": [
                            {
                                "j": "k"
                            }
                        ]
                    },
                ]
            },
            "q": {8, 9, 12, 2, 3},
            "r": [1, 2, 3, 7]
        }

        with open(os.path.join(RESOURCE_DIRECTORY, "merge.part_a.json"), 'r') as part_a_file:
            self.specification_part_a = json.load(part_a_file)

        with open(os.path.join(RESOURCE_DIRECTORY, "merge.part_b.json"), 'r') as part_b_file:
            self.specification_part_b = json.load(part_b_file)

        with open(os.path.join(RESOURCE_DIRECTORY, "merge.expected.json"), 'r') as entire_file:
            self.entire_specification = json.load(entire_file)

        self.fail_merger = merge.create_dictionary_merger(strategy=merge.ConflictStrategy.FAIL)
        self.combine_merger = merge.create_dictionary_merger(strategy=merge.ConflictStrategy.COMBINE)
        self.overwrite_merger = merge.create_dictionary_merger(strategy=merge.ConflictStrategy.OVERWRITE)

        self.default_merger = self.fail_merger
        self.default_conditions = merge.MergeConditions()

    def test_map_structure_is_compatible(self):
        control = {
            "g": 14,
            "h": "h",
            "i": [
                {
                    "j": "k"
                }
            ]
        }

        matching = {
            "g": 14,
            "h": "h",
            "i": [
                {
                    "s": 1231
                }
            ]
        }

        not_matching = {
            "g": 1432,
            "h": "h",
            "i": [
                {
                    "j": "k"
                }
            ]
        }

        control_structure_matches_matching = merge.map_structure_is_compatible(control, matching)
        control_structure_matches_not_matching = merge.map_structure_is_compatible(control, not_matching)

        self.assertTrue(control_structure_matches_matching)
        self.assertFalse(control_structure_matches_not_matching)

    def test_map_conflicts(self):
        control = {
            "g": 14,
            "h": "h",
            "i": [
                {
                    "j": "k"
                }
            ]
        }

        variation_one = {
            "g": 14,
            "h": "h",
            "i": [
                {
                    "s": 1231
                }
            ]
        }

        variation_two = {
            "g": 1432,
            "h": "h",
            "i": [
                {
                    "j": "k"
                }
            ]
        }

        should_not_conflict = not merge.maps_conflict(control, variation_one)
        should_conflict = merge.maps_conflict(control, variation_two)

        self.assertTrue(should_not_conflict)
        self.assertTrue(should_conflict)

    def test_dictionary_merge(self):
        merged_data = merge.merge_dictionaries(self.first_dictionary, self.second_dictionary)
        self.assertEqual(merged_data, self.expected_combination)

    def test_nothing(self):
        should_be_none = merge.nothing(
            self.default_merger,
            self.default_conditions,
            None,
            None,
            self.default_merger.strategy,
            None
        )
        self.assertIsNone(should_be_none)

    def test_return_the_non_null(self):
        should_be_six = merge.return_the_non_null(
            self.default_merger,
            self.default_conditions,
            6,
            None,
            self.default_merger.strategy,
            None
        )

        should_be_nine = merge.return_the_non_null(
            self.default_merger,
            self.default_conditions,
            None,
            "nine",
            self.default_merger.strategy,
            None
        )

        self.assertEqual(should_be_six, 6)
        self.assertEqual(should_be_nine, "nine")

    def test_combine_sets(self):
        merge_path = merge.MergePath("/one/two/three/test", "/one/two/three/8")

        should_be_1_2_3_4_5 = merge.combine_sets(
            self.default_merger,
            self.default_conditions,
            {1, 2, 3},
            {3, 4, 5},
            self.default_merger.strategy,
            merge_path
        )

        self.assertEqual(should_be_1_2_3_4_5, {1, 2, 3, 4, 5})

    def test_merge_maps(self):
        first_map = {
            "a": 1,
            "b": 2,
            "c": 3,
            "j": {1, 2}
        }

        second_map = {
            "d": 4,
            "e": 5,
            "f": 6,
            "g": {
                "h": 8,
                "i": 9
            },
            "j": {3, 4}
        }

        merged_map = merge.merge_maps(
            self.default_merger,
            self.default_conditions,
            first_map,
            second_map,
            self.default_merger.strategy,
            merge.MergePath()
        )

        expected_map = {
            "a": 1,
            "b": 2,
            "c": 3,
            "d": 4,
            "e": 5,
            "f": 6,
            "g": {
                "h": 8,
                "i": 9
            },
            "j": {1, 2, 3, 4}
        }

        self.assertEqual(merged_map, expected_map)

    def test_combine_when_first_is_a_set_second_is_hashable(self):
        path = merge.MergePath(
            "/Animalia/Chordata/Mammalia/Carnivora/Canidae/Canis",
            "/Hospitals/Vetenarians/3/patient_type/0"
        )

        first_data = {"Canis Aureus", "Canis Latrans", "Canis Lupaster", "Canis Rufus"}
        second_data = "Canus Familiaris"
        first_data_with_second_entry = first_data.copy()
        first_data_with_second_entry.add(second_data)

        overwritten_data_without_entry = merge.combine_when_first_is_a_set_second_is_hashable(
            self.overwrite_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(overwritten_data_without_entry, second_data)

        combination_data_without_entry = merge.combine_when_first_is_a_set_second_is_hashable(
            self.combine_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(combination_data_without_entry, first_data_with_second_entry)

        self.assertRaises(
            ValueError,
            merge.combine_when_first_is_a_set_second_is_hashable,
            self.fail_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.fail_merger.strategy,
            path
        )

        not_failed_data = merge.combine_when_first_is_a_set_second_is_hashable(
            self.fail_merger,
            self.default_conditions,
            first_data_with_second_entry,
            second_data,
            self.fail_merger.strategy,
            path
        )

        self.assertEqual(not_failed_data, first_data_with_second_entry)

    def test_combine_when_first_is_hashable_second_is_a_set(self):
        path = merge.MergePath(
            "/Animalia/Chordata/Mammalia/Carnivora/Canidae/Canis",
            "/Hospitals/Vetenarians/3/patient_type/0"
        )

        first_data = "Canus Familiaris"
        second_data = {"Canis Aureus", "Canis Latrans", "Canis Lupaster", "Canis Rufus"}
        second_data_with_first_entry = second_data.copy()
        second_data_with_first_entry.add(first_data)

        overwritten_data_without_entry = merge.combine_when_first_is_hashable_second_is_a_set(
            self.overwrite_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(overwritten_data_without_entry, second_data)

        combination_data_without_entry = merge.combine_when_first_is_hashable_second_is_a_set(
            self.combine_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(combination_data_without_entry, second_data_with_first_entry)

        self.assertRaises(
            ValueError,
            merge.combine_when_first_is_hashable_second_is_a_set,
            self.fail_merger,
            self.default_conditions,
            first_data,
            second_data,
            self.fail_merger.strategy,
            path
        )

        not_failed_data = merge.combine_when_first_is_hashable_second_is_a_set(
            self.fail_merger,
            self.default_conditions,
            first_data,
            second_data_with_first_entry,
            self.fail_merger.strategy,
            path
        )

        self.assertEqual(not_failed_data, second_data_with_first_entry)

    def test_combine_two_arrays(self):
        path = merge.MergePath(
            "/Animalia/Chordata/Mammalia/Carnivora/Canidae/Canis",
            "/Hospitals/Veterinarians/3/patient_type"
        )

        first_data = [1, 2, 3, 4, 5]

        combined_first_and_empty = merge.combine_two_arrays(
            self.default_merger,
            self.default_conditions,
            first_data,
            [],
            self.default_merger.strategy,
            path
        )

        self.assertEqual(first_data, combined_first_and_empty)

        combined_empty_and_first = merge.combine_two_arrays(
            self.default_merger,
            self.default_conditions,
            [],
            first_data,
            self.default_merger.strategy,
            path
        )

        self.assertEqual(first_data, combined_empty_and_first)

        combined_first_and_first = merge.combine_two_arrays(
            self.default_merger,
            self.default_conditions,
            first_data,
            first_data,
            self.default_merger.strategy,
            path
        )

        self.assertEqual(first_data, combined_first_and_first)

        first_id_data = ["Animalia", "Chordata", "Mammalia", "Carnivora", "Canidae", "Canis"]
        second_id_data = ["Hospitals", "Veterinarians", "3", "patient_type"]

        overwritten_first_id_and_second = merge.combine_two_arrays(
            self.fail_merger,
            self.default_conditions,
            first_id_data,
            second_id_data,
            self.fail_merger.strategy,
            path
        )

        self.assertEqual(second_id_data, overwritten_first_id_and_second)

        overwritten_first_id_and_second = merge.combine_two_arrays(
            self.overwrite_merger,
            self.default_conditions,
            first_id_data,
            second_id_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(second_id_data, overwritten_first_id_and_second)

        combined_first_id_and_second = merge.combine_two_arrays(
            self.combine_merger,
            self.default_conditions,
            first_id_data,
            second_id_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(combined_first_id_and_second, first_id_data + second_id_data)

        mixed_first_data = ["Animalia", 0, "Mammalia", "Carnivora", "Canidae", "Canis"]
        similar_content_for_first_data = [0, "Animalia", "Mammalia", "Carnivora", "Canidae", "Canis"]

        combined_mixed_first_and_mixed_second = merge.combine_two_arrays(
            self.combine_merger,
            self.default_conditions,
            mixed_first_data,
            similar_content_for_first_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            combined_mixed_first_and_mixed_second,
            mixed_first_data + similar_content_for_first_data
        )

        combined_mixed_first_and_mixed_second = merge.combine_two_arrays(
            self.overwrite_merger,
            self.default_conditions,
            mixed_first_data,
            similar_content_for_first_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(
            combined_mixed_first_and_mixed_second,
            mixed_first_data + similar_content_for_first_data
        )

        first_data_with_maps = [
            "a",
            1,
            {
                "b": 1,
                "c": 2,
                "i": [
                    3, 4, 5, 6
                ],
                "j": {
                    "k": 22,
                    "l": 14
                }
            }
        ]

        second_data_with_maps = [
            4,
            "nine",
            {
                "b": 1,
                "c": 21,
                "i": [
                    3, 4, 5, 6
                ],
                "j": {
                    "k": 22,
                    "l": 14
                }
            },
            {
                "b": 1,
                "c": 2,
                "i": [
                    37, 44, 65, 66
                ],
                "j": {
                    "m": 2,
                    "n": 3
                }
            }
        ]

        expected_combined_with_maps = [
            "a",
            1,
            {
                "b": 1,
                "c": 2,
                "i": [
                    3, 4, 5, 6, 37, 44, 65, 66
                ],
                "j": {
                    "k": 22,
                    "l": 14,
                    "m": 2,
                    "n": 3
                }
            },
            4,
            "nine",
            {
                "b": 1,
                "c": 21,
                "i": [
                    3, 4, 5, 6
                ],
                "j": {
                    "k": 22,
                    "l": 14
                }
            }
        ]

        combined_with_dictionaries = merge.combine_two_arrays(
            self.combine_merger,
            self.default_conditions,
            first_data_with_maps,
            second_data_with_maps,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            combined_with_dictionaries,
            expected_combined_with_maps
        )

    def test_combine_array_and_non_array(self):
        path = merge.MergePath(
            "/Animalia/Chordata/Mammalia/Carnivora/Canidae/Canis",
            "/Hospitals/Vetenarians/3/patient_type/0/name"
        )

        first_data = ["Canis Aureus", "Canis Latrans", "Canis Lupaster", "Canis Rufus"]
        second_data = "Canus Familiaris"

        self.assertRaises(
            ValueError,
            merge.combine_array_and_non_array,
            self.fail_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.fail_merger.strategy,
            path
        )

        overwritten_data = merge.combine_array_and_non_array(
            self.overwrite_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(
            second_data,
            overwritten_data
        )

        combined_data = merge.combine_array_and_non_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            first_data + [second_data],
            combined_data
        )

        first_with_map = [
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Antonii",
                    "Canis Edwardii"
                ]
            }
        ]
        second_with_matching_map = {
            "extinct": [
                "Canis Etruscus",
                "Canis Variabilis"
            ]
        }
        second_with_different_map = {
            "subgenus": [
                "Canis Africanus"
            ]
        }

        expected_combination_of_first_and_second_with_matching = [
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Antonii",
                    "Canis Edwardii",
                    "Canis Etruscus",
                    "Canis Variabilis"
                ]
            },
        ]

        expected_combination_of_first_and_second_without_matching = [
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Antonii",
                    "Canis Edwardii"
                ]
            },
            {
                "subgenus": [
                    "Canis Africanus"
                ]
            }
        ]

        combined_first_and_second_with_matching = merge.combine_array_and_non_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_with_map, second_with_matching_map),
            first_with_map,
            second_with_matching_map,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            expected_combination_of_first_and_second_with_matching,
            combined_first_and_second_with_matching
        )

        combined_first_and_second_without_matching = merge.combine_array_and_non_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_with_map, second_with_different_map),
            first_with_map,
            second_with_different_map,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            expected_combination_of_first_and_second_without_matching,
            combined_first_and_second_without_matching
        )

    def test_combine_non_array_and_array(self):
        path = merge.MergePath(
            "/Animalia/Chordata/Mammalia/Carnivora/Canidae/Canis",
            "/Hospitals/Vetenarians/3/patient_type/0/name"
        )

        first_data = "Canus Familiaris"
        second_data = ["Canis Aureus", "Canis Latrans", "Canis Lupaster", "Canis Rufus"]

        self.assertRaises(
            ValueError,
            merge.combine_non_array_and_array,
            self.fail_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.fail_merger.strategy,
            path
        )

        overwritten_data = merge.combine_non_array_and_array(
            self.overwrite_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.overwrite_merger.strategy,
            path
        )

        self.assertEqual(
            second_data,
            overwritten_data
        )

        combined_data = merge.combine_non_array_and_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_data, second_data),
            first_data,
            second_data,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            [first_data] + second_data,
            combined_data
        )

        second_with_map = [
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Antonii",
                    "Canis Edwardii"
                ]
            }
        ]
        first_with_matching_map = {
            "extinct": [
                "Canis Etruscus",
                "Canis Variabilis"
            ]
        }
        first_with_different_map = {
            "subgenus": [
                "Canis Africanus"
            ]
        }

        expected_combination_of_first_and_second_with_matching = [
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Etruscus",
                    "Canis Variabilis",
                    "Canis Antonii",
                    "Canis Edwardii",
                ]
            },
        ]

        expected_combination_of_first_and_second_without_matching = [
            {
                "subgenus": [
                    "Canis Africanus"
                ]
            },
            "Canis Aureus",
            "Canis Latrans",
            "Canis Lupaster",
            "Canis Rufus",
            {
                "extinct": [
                    "Canis Antonii",
                    "Canis Edwardii"
                ]
            }
        ]

        combined_first_and_second_with_matching = merge.combine_non_array_and_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_with_matching_map, second_with_map),
            first_with_matching_map,
            second_with_map,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            expected_combination_of_first_and_second_with_matching,
            combined_first_and_second_with_matching
        )

        combined_first_and_second_without_matching = merge.combine_non_array_and_array(
            self.combine_merger,
            merge.MergeConditions.from_values(first_with_different_map, second_with_map),
            first_with_different_map,
            second_with_map,
            self.combine_merger.strategy,
            path
        )

        self.assertEqual(
            expected_combination_of_first_and_second_without_matching,
            combined_first_and_second_without_matching
        )

    def test_combine_scalars(self):
        six_and_six = merge.combine_scalars(
            self.combine_merger,
            self.default_conditions,
            6,
            6,
            self.combine_merger.strategy,
            merge.MergePath()
        )

        self.assertEqual(6, six_and_six)

        six_and_seven = merge.combine_scalars(
            self.combine_merger,
            self.default_conditions,
            6,
            7,
            self.combine_merger.strategy,
            merge.MergePath()
        )

        self.assertEqual([6, 7], six_and_seven)

        only_seven = merge.combine_scalars(
            self.default_merger,
            self.default_conditions.from_values(6, 7),
            6,
            7,
            self.default_merger.strategy,
            merge.MergePath()
        )

        self.assertEqual(7, only_seven)

    def test_merge_dictionaries(self):
        merged_data = merge.merge_dictionaries(
            self.specification_part_a,
            self.specification_part_b
        )

        self.assertEqual(
            self.entire_specification,
            merged_data
        )


    def test_simple_merge_dictionaries(self):
        first_data = {"one": 1, "two": 2}
        second_data = {"two": 3, "three": 3}
        third_data = {"one": 1, "two": 2, "three": {3, 5, 6}}
        fourth_data = {"one": {"a": "a", "b": "b"}, "two": 3, "three": 3}
        fifth_data = {"one": {"a": 1, "c": "c"}, "two": 2}
        """
        >>> first_map = {"one": 1, "two": 2}
        >>> merge.merge_dictionaries(first_map, second_map)
        {"one": 1, "two": 2}
        >>> second_map = {"two": 3, "three": 3}
        >>> merge.merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": 3}
        >>> first_map = {"one": 1, "two": 2, "three": {3, 5, 6}}
        >>> merge.merge_dictionaries(first_map, second_map)
        {"one": 1, "two": [2, 3], "three": {3, 5, 6}}
        >>> second_map = {"one": {"a": "a", "b": "b"}, "two": 3, "three": 3}
        >>> merge.merge_dictionaries(first_map, second_map)
        {"one": [1, {"a": "a", "b": "b"}], "two": [2, 3], "three": {3, 5, 6}}
        >>> first_map = {"one": {"a": 1, "c": "c"}, "two": 2}
        >>> merge.merge_dictionaries(first_map, second_map)
        {"one": {"a": ["a", 1], "b": "b", "c": "c"}, "two": [2, 3], "three": 3}}
        >>> merge.merge_dictionaries(first=first_map, second=second_map)
        {"one": {"a": "a", "b": "b", "c": "c"}, "two": 3, "three": 3}"""
        self.assertIsNone(merge.merge_dictionaries(None, None))
        self.assertEqual(merge.merge_dictionaries({}, {}), {})

        self.assertEqual(merge.merge_dictionaries(first_data, {}), first_data)
        self.assertEqual(merge.merge_dictionaries({}, first_data), first_data)
        self.assertEqual(merge.merge_dictionaries(first_data, None), first_data)
        self.assertEqual(merge.merge_dictionaries(None, first_data), first_data)

        self.assertEqual(
            merge.merge_dictionaries(first_data, second_data, strategy=merge.ConflictStrategy.COMBINE),
            {"one": 1, "two": [2, 3], "three": 3}
        )
        self.assertEqual(
            merge.merge_dictionaries(second_data, first_data, strategy=merge.ConflictStrategy.COMBINE),
            {"one": 1, "two": [3, 2], "three": 3}
        )
        self.assertEqual(
            merge.merge_dictionaries(first_data, second_data),
            {
                "one": 1,
                "two": 3,
                "three": 3
            }
        )
        self.assertEqual(
            merge.merge_dictionaries(second_data, first_data),
            {
                "one": 1,
                "two": 2,
                "three": 3
            }
        )

        self.assertEqual(
            merge.merge_dictionaries(first_data, third_data),
            {
                "one": 1,
                "two": 2,
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge.merge_dictionaries(second_data, third_data, strategy=merge.ConflictStrategy.COMBINE),
            {
                "one": 1,
                "two": [3, 2],
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge.merge_dictionaries(second_data, third_data),
            {
                "one": 1,
                "two": 2,
                "three": {3, 5, 6}
            }
        )
        self.assertEqual(
            merge.merge_dictionaries(third_data, second_data, strategy=merge.ConflictStrategy.OVERWRITE),
            {
                "one": 1,
                "two": 3,
                "three": 3
            }
        )

        self.assertEqual(
            merge.merge_dictionaries(first_data, fourth_data, strategy=merge.ConflictStrategy.COMBINE),
            {
                "one": [1, {"a": "a", "b": "b"}],
                "two": [2, 3],
                "three": 3
            }
        )
        self.assertEqual(
            merge.merge_dictionaries(fourth_data, first_data, strategy=merge.ConflictStrategy.COMBINE),
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
        combined_data = merge.merge_dictionaries(TOP_HALF, BOTTOM_HALF)
        self.assertEqual(combined_data, EXPECTED_ENTIRETY)
