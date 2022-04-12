import typing
import os.path
import unittest

from ...evaluations import crosswalk
from ...evaluations import specification

TEST_DOCUMENT_PATH = os.path.join(os.path.dirname(__file__), "crosswalk.json")


class TestFileCrosswalk(unittest.TestCase):
    def setUp(self) -> None:
        self.__json_specification = specification.CrosswalkSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        address=TEST_DOCUMENT_PATH,
                        data_format="json"
                ),
                origin="",
                observation_field_name="observed",
                prediction_field_name="predicted",
                field=specification.ValueSelector(
                        name="predicted",
                        where="key",
                        path="*",
                        origin="$",
                        datatype="string",
                        associated_fields=[
                            specification.AssociatedField(
                                    name="observed",
                                    path="site_no"
                            )
                        ]
                )
        )

    @classmethod
    def make_assertions(
            cls,
            test: unittest.TestCase,
            retriever: crosswalk.CrosswalkRetriever,
            expected_mapping: typing.List[typing.Dict[str, str]]
    ):
        data = retriever.retrieve()
        print("Data Retrieved")

        test.assertEqual(len(data), len(expected_mapping))

        for mapping in expected_mapping:
            search_results = data[
                (data.predicted_location == mapping["predicted_location"])
                & (data.observed_location == mapping["observed_location"])
            ]

            test.assertFalse(search_results.empty)

    def test_inferred_json_crosswalk(self):
        retriever = crosswalk.get_crosswalk(self.__json_specification)
        self.make_assertions(
                self,
                retriever,
                [
                    {
                        "predicted_location": "cat-67",
                        "observed_location": "02146562"
                    },
                    {
                        "predicted_location": "cat-27",
                        "observed_location": "0214655255"
                    },
                    {
                        "predicted_location": "cat-52",
                        "observed_location": "0214657975"
                    }
                ]
        )

    def test_explicit_json_crosswalk(self):
        retriever = crosswalk.disk.JSONRetriever(self.__json_specification)
        self.make_assertions(
                self,
                retriever,
                [
                    {
                        "predicted_location": "cat-67",
                        "observed_location": "02146562"
                    },
                    {
                        "predicted_location": "cat-27",
                        "observed_location": "0214655255"
                    },
                    {
                        "predicted_location": "cat-52",
                        "observed_location": "0214657975"
                    }
                ]
        )


if __name__ == '__main__':
    unittest.main()
