import unittest
import git
import json

from dmod.communication.client import get_or_create_eventloop
from dmod.core.meta_data import DataCategory, DataDomain
from dmod.core.dataset import Dataset, DatasetType, DatasetManager
from dmod.scheduler.job import RequestedJob
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple

from ..dataservice.dataset_manager_collection import DatasetManagerCollection
from ..dataservice.dataset_inquery_util import DatasetInqueryUtil


class MockDataset(Dataset):

    @classmethod
    def additional_init_param_deserialized(cls, json_obj: dict) -> Dict[str, Any]:
        return dict()

    @property
    def docker_mount(self) -> str:
        return self.name


class MockDatasetManager(DatasetManager):

    def add_data(self, dataset_name: str, dest: str, data: Optional[bytes] = None, source: Optional[str] = None,
                 is_temp: bool = False, **kwargs) -> bool:
        pass

    def combine_partials_into_composite(self, dataset_name: str, item_name: str, combined_list: List[str]) -> bool:
        pass

    def create(self, name: str, category: DataCategory, domain: DataDomain, is_read_only: bool,
               initial_data: Optional[str] = None) -> Dataset:
        pass

    def delete(self, dataset: Dataset, **kwargs) -> bool:
        pass

    @property
    def data_chunking_params(self) -> Optional[Tuple[str, str]]:
        pass

    def get_data(self, dataset_name: str, item_name: str, **kwargs) -> Union[bytes, Any]:
        pass

    def list_files(self, dataset_name: str, **kwargs) -> List[str]:
        pass

    def reload(self, reload_from: str, serialized_item: Optional[str] = None) -> Dataset:
        pass

    @property
    def supported_dataset_types(self) -> Set[DatasetType]:
        return {DatasetType.FILESYSTEM}


class TestDataInqueryUtil(unittest.TestCase):

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
        super().__init__(*args, **kwargs)
        self._proj_root = None

    @property
    def proj_root(self) -> Path:
        if self._proj_root is None:
            err_msg = 'Unable to find project root; cannot continue setUp for {}'
            proj_root_str = self.find_git_root_dir()
            if proj_root_str is None:
                raise RuntimeError(err_msg.format(self.__class__.__name__))
            self._proj_root = Path(proj_root_str)
            if not self._proj_root.is_dir():
                raise RuntimeError(err_msg.format(self.__class__.__name__))
        return self._proj_root

    def setUp(self) -> None:
        self.loop = get_or_create_eventloop()
        self.example_jobs = []
        self.datasets: Dict[str, Dataset] = {}

        example_serial_datasets_dir = self.proj_root.joinpath('data').joinpath('serialized_dataset_examples')

        for df in (f for f in example_serial_datasets_dir.glob('*.json')):
            with df.open("r") as dataset_file:
                d = MockDataset.factory_init_from_deserialized_json(json.load(dataset_file))
                self.datasets[d.name] = d

        self.manager = MockDatasetManager(datasets=self.datasets)

        managers = DatasetManagerCollection()
        managers.add(self.manager)
        self.data_inquery_util = DatasetInqueryUtil(dataset_manager_collection=managers)

        # Example 0 - without fulfillment properties set before deserialization
        cpu_count_ex_0 = 8
        ex_json_0 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_0,
                "data_requirements": [
                    {
                        "category": "CONFIG",
                        "domain": {
                            "continuous": [],
                            "data_format": "BMI_CONFIG",
                            "discrete": [
                                {
                                    "values": [
                                        "simple-bmi-cfe-1"
                                    ],
                                    "variable": "DATA_ID"
                                }
                            ]
                        },
                        "is_input": True
                    },
                    {
                        "category": "FORCING",
                        "domain": {
                            "continuous": [
                                {
                                    "begin": "2012-05-01 00:00:00",
                                    "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                    "end": "2012-06-01 00:00:00",
                                    "subclass": "TimeRange",
                                    "variable": "TIME"
                                }
                            ],
                            "data_format": "AORC_CSV",
                            "discrete": [
                                {
                                    "values": [],
                                    "variable": "CATCHMENT_ID"
                                }
                            ]
                        },
                        "is_input": True
                    },
                    {
                        "category": "HYDROFABRIC",
                        "domain": {
                            "continuous": [],
                            "data_format": "NGEN_GEOJSON_HYDROFABRIC",
                            "discrete": [
                                {
                                    "values": [
                                        "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81"
                                    ],
                                    "variable": "HYDROFABRIC_ID"
                                },
                                {
                                    "values": [
                                        "huc01-hydrofabric-2021-10-28-part-8"
                                    ],
                                    "variable": "DATA_ID"
                                }
                            ]
                        },
                        "is_input": True
                    },
                    {
                        "category": "CONFIG",
                        "domain": {
                            "continuous": [],
                            "data_format": "NGEN_PARTITION_CONFIG",
                            "discrete": [
                                {
                                    "values": [
                                        "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81"
                                    ],
                                    "variable": "HYDROFABRIC_ID"
                                },
                                {
                                    "values": [
                                        8
                                    ],
                                    "variable": "LENGTH"
                                }
                            ]
                        },
                        "is_input": True
                    },
                    {
                        "category": "CONFIG",
                        "domain": {
                            "continuous": [
                                {
                                    "begin": "2012-05-01 00:00:00",
                                    "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                    "end": "2012-06-01 00:00:00",
                                    "subclass": "TimeRange",
                                    "variable": "TIME"
                                }
                            ],
                            "data_format": "NGEN_REALIZATION_CONFIG",
                            "discrete": [
                                {
                                    "values": [],
                                    "variable": "CATCHMENT_ID"
                                },
                                {
                                    "values": [
                                        "huc01-simple-config-1"
                                    ],
                                    "variable": "DATA_ID"
                                }
                            ]
                        },
                        "is_input": True
                    }
                ],
                "job_class": "RequestedJob",
                "job_id": "57d251f5-ab45-4e9f-8776-081d36e10c8f",
                "last_updated": "2022-05-12 12:48:19",
                "memory_size": 500000,
                "originating_request": {
                    "allocation": "SINGLE_NODE",
                    "cpus": 4,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_0,
                        "job_type": "ngen",
                        "session_secret": "381191cc9b5917b4fb7135e12915dd36513d0483c3c3890bc331a7346cda1cb1",
                        "request_body": {
                            "bmi_config_data_id": "simple-bmi-cfe-1",
                            "realization_config_data_id": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81",
                            "config_data_id": "huc01-simple-config-1",
                            "hydrofabric_data_id": "huc01-hydrofabric-2021-10-28-part-8",
                            "hydrofabric_uid": "72c2a0220aa7315b50e55b6c5b68f927ac1d9b81",
                            "time_range": {
                                "begin": "2012-05-01 00:00:00",
                                "datetime_pattern": "%Y-%m-%d %H:%M:%S",
                                "end": "2012-06-01 00:00:00",
                                "subclass": "TimeRange",
                                "variable": "TIME"
                            }
                        }
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }

        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_0))

    def test_can_be_fulfilled_0_a(self):
        """ Test function against first job requirement for example 0 (requires all datasets, no preset fulfills). """
        ex_num = 0
        requirement_index = 0

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(
            self.data_inquery_util.can_be_fulfilled(job.data_requirements[requirement_index]))

        self.assertTrue(result[0])
