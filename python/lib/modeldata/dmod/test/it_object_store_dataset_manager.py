import git
import json
import os
import unittest
from ..modeldata.data.object_store_manager import Dataset, DatasetType, ObjectStoreDatasetManager
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DiscreteRestriction, TimeRange
from pathlib import Path
from typing import Optional, Set


class IntegrationTestObjectStoreDatasetManager(unittest.TestCase):

    _TEST_ENV_FILE_BASENAME = ".test_env"

    @classmethod
    def find_git_root_dir(cls, path: Optional[Path] = None) -> str:
        """
        Given a path (with ``None`` implying the current directory) assumed to be in a Git repo, find repo's root.

        Parameters
        ----------
        path : Path
            A file path within the project directory structure, or ``None`` to imply use the current directory.

        Returns
        -------
        str
            The string representation of the root directory for the Git repo containing the given path.

        Raises
        -------
        InvalidGitRepositoryError : If the given path is not within a Git repo.
        NoSuchPathError : If the given path is not valid.
        BadObject : If the given revision of the obtained ::class:`git.Repo` could not be found.
        ValueError : If the rev of the obtained ::class:`git.Repo` couldn't be parsed
        IndexError: If an invalid reflog index is specified.
        """
        if path is None:
            path = Path('.')
        git_repo = git.Repo(path, search_parent_directories=True)
        return git_repo.git.rev_parse("--show-toplevel")
    
    def __init__(self, *args, **kwargs):
        super(IntegrationTestObjectStoreDatasetManager, self).__init__(*args, **kwargs)
        self.manager: ObjectStoreDatasetManager = None
        self.minio_client = None

    def _initialize_manager(self, reset_existing: bool = True):
        """
        Initialize or reinitialize the ::attribute:`manager` and ::attribute:`minio_client` attributes for testing.
        
        Parameters
        ----------
        reset_existing : bool
            Whether new objects should be created, regardless of whether the attributes reference existing objects.
        """
        if reset_existing or self.manager is None:
            self.manager = ObjectStoreDatasetManager(obj_store_host_str='{}:{}'.format(self._hostname, self._port), 
                                                     access_key=self._access_key, secret_key=self._secret_key)
            self.minio_client = self.manager._client

    def setUp(self) -> None:
        # TODO: this is suppose to actually connect through the proxy, but there are issues with that currently
        # TODO: bypassing proxy for now and going straight to minio1, but that will need to be fixed
        self._port = int(os.environ.get('DMOD_OBJECT_STORE_PROXY_HOST_PORT', 9000))
        #self._port = int(os.environ.get('DMOD_OBJECT_STORE_1_HOST_PORT', 9002))
        self._hostname = 'localhost'

        self._secrets_dir: Path = Path(self.find_git_root_dir()).joinpath("docker/secrets/")
        self._access_key = self._secrets_dir.joinpath("object_store/model_exec_access_key").read_text()
        self._secret_key = self._secrets_dir.joinpath("object_store/model_exec_secret_key").read_text()

        # Initialize the manager and its backing minio client
        self._initialize_manager()

        # These are names of datasets we will need to clean up as part of teardown
        self._datasets_to_cleanup: Set[str] = set()

        self.examples = dict()

        # '%Y-%m-%d %H:%M:%S'
        time_range_1 = TimeRange.factory_init_from_deserialized_json(
            {'begin': '2022-01-01 00:00:00',
             'end': '2022-02-01 00:00:00',
             'variable': 'TIME',
             'subclass': 'TimeRange',
             'datetime_pattern': TimeRange.get_datetime_str_format()})
        domain_1 = DataDomain(data_format=DataFormat.AORC_CSV, continuous_restrictions=[time_range_1],
                              discrete_restrictions=[DiscreteRestriction("catchment_id", ['cat-1', 'cat-2', 'cat-3'])])
        # Remember that this is not example serialized JSON, but a dict that gets expanded into parameters passed to
        # the __init__ function for creating a manager
        self.examples[1] = {'name': 'test-ds-1', 'category': DataCategory.CONFIG, 'domain': domain_1,
                            'is_read_only': False}

    def tearDown(self) -> None:
        # Remove testing datasets slated to be cleaned up
        for dataset_name in self._datasets_to_cleanup:
            for obj in self.minio_client.list_objects(dataset_name):
                self.minio_client.remove_object(dataset_name, obj.object_name)
            self.minio_client.remove_bucket(dataset_name)

    def test_add_data_1_a(self):
        """ Test that a simple data add creates a new object as expected. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        dest_object_name = 'data_file'

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertNotIn(dest_object_name, self.manager.list_files(dataset_name))

        original_data = "File data contents"
        result = self.manager.add_data(dataset_name=dataset_name, dest=dest_object_name, data=original_data.encode())

        self.assertTrue(result)
        self.assertIn(dest_object_name, self.manager.list_files(dataset_name))

    def test_add_data_1_b(self):
        """ Test that a simple data add of raw data works correctly. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        dest_object_name = 'data_file'

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        original_data = "File data contents"
        self.manager.add_data(dataset_name=dataset_name, dest=dest_object_name, data=original_data.encode())
        raw_read_data = self.manager.get_data(dataset_name, item_name=dest_object_name)
        read_data = raw_read_data.decode()

        self.assertEqual(original_data, read_data)

    def test_add_data_1_c(self):
        """ Test that a data add of a file works correctly with specified dest. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        file_to_add = Path(self.find_git_root_dir()).joinpath('doc/GIT_USAGE.md')
        expected_name = 'GIT_USAGE.md'

        self.assertTrue(file_to_add.is_file())
        expected_data = file_to_add.read_bytes()

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.manager.add_data(dataset_name=dataset_name, dest=expected_name, source=str(file_to_add))
        raw_read_data = self.manager.get_data(dataset_name, item_name=expected_name)

        self.assertEqual(expected_data, raw_read_data)

    def test_add_data_1_d(self):
        """ Test that a data add of a directory of files works correctly with implied bucket root. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        dir_to_add = Path(self.find_git_root_dir()).joinpath('doc')

        # Note that if the project's doc dir is altered in certain ways, this may have to be manually updated
        self.assertTrue(dir_to_add.is_dir())
        one_files_name = 'GIT_USAGE.md'
        one_file = dir_to_add.joinpath(one_files_name)
        one_files_expected_data = one_file.read_bytes()
        num_uploaded_files = 0
        for p in dir_to_add.iterdir():
            if p.is_file():
                num_uploaded_files += 1
        # This is actually one more, because of the serialized dataset state file
        expected_num_files = num_uploaded_files + 1

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.manager.add_data(dataset_name=dataset_name, dest='', source=str(dir_to_add))
        actual_num_files = len(self.manager.list_files(dataset_name))

        self.assertEqual(expected_num_files, actual_num_files)

        raw_read_data = self.manager.get_data(dataset_name, item_name=one_files_name)

        self.assertEqual(one_files_expected_data, raw_read_data)

    def test_create_1_a(self):
        """
        Test that create works for a dataset that does not already exist.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertTrue(does_exist)

    def test_create_1_b(self):
        """
        Test that create writes the state serialization file to the newly created dataset.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        result = self.minio_client.get_object(bucket_name=dataset_name, object_name=serial_file_name)
        self.assertIsNotNone(result)

    def test_get_data_1_a(self):
        """ Test that we can get the serialized file for a newly created dataset. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        data = self.manager.get_data(dataset_name, item_name=serial_file_name)
        self.assertIsInstance(data, bytes)

    def test_get_data_1_b(self):
        """ Test that we can get the serialized file for a newly created dataset, and that it decodes. """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        data_dict = json.loads(self.manager.get_data(dataset_name, item_name=serial_file_name).decode())

        self.assertEqual(dataset_name, data_dict["name"])

    def test_list_files_1_a(self):
        """
        Test that list files includes the serialized file for a newly created dataset.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertTrue(serial_file_name in self.manager.list_files(dataset_name))

    def test_persist_serialized_1_a(self):
        """
        Test that serialized persistence works for new dataset after an extra, manual persist call.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.manager.persist_serialized(name=dataset_name)
        expected_obj_name = self.manager._gen_dataset_serial_obj_name(dataset_name)
        result = self.minio_client.get_object(bucket_name=dataset_name, object_name=expected_obj_name)
        self.assertIsNotNone(result)

    def test_persist_serialized_1_b(self):
        """
        Test that ``persist_serialized`` (during create) writes a serialization file that can be deserialized properly.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        data_dict = json.loads(self.manager.get_data(dataset_name, item_name=serial_file_name).decode())
        dataset = Dataset.factory_init_from_deserialized_json(data_dict)
        expected_dataset = self.manager.datasets[dataset_name]

        self.assertEqual(expected_dataset, dataset)

    def test_persist_serialized_1_c(self):
        """
        Test that serialized persistence works for new dataset and correctly saves dataset domain.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        serial_dataset_obj_name = self.manager._gen_dataset_serial_obj_name(dataset_name)
        response_obj = self.minio_client.get_object(bucket_name=dataset_name, object_name=serial_dataset_obj_name)
        response_data = json.loads(response_obj.data.decode())
        expected_domain = self.examples[ex_num]['domain']
        serialized_domain = DataDomain.factory_init_from_deserialized_json(response_data['data_domain'])
        self.assertEqual(expected_domain, serialized_domain)

    def test_persist_serialized_1_d(self):
        """
        Test that serialized persistence works for new dataset and correctly saves several other dataset attributes.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        expected_dataset = self.manager.datasets[dataset_name]
        serial_dataset_obj_name = self.manager._gen_dataset_serial_obj_name(dataset_name)
        response_obj = self.minio_client.get_object(bucket_name=dataset_name, object_name=serial_dataset_obj_name)
        response_data = json.loads(response_obj.data.decode())
        deserialized_dataset = Dataset.factory_init_from_deserialized_json(response_data)
        self.assertEqual(expected_dataset, deserialized_dataset)

    def test_persist_serialized_1_e(self):
        """
        Test that create writes a state serialization file that is loaded properly by a new manager instance.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self._initialize_manager(reset_existing=True)

        self.assertIn(dataset_name, self.manager.datasets)

    def test_persist_serialized_1_f(self):
        """
        Test that create writes a state serialization file that is loaded properly by a new manager instance.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        expected_dataset = self.manager.datasets[dataset_name]
        self._initialize_manager(reset_existing=True)
        dataset = self.manager.datasets[dataset_name]

        self.assertEqual(expected_dataset, dataset)

    def test_persist_serialized_1_g(self):
        """
        Test that create writes a state serialization file that is loaded properly by a new manager instance.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        serial_file_name = self.manager._gen_dataset_serial_obj_name(dataset_name)

        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        # Get the initial data from the serial file
        expected_data = self.manager.get_data(dataset_name, item_name=serial_file_name)
        # Create a new manager object, which should reload the dataset from the bucket and serial file
        self._initialize_manager(reset_existing=True)
        # Now load the data from the new manager
        DataFormat.NGEN_GEOJSON_HYDROFABRIC
        data = self.manager.get_data(dataset_name, item_name=serial_file_name)

        self.assertEqual(expected_data, data)

    def test_datasets_1_a(self):
        """
        Test that ``datasets`` property does not initially have testing dataset.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.assertFalse(dataset_name in self.manager.datasets)

    def test_datasets_1_b(self):
        """
        Test that ``datasets`` property shows dataset after it is created.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        all_datasets = self.manager.datasets
        self.assertFalse(dataset_name in self.manager.datasets)

        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertTrue(dataset_name in self.manager.datasets)

    def test_datasets_1_c(self):
        """
        Test that ``datasets`` property store actual dataset object of correct type after it is created.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.assertFalse(dataset_name in self.manager.datasets)

        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertEqual(self.manager.datasets[dataset_name].dataset_type, DatasetType.OBJECT_STORE)

    def test_datasets_1_d(self):
        """
        Test that ``datasets`` property store actual dataset object after it is created.
        """
        ex_num = 1
        dataset_name = self.examples[ex_num]['name']
        self.assertFalse(self.minio_client.bucket_exists(dataset_name))
        self.assertFalse(dataset_name in self.manager.datasets)

        self.manager.create(**self.examples[ex_num])
        does_exist = self.minio_client.bucket_exists(dataset_name)
        if does_exist:
            self._datasets_to_cleanup.add(dataset_name)

        self.assertEqual(self.manager.datasets[dataset_name].name, dataset_name)
        self.assertEqual(self.manager.datasets[dataset_name].category, self.examples[ex_num]['category'])

