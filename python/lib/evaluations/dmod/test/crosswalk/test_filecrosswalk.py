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
                fields=specification.ValueSelector(
                        name="predicted",
                        where="key",
                        path="*",
                        origin="$",
                        datatype="string"
                )
        )

    @classmethod
    def make_assertions(
            cls,
            test: unittest.TestCase,
            retriever: crosswalk.CrosswalkRetriever,
            expected_mapping: typing.List[typing.Dict[str, str]]
    ):
        pass

    def test_inferred_json_crosswalk(self):
        retriever = crosswalk.get_crosswalk(self.__json_specification)
        self.make_assertions(
                self,
                retriever,
                [
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
        )

    def test_explicit_json_crosswalk(self):
        retriever = crosswalk.disk.JSONRetriever(self.__json_specification)
        self.make_assertions(
                self,
                retriever,
                [
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
        )


if __name__ == '__main__':
    unittest.main()
