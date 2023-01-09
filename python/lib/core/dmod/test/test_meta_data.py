import unittest
from datetime import datetime

from ..core.meta_data import (
    ContinuousRestriction,
    DiscreteRestriction,
    StandardDatasetIndex,
    DataDomain,
    DataFormat,
    TimeRange,
    DataCategory,
    DataRequirement,
)

from typing import Any


class TestContinuousRestriction(unittest.TestCase):
    def test_custom_datetime_pattern(self):
        o = ContinuousRestriction(
            begin="2020-01-01",
            end="2020-01-02",
            variable="TIME",
            datetime_pattern="%Y-%m-%d",
        )
        self.assertEqual(o.variable, StandardDatasetIndex.TIME)

    def test_custom_datetime_pattern_should_fail(self):
        with self.assertRaises(RuntimeError):
            ContinuousRestriction(
                begin="2020-01-01",
                end="2019-12-31",
                variable="TIME",
                datetime_pattern="%Y-%m-%d",
            )

    def test_create_from_python_objects(self):
        begin = datetime(2020, 1, 1)
        end = datetime(2020, 1, 2)
        o = ContinuousRestriction(
            begin=begin, end=end, variable=StandardDatasetIndex.TIME
        )
        self.assertEqual(o.begin, begin)
        self.assertEqual(o.end, end)
        self.assertEqual(o.variable, StandardDatasetIndex.TIME)

    def test_create_fails_with_invalid_variable(self):
        begin = datetime(2020, 1, 1)
        end = datetime(2020, 1, 2)
        with self.assertRaises(ValueError):
            ContinuousRestriction(
                begin=begin, end=end, variable=StandardDatasetIndex.UNKNOWN
            )

    def test_eq(self):
        begin = datetime(2020, 1, 1)
        end = datetime(2020, 1, 2)
        o1 = ContinuousRestriction(
            begin=begin, end=end, variable=StandardDatasetIndex.TIME
        )
        o2 = ContinuousRestriction(
            begin=begin, end=end, variable=StandardDatasetIndex.TIME
        )

        self.assertEqual(o1, o2)

    def test_hash(self):
        begin = datetime(2020, 1, 1)
        end = datetime(2020, 1, 2)
        var = StandardDatasetIndex.TIME
        expected_hash = hash(f"{var.name}-{begin}-{end}")
        o_hash = hash(ContinuousRestriction(variable=var, begin=begin, end=end))
        self.assertEqual(expected_hash, o_hash)

    def test_to_dict(self):
        begin = "2020-01-01"
        end = "2020-01-02"
        d = ContinuousRestriction(
            begin=begin,
            end=end,
            variable="TIME",
            datetime_pattern="%Y-%m-%d",
        ).to_dict()
        self.assertEqual(d["begin"], begin)
        self.assertEqual(d["end"], end)
        self.assertEqual(d["variable"], StandardDatasetIndex.TIME.name)

    def test_factory_init_from_deserialized_json(self):
        deserialied = {"begin": 0, "end": 1, "variable": "TIME"}
        o1 = ContinuousRestriction.factory_init_from_deserialized_json(deserialied)

        deserialied = {
            "begin": 0,
            "end": 1,
            "variable": "TIME",
            "subclass": "ContinuousRestriction",
        }
        o2 = ContinuousRestriction.factory_init_from_deserialized_json(deserialied)
        self.assertEqual(o1, o2)

    def test_to_json(self):
        import json
        begin = "2020-01-01"
        end = "2020-01-02"
        d = json.loads(
            ContinuousRestriction(
            begin=begin,
            end=end,
            variable="TIME",
            datetime_pattern="%Y-%m-%d",
        ).to_json()
        )

        self.assertEqual(d["begin"], begin)
        self.assertEqual(d["end"], end)
        self.assertEqual(d["variable"], StandardDatasetIndex.TIME.name)


class TestDiscreteRestriction(unittest.TestCase):
    def test_duplicate_values_removed(self):
        o = DiscreteRestriction(
            variable="TIME", values=[1, 1, 1], remove_duplicates=True
        )
        self.assertListEqual(o.values, [1])

    def test_values_reordered(self):
        values = [3, 2, 1]
        o = DiscreteRestriction(variable="TIME", values=values, allow_reorder=True)
        self.assertListEqual(o.values, values[::-1])

    def test_values_removed_not_reordered(self):
        values = [3, 3, 2, 1]
        o = DiscreteRestriction(
            variable="TIME",
            values=values,
            allow_reorder=False,
            remove_duplicates=True,
        )
        self.assertListEqual(o.values, values[1:])

    def test_values_reordered_not_removed(self):
        values = [3, 3, 2, 1]
        o = DiscreteRestriction(
            variable="TIME",
            values=values,
            allow_reorder=True,
            remove_duplicates=False,
        )
        self.assertListEqual(o.values, values[::-1])


class TestDataDomain(unittest.TestCase):
    def test_it_works(self):
        disc_rest = DiscreteRestriction(
            variable=StandardDatasetIndex.DATA_ID, values=["0"]
        )
        o = DataDomain(
            data_format=DataFormat.AORC_CSV,
            discrete_restrictions=[disc_rest],
            data_fields=dict(a="str", b="float", c="int", d="datetime"),
        )
        self.assertEqual(o.custom_data_fields["a"], str)
        self.assertEqual(o.custom_data_fields["b"], float)
        self.assertEqual(o.custom_data_fields["c"], int)
        self.assertEqual(o.custom_data_fields["d"], Any)

    def test_init_fails_if_insufficient_restrictions(self):
        with self.assertRaises(RuntimeError):
            DataDomain(
                data_format=DataFormat.AORC_CSV,
                continuous_restrictions=[],
                discrete_restrictions=[],
            )

        with self.assertRaises(RuntimeError):
            DataDomain(data_format=DataFormat.AORC_CSV)

    def test_factory_init_from_deserialized_json(self):
        data = {
            "data_format": "AORC_CSV",
            "continuous_restrictions": [],
            "discrete_restrictions": [{"variable": "DATA_ID", "values": ["0"]}],
        }
        o = DataDomain.factory_init_from_deserialized_json(data)
        self.assertEqual(o.data_format.name, "AORC_CSV")


class TestTimeRange(unittest.TestCase):
    def test_begin_cannot_come_after_end(self):
        with self.assertRaises(RuntimeError):
            TimeRange(begin=1, end=0)

    def test_cannot_provide_non_time_variable(self):
        with self.assertRaises(RuntimeError):
            TimeRange(variable=StandardDatasetIndex.DATA_ID, begin=1, end=0)

class TestDataRequirement(unittest.TestCase):
    def test_unset_fields_are_excluded_in_serialized_dict(self):
        domain = DataDomain(
            data_format=DataFormat.AORC_CSV,
            discrete_restrictions=[
                DiscreteRestriction(variable=StandardDatasetIndex.DATA_ID, values=["0"])
            ],
        )

        d = DataRequirement(
            domain=domain, is_input=True, category=DataCategory.CONFIG
        ).to_dict()
        self.assertNotIn("size", d)
        self.assertNotIn("fulfilled_by", d)
        self.assertNotIn("fulfilled_access_at", d)

