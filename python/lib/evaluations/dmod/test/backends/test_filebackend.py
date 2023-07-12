import typing
import os.path
import unittest
import json

from ...evaluations import backends
from ...evaluations.backends import file as file_backend
from ...evaluations import specification

from ..common import get_resource_path
from ..common import get_resource_directory

TEST_DOCUMENT_PATH = str(get_resource_path("nexus_data.geojson"))
TEST_DOCUMENT_REGEX = os.path.join(get_resource_directory(), ".+_data\.(geo)?json$")


def is_geojson(data: typing.Union[str, bytes, typing.Dict[str, typing.Any]]) -> bool:
    if data is None:
        return False

    try:
        if isinstance(data, bytes):
            data = data.decode()

        if isinstance(data, str):
            data = json.loads(data)

        if not isinstance(data, dict):
            return False

        if 'type' not in data or data['type'] != 'FeatureCollection':
            return False

        if 'features' not in data or not isinstance(data['features'], typing.Sequence):
            return False

        if len(data['features']) == 0:
            return True

        features = [
            feature
            for feature in data['features']
            if not isinstance(feature, dict)
        ]

        return len(features) == 0
    except:
        return False


class TestFileBackend(unittest.TestCase):
    @classmethod
    def create_direct_definition(cls) -> specification.BackendSpecification:
        return specification.BackendSpecification(
                backend_type="file",
                format="json",
                address=TEST_DOCUMENT_PATH
        )

    @classmethod
    def create_regex_definition(cls) -> specification.BackendSpecification:
        return specification.BackendSpecification(
                backend_type="file",
                format="json",
                address=TEST_DOCUMENT_REGEX
        )

    def setUp(self) -> None:
        self.__direct_definition = TestFileBackend.create_direct_definition()
        self.__regex_definition = TestFileBackend.create_regex_definition()

    def test_single_loading(self):
        direct_backend = file_backend.FileBackend(self.__direct_definition)
        self.run_assertions(
                self,
                direct_backend,
                [TEST_DOCUMENT_PATH]
        )

    def test_multi_loading(self):
        multi_backend = file_backend.FileBackend(self.__regex_definition)
        self.run_assertions(
                self,
                multi_backend,
                [
                    str(get_resource_path("nexus_data.geojson")),
                    str(get_resource_path("catchment_data.geojson")),
                    str(get_resource_path("flowpath_data.geojson"))
                ]
        )

    def test_inferred_single_loading(self):
        direct_backend = backends.get_backend(self.__direct_definition)
        self.run_assertions(
                self,
                direct_backend,
                [TEST_DOCUMENT_PATH]
        )

    def test_inferred_multi_loading(self):
        multi_backend = backends.get_backend(self.__regex_definition)
        self.run_assertions(
                self,
                multi_backend,
                [
                    str(get_resource_path("nexus_data.geojson")),
                    str(get_resource_path("catchment_data.geojson")),
                    str(get_resource_path("flowpath_data.geojson"))
                ]
        )

    @classmethod
    def run_assertions(
            cls,
            test: unittest.TestCase,
            backend: backends.Backend,
            expected_files: typing.Sequence[str]
    ):
        test.assertEqual(len(backend), len(expected_files))

        for expected_file in expected_files:
            test.assertIn(expected_file, backend)
            raw_data = backend.read(expected_file, store_data=False)

            stream = backend.read_stream(expected_file, store_data=True)
            stream_data = stream.read()
            test.assertEqual(raw_data, stream_data)

            raw_data = backend.read(expected_file)
            test.assertEqual(raw_data, stream_data)


if __name__ == '__main__':
    unittest.main()
