import typing
import os.path
import unittest

from dmod.core.common.collections import catalog

from ...evaluations import crosswalk
from ...evaluations import specification

from ..common import get_resource_path

TEST_DOCUMENT_PATH = str(get_resource_path("crosswalk.json"))


class TestFileCrosswalk(unittest.TestCase):
    @classmethod
    def get_json_specification(cls) -> specification.CrosswalkSpecification:
        return specification.CrosswalkSpecification(
                backend=specification.BackendSpecification(
                        backend_type="file",
                        address=TEST_DOCUMENT_PATH,
                        format="json"
                ),
                origin="",
                observation_field_name="observation_location",
                prediction_field_name="prediction_location",
                field=specification.ValueSelector(
                        name="prediction_location",
                        where="key",
                        path="*",
                        origin="$",
                        datatype="string",
                        associated_fields=[
                            specification.AssociatedField(
                                    name="observation_location",
                                    path="site_no"
                            )
                        ]
                )
        )

    def setUp(self) -> None:
        self.json_specification: specification.CrosswalkSpecification = TestFileCrosswalk.get_json_specification()

    @classmethod
    def make_assertions(
            cls,
            test: unittest.TestCase,
            retriever: crosswalk.CrosswalkRetriever,
            expected_mapping: typing.List[typing.Dict[str, str]]
    ):
        data = retriever.retrieve()

        test.assertEqual(len(data), len(expected_mapping))

        for mapping in expected_mapping:
            search_results = data[
                (data[retriever.prediction_field_name] == mapping["predicted_location"])
                & (data[retriever.observation_field_name] == mapping["observed_location"])
            ]

            test.assertFalse(search_results.empty)

    def test_inferred_json_crosswalk(self):
        retriever = crosswalk.get_crosswalk(self.json_specification, catalog.InputCatalog())
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
        retriever = crosswalk.disk.JSONCrosswalkRetriever(self.json_specification, catalog.InputCatalog())
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
