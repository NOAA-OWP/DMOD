import os.path
import unittest

from datetime import datetime
from datetime import tzinfo
from datetime import timedelta
from datetime import timezone
from datetime import date

import pandas

from ..evaluations import util


class TestCSVRetrieving(unittest.TestCase):
    def test_name_to_dtype(self):
        pass

    def test_is_arraytype(self):
        pass

    def test_value_is_number(self):
        pass

    def test_type_is_number(self):
        pass

    def test_clean_name(self):
        pass

    def test_is_indexed(self):
        pass

    def test_str_is_float(self):
        pass

    def test_find_indices(self):
        pass

    def test_parse_non_naive_dates(self):
        pass

    def test_to_date_or_time(self):
        todays_date = datetime.utcnow()

        possible_date = "2022-05-22T15:33-03:00"

        parsed_date = util.to_date_or_time(possible_date)

        self.assertIsNotNone(parsed_date)

        self.assertEqual(parsed_date.year, 2022)
        self.assertEqual(parsed_date.month, 5)
        self.assertEqual(parsed_date.day, 22)
        self.assertEqual(parsed_date.hour, 15)
        self.assertEqual(parsed_date.minute, 33)

        self.assertIsNotNone(parsed_date.tzinfo)

        date_data = {
            "year": 1915
        }

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, date)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, todays_date.month)
        self.assertEqual(parsed_date.day, todays_date.day)

        date_data['day'] = 7
        date_data['d'] = 42

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, date)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, todays_date.month)
        self.assertEqual(parsed_date.day, todays_date.day)

        date_data['hour'] = 9
        date_data['hr'] = 42

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, todays_date.month)
        self.assertEqual(parsed_date.day, todays_date.day)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 0)

        self.assertIsNone(parsed_date.tzinfo)

        date_data['minute'] = 14
        date_data['min'] = 42

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, todays_date.month)
        self.assertEqual(parsed_date.day, todays_date.day)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 14)

        self.assertIsNone(parsed_date.tzinfo)

        date_data['month'] = 12
        date_data['mth'] = 42

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, 12)
        self.assertEqual(parsed_date.day, 7)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 14)

        self.assertIsNone(parsed_date.tzinfo)

        date_data['tz'] = "UTC"
        date_data['t'] = "sadfa"

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, 12)
        self.assertEqual(parsed_date.day, 7)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 14)

        self.assertIsNotNone(parsed_date.tzinfo)
        self.assertEqual(parsed_date.tzinfo.utcoffset(parsed_date), timedelta(0))

        date_data['timezone'] = "-0300"
        date_data['tq'] = "sdfsdfsadfa"

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 1915)
        self.assertEqual(parsed_date.month, 12)
        self.assertEqual(parsed_date.day, 7)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 14)

        self.assertIsNotNone(parsed_date.tzinfo)
        self.assertEqual(parsed_date.tzinfo.utcoffset(parsed_date), timedelta(hours=-3))

        date_data['Date'] = "2022/1/14"
        date_data['sdf'] = "d"

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 2022)
        self.assertEqual(parsed_date.month, 1)
        self.assertEqual(parsed_date.day, 14)
        self.assertEqual(parsed_date.hour, 9)
        self.assertEqual(parsed_date.minute, 14)

        self.assertIsNotNone(parsed_date.tzinfo)
        self.assertEqual(parsed_date.tzinfo.utcoffset(parsed_date), timedelta(hours=-3))

        date_data['datetime'] = 1649106272.846112
        date_data['dtime'] = 3205935.3453

        parsed_date = util.to_date_or_time(date_data)

        self.assertIsNotNone(parsed_date)
        self.assertIsInstance(parsed_date, datetime)

        self.assertEqual(parsed_date.year, 2022)
        self.assertEqual(parsed_date.month, 4)
        self.assertEqual(parsed_date.day, 4)
        self.assertEqual(parsed_date.hour, 21)
        self.assertEqual(parsed_date.minute, 4)
        self.assertEqual(parsed_date.second, 32)

        self.assertIsNone(parsed_date.tzinfo)




if __name__ == '__main__':
    unittest.main()
