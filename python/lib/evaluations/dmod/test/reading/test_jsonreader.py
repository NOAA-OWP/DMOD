import os.path
import unittest
import typing
import io

from datetime import datetime
from datetime import timedelta

from dateutil.parser import parse as parse_date

from ...evaluations import jsonquery as jsonquery

TEST_DOCUMENT_PATH = os.path.join(os.path.dirname(__file__), "nwis.json")


class TestJSONQuery(unittest.TestCase):

    def run_value_queries(self, document: jsonquery.Document):
        # Check to see if it can get the string for the address of the request
        query_url = document.query("value/queryInfo/queryURL")

        self.assertEqual(
                query_url,
                "http://waterservices.usgs.gov/nwis/iv/format=json"
                "&indent=on"
                "&sites=01646500"
                "&period=PT12H"
                "&parameterCd=00060"
                "&siteStatus=all"
        )

        # Get all resulting values from the document
        all_measurements = document.query("value/timeSeries/#/values/#/value/*")

        self.assertEqual(len(all_measurements), 44)

        # Get the results from the first time series (will equal the above since there's only one)
        first_measurements = document.query("value/timeSeries/0/values/#/value/*")

        self.assertEqual(len(first_measurements), 44)

        # Get the results from the first set of values of first time series
        #   (will equal the above since there's only one)
        first_measurements = document.query("value/timeSeries/0/values/0/value/*")

        self.assertEqual(len(first_measurements), 44)

        # Get the first measurement
        first_measurement = document.query("value/timeSeries/0/values/0/value/0")

        self.assertTrue(isinstance(first_measurement, dict))

        self.assertEqual(first_measurement['value'], '9570')
        self.assertEqual(first_measurement['dateTime'], "2022-03-15T01:45:00.000-04:00")

        self.assertTrue(isinstance(first_measurement['qualifiers'], typing.Sequence))
        self.assertEqual(len(first_measurement['qualifiers']), 1)
        self.assertEqual(first_measurement['qualifiers'][0], 'P')

        # Get the results from the first set of values of first time series by invoking a reverse lookup
        #   (will equal the above since there's only one)
        first_measurements = document.query("value/timeSeries/0/values/0/value/0/..")

        self.assertEqual(len(first_measurements), 44)

        # Get the results from the first set of values of first time series
        #   (will equal the above since there's only one)
        first_datetimes = document.query("value/timeSeries/0/values/0/value/*/dateTime")

        self.assertEqual(len(first_datetimes), 44)

        interval = timedelta(minutes=15)
        first_datetime = None
        interval_iteration = 0

        for date_and_time_string in first_datetimes:
            date_and_time = parse_date(date_and_time_string)

            if first_datetime is None:
                first_datetime = date_and_time

            self.assertEqual(date_and_time, first_datetime + (interval_iteration * interval))

            interval_iteration += 1

    def test_load_from_string(self):
        with open(TEST_DOCUMENT_PATH, 'r') as test_file:
            raw_json = test_file.read()

        document = jsonquery.Document(raw_json)
        self.run_value_queries(document)

    def test_load_from_bytes(self):
        with open(TEST_DOCUMENT_PATH, 'rb') as test_file:
            raw_json = test_file.read()

        document = jsonquery.Document(raw_json)
        self.run_value_queries(document)

    def test_load_from_string_buffer(self):
        with open(TEST_DOCUMENT_PATH, 'r') as test_file:
            raw_json = test_file.read()

        buffer = io.StringIO()
        buffer.write(raw_json)
        buffer.seek(0)
        document = jsonquery.Document(buffer)
        self.run_value_queries(document)

    def test_load_from_bytes_buffer(self):
        with open(TEST_DOCUMENT_PATH, 'rb') as test_file:
            raw_json = test_file.read()

        buffer = io.BytesIO()
        buffer.write(raw_json)
        buffer.seek(0)
        document = jsonquery.Document(buffer)
        self.run_value_queries(document)

    def test_load_from_file(self):
        with open(TEST_DOCUMENT_PATH, 'r') as test_file:
            document = jsonquery.Document(test_file)

        self.run_value_queries(document)


if __name__ == '__main__':
    unittest.main()
