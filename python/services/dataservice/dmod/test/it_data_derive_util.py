import unittest
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from dmod.core.meta_data import DataCategory
from dmod.modeldata.data.object_store_manager import ObjectStoreDatasetManager
from dmod.dataservice.dataset_manager_collection import DatasetManagerCollection
from ..dataservice.data_derive_util import DataDeriveUtil
from typing import List, Optional


class TestBase:

    _TEST_ENV_FILE_BASENAME = ".test_env"

    @classmethod
    def find_project_root(cls, path: Optional[Path] = None) -> Path:
        if path is None:
            path = Path('.').resolve()
        original = path
        while True:
            if path.is_dir() and path.joinpath("example.env").exists() and path.joinpath("docker").exists():
                return path
            elif path == path.anchor:
                break
            else:
                path = path.parent
        raise RuntimeError(f"Can't identify project root starting from {original!s}")

    @classmethod
    def source_test_env_file(cls):
        # Find the global .test_env file from project root, and source
        proj_root = cls.find_project_root()
        test_env = proj_root.joinpath(cls._TEST_ENV_FILE_BASENAME)

        if test_env.exists():
            load_dotenv(dotenv_path=str(test_env))


TestBase.source_test_env_file()
explicit_on = os.environ.get("DERIVE_UTIL_IT_ON", "false").strip().lower() == "true"
reason_str = (f"IntegrationTestDataDeriveUtil tests skipped locally; you can activate by setting 'DERIVE_UTIL_IT_ON' "
              f"to 'true' in your project '{TestBase._TEST_ENV_FILE_BASENAME}' file.")
skip_unless_explicit = unittest.skipUnless(explicit_on, reason=reason_str)


