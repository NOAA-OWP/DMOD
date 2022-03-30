import os.path
import unittest
import typing
import io

from ...evaluations import specification
from ...evaluations.crosswalk import reader
from ...evaluations import jsonquery

TEST_DOCUMENT_PATH = os.path.join(os.path.dirname(__file__), "crosswalk.json")


class TestJSONReading(unittest.TestCase):
    def setUp(self) -> None:
        self.__crosswalk_specification = specification.CrosswalkSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        address=TEST_DOCUMENT_PATH,
                        data_format="json"
                ),
                fields=specification.ValueSelector(
                        name="predicted",
                        where="key",
                        path=["* where site_no"],
                        origin="$",
                        datatype="string",
                        associated_fields=[
                            specification.AssociatedField(
                                    name="observed",
                                    path="site_no",
                                    datatype="string"
                            )
                        ]
                )
        )

    def select_values(self, document: jsonquery.Document):
        crosswalked_data = reader.select_values(document.data, self.__crosswalk_specification.fields)

        crosswalked_data.dropna(inplace=True)
        self.assertEqual(len(crosswalked_data), 3)

        correct_pairs = [
            {
                "predicted": "cat-67",
                "observed": "02146562"
            },
            {
                "predicted": "cat-27",
                "observed": "0214655255"
            },
            {
                "predicted": "cat-52",
                "observed": "0214657975"
            }
        ]

        for pair in correct_pairs:
            self.assertFalse(
                    crosswalked_data[
                        (crosswalked_data.observed == pair['observed'])
                        & (crosswalked_data.predicted == pair['predicted'])
                    ].empty
            )

    def run_value_queries(self, document: jsonquery.Document):
        # Check to see if it can get the string for the address of the request
        self.select_values(document)

    def test_load_from_string(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            raw_json = test_file.read()

        document = jsonquery.Document(raw_json)
        self.run_value_queries(document)

    def test_load_from_bytes(self):
        with open(self.__crosswalk_specification.backend.address, 'rb') as test_file:
            raw_json = test_file.read()

        document = jsonquery.Document(raw_json)
        self.run_value_queries(document)

    def test_load_from_string_buffer(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            raw_json = test_file.read()

        buffer = io.StringIO()
        buffer.write(raw_json)
        buffer.seek(0)
        document = jsonquery.Document(buffer)
        self.run_value_queries(document)

    def test_load_from_bytes_buffer(self):
        with open(self.__crosswalk_specification.backend.address, 'rb') as test_file:
            raw_json = test_file.read()

        buffer = io.BytesIO()
        buffer.write(raw_json)
        buffer.seek(0)
        document = jsonquery.Document(buffer)
        self.run_value_queries(document)

    def test_load_from_file(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            document = jsonquery.Document(test_file)

        self.run_value_queries(document)


if __name__ == '__main__':
    unittest.main()
