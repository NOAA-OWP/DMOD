import os.path
import unittest
import typing

from ...evaluations import specification
from ...evaluations import reader
from ...evaluations import util

from ..common import get_resource_path

TEST_DOCUMENT_PATH = str(get_resource_path("crosswalk.json"))


class TestJSONReading(unittest.TestCase):
    @classmethod
    def create_specification(cls) -> specification.CrosswalkSpecification:
        return specification.CrosswalkSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        address=TEST_DOCUMENT_PATH,
                        format="json"
                ),
                observation_field_name="observation_location",
                prediction_field_name="prediction_location",
                field=specification.ValueSelector(
                        name="prediction_location",
                        where="key",
                        path=["* where site_no"],
                        origin="$",
                        datatype="string",
                        associated_fields=[
                            specification.AssociatedField(
                                    name="observation_location",
                                    path="site_no",
                                    datatype="string"
                            )
                        ]
                )
        )

    def setUp(self) -> None:
        self.__crosswalk_specification = TestJSONReading.create_specification()

    def select_values(self, document: typing.Dict[str, typing.Any]):
        crosswalked_data = reader.select_values(document, self.__crosswalk_specification.field)

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
                        (crosswalked_data.observation_location == pair['observed'])
                        & (crosswalked_data.prediction_location == pair['predicted'])
                    ].empty
            )

    def run_value_queries(self, document: typing.Dict[str, typing.Any]):
        # Check to see if it can get the string for the address of the request
        self.select_values(document)

    def test_load_from_string(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            document = util.data_to_dictionary(test_file.read())
            self.run_value_queries(document)


    def test_load_from_bytes(self):
        with open(self.__crosswalk_specification.backend.address, 'rb') as test_file:
            document = util.data_to_dictionary(test_file.read())
            self.run_value_queries(document)


    def test_load_from_string_buffer(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            document = util.data_to_dictionary(test_file)
            self.run_value_queries(document)

    def test_load_from_bytes_buffer(self):
        with open(self.__crosswalk_specification.backend.address, 'rb') as test_file:
            document = util.data_to_dictionary(test_file)
            self.run_value_queries(document)

    def test_load_from_file(self):
        with open(self.__crosswalk_specification.backend.address, 'r') as test_file:
            document = util.data_to_dictionary(test_file)

        self.run_value_queries(document)


if __name__ == '__main__':
    unittest.main()