@skip_unless_explicit
class IntegrationTestDataDeriveUtil(TestBase, unittest.TestCase):

    _minio_client = None
    _noah_params_dir: Path = None
    _proj_root: Path = None
    _obj_store_manager: ObjectStoreDatasetManager = None
    _secrets_dir: Path = None
    _real_ds_name: str = None
    _hf_ds_name: str = None
    _class_ds_to_clean_up: List[str] = []

    @classmethod
    def _create_real_cfg_dataset(cls) -> str:
        """
        Create the realization config dataset needed for this class's tests.

        Returns
        -------
        str
            The name of the created dataset.
        """
        expected_name = "derive-testing-realization-config-01"
        if expected_name in cls._obj_store_manager.datasets:
            return expected_name

        from dmod.modeldata.data.item_domain_detector import RealizationConfigDomainDetector
        from ..dataservice.initial_data_adder_impl import FromRawInitialDataAdder

        cfg_file = cls._proj_root.joinpath("data/example_realization_configs/ex_realization_config_04.json")
        detector = RealizationConfigDomainDetector(item=cfg_file)
        domain = detector.detect()
        adder = FromRawInitialDataAdder(dataset_name=expected_name, dataset_manager=cls._obj_store_manager,
                                        data_items={"realization_config.json": cfg_file.read_bytes()})
        real_ds = cls._obj_store_manager.create(name=expected_name, category=DataCategory.CONFIG, domain=domain,
                                                is_read_only=True, initial_data=adder)

        cls._class_ds_to_clean_up.append(real_ds.name)

        return real_ds.name

    @classmethod
    def _create_hydrofabric_dataset(cls):
        """
        Create the hydrofabric dataset needed for this class's tests.

        Returns
        -------
        str
            The name of the created dataset.
        """
        expected_name = "nextgen-01"
        if expected_name in cls._obj_store_manager.datasets:
            return expected_name
        # TODO: implement properly
        raise NotImplementedError(f"Automated setup of hydrofabric dataset for {cls.__name__} not implemented; manually"
                                  f"create dataset named '{expected_name}' from VPU01 data to enable testing")

    @classmethod
    def setUpClass(cls):
        """
        Perform class-level test setup.

        In particular, this involves setting attributes related to the ObjectStoreDatasetManager used by the tests, so
        that it only has to look for and reload datasets once.  This allows an existing deployment's object store to be
        used for simplicity.
        """
        cls.source_test_env_file()
        obj_store_host = os.environ.get("DMOD_OBJECT_STORE_PROXY_HOSTNAME", "localhost")
        obj_store_port = int(os.environ.get('DMOD_OBJECT_STORE_PROXY_HOST_PORT', 9000))

        cls._proj_root = cls.find_project_root()
        cls._noah_params_dir = cls._proj_root.joinpath("docker/main/ngen/noah_owp_parameters")
        cls._secrets_dir = cls._proj_root.joinpath("docker/secrets/")

        access_key = os.environ.get("MODEL_EXEC_ACCESS_KEY",
                                    cls._secrets_dir.joinpath("object_store/model_exec_access_key").read_text()
                                    ).strip()
        assert access_key is not None, "'MODEL_EXEC_ACCESS_KEY' environment variable or 'docker/secrets/object_store/model_exec_access_key' file is required"

        secret_key = os.environ.get("MODEL_EXEC_SECRET_KEY",
                                    cls._secrets_dir.joinpath("object_store/model_exec_secret_key").read_text()
                                    ).strip()
        assert secret_key is not None, "'MODEL_EXEC_SECRET_KEY' environment variable or 'docker/secrets/object_store/model_exec_secret_key' file is required"

        cls._obj_store_manager = ObjectStoreDatasetManager(obj_store_host_str=f"{obj_store_host}:{obj_store_port!s}",
                                                           access_key=access_key,
                                                           secret_key=secret_key)

        cls._real_ds_name = cls._create_real_cfg_dataset()
        cls._hf_ds_name = cls._create_hydrofabric_dataset()

    @classmethod
    def tearDownClass(cls):
        for ds in [cls._obj_store_manager.datasets[d] for d in cls._class_ds_to_clean_up]:
            ds.manager.delete(ds)

    def setUp(self):
        self.dataset_manager_collection = DatasetManagerCollection()
        self.dataset_manager_collection.add(self._obj_store_manager)

        self.test_1_bmi_ds_name = "test-bmi-generated-ds-01"

        if self.test_1_bmi_ds_name in self._obj_store_manager.datasets:
            self._obj_store_manager.delete(self._obj_store_manager.datasets[self.test_1_bmi_ds_name])

        self.derive_util = DataDeriveUtil(dataset_manager_collection=self.dataset_manager_collection,
                                          noah_owp_params_dir=str(self._noah_params_dir))
        self.ds_to_cleanup: List[str] = []

    def tearDown(self):
        for ds_name in self.ds_to_cleanup:
            ds = self.dataset_manager_collection.known_datasets().get(ds_name)
            if ds is None:
                continue
            ds.manager.delete(dataset=ds)

    @skip_unless_explicit
    def test__generate_bmi_ds_1_a(self):
        """ Test to see if auto-generation of BMI config dataset will work as expected in object store dataset. """
        ds_name = self.test_1_bmi_ds_name

        real_ds_name = self._real_ds_name
        hf_ds_name = self._hf_ds_name

        t1 = datetime.now()
        print(f"\nStarted Dataset Generation: {t1!s}")
        dataset = self.derive_util._generate_bmi_ds(bmi_ds_name=ds_name,
                                                    bmi_ds_mgr=self._obj_store_manager,
                                                    hydrofabric_ds_name=hf_ds_name,
                                                    realization_cfg_ds_name=real_ds_name)
        t2 = datetime.now()

        self.ds_to_cleanup.append(ds_name)

        print(f"Finished Dataset Generation: {t2!s}")
        interval = t2 - t1
        print(f"Generation Task Interval: {interval!s}")
        self.assertTrue(dataset.name in self.dataset_manager_collection.known_datasets())

        managed_ds = self.dataset_manager_collection.known_datasets()[ds_name]

        ds_files = managed_ds.manager.list_files(ds_name)

        self.assertEqual(len(ds_files), 2)
        self.assertIn(managed_ds.archive_name, ds_files)


