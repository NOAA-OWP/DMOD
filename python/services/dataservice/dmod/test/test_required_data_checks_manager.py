import unittest
import git
import json
import os

from ..dataservice.dataset_manager_collection import DatasetManagerCollection
from ..dataservice.dataset_inquery_util import DatasetInqueryUtil
from ..dataservice.service import Count, RequiredDataChecksManager
from dmod.communication.client import get_or_create_eventloop
from dmod.core.dataset import DataCategory, DataDomain, Dataset, DatasetManager, DatasetType
from dmod.scheduler.job import RequestedJob
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


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


class TestRequiredDataChecksManager(unittest.TestCase):

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
        return git.Repo(__file__, search_parent_directories=True).working_dir

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._proj_root = None
        self._ssl_certs_dir = None

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

        example_serial_datasets_dir = self.proj_root.joinpath('data').joinpath('serialized_dataset_examples')

        datasets: Dict[str, Dataset] = dict()
        for d_file in example_serial_datasets_dir.glob('*.json'):
            with d_file.open("r") as open_file:
                dataset: Dataset = MockDataset.factory_init_from_deserialized_json(json.load(open_file))
                datasets[dataset.name] = dataset
        dataset_manager_collection = DatasetManagerCollection()
        dataset_manager_collection.add(MockDatasetManager(datasets=datasets))

        dataset_inquery_util = DatasetInqueryUtil(dataset_manager_collection=dataset_manager_collection)

        self.manager = RequiredDataChecksManager(
            job_util=None,
            dataset_manager_collection=dataset_manager_collection,
            count=Count(),
            dataset_inquery_util=dataset_inquery_util,
        )

        self.example_jobs = []

        # Example 0 - just requiring forcing dataset
        cpu_count_ex_0 = 8
        ex_json_0 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_0,
                "data_requirements": [
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
                        "fulfilled_by": "huc01-forcings-demo-1",
                        "fulfilled_access_at": "huc01-forcings-demo-1",
                        "is_input": True
                    }
                ],
                "job_class": "RequestedJob",
                "job_id": "57d251f5-ab45-4e9f-8776-081d36e10c8f",
                "last_updated": "2022-05-12 12:48:19",
                "memory_size": 500000,
                "originating_request": {
                    "allocation": "SINGLE_NODE",
                    "cpus": cpu_count_ex_0,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_0))

        # Example 1 - just BMI config dataset
        cpu_count_ex_1 = 8
        ex_json_1 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_1,
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
                        "fulfilled_by": "simple-bmi-cfe-1",
                        "fulfilled_access_at": "simple-bmi-cfe-1",
                        "is_input": True
                    }
                ],
                "job_class": "RequestedJob",
                "job_id": "57d251f5-ab45-4e9f-8776-081d36e10c8f",
                "last_updated": "2022-05-12 12:48:19",
                "memory_size": 500000,
                "originating_request": {
                    "allocation": "SINGLE_NODE",
                    "cpus": cpu_count_ex_1,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_1,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_1))

        # Example 2 - just hydrofabric dataset
        cpu_count_ex_2 = 8
        ex_json_2 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_2,
                "data_requirements": [
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
                        "fulfilled_by": "huc01-hydrofabric-2021-10-28-part-8",
                        "fulfilled_access_at": "huc01-hydrofabric-2021-10-28-part-8",
                        "is_input": True
                    }
                ],
                "job_class": "RequestedJob",
                "job_id": "57d251f5-ab45-4e9f-8776-081d36e10c8f",
                "last_updated": "2022-05-12 12:48:19",
                "memory_size": 500000,
                "originating_request": {
                    "allocation": "SINGLE_NODE",
                    "cpus": cpu_count_ex_2,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_2,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_2))

        # Example 3 - just partitioning config dataset
        cpu_count_ex_3 = 8
        ex_json_3 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_3,
                "data_requirements": [
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
                    }
                ],
                "job_class": "RequestedJob",
                "job_id": "57d251f5-ab45-4e9f-8776-081d36e10c8f",
                "last_updated": "2022-05-12 12:48:19",
                "memory_size": 500000,
                "originating_request": {
                    "allocation": "SINGLE_NODE",
                    "cpus": cpu_count_ex_3,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_3,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_3))

        # Example 4 - just realization config dataset
        cpu_count_ex_4 = 8
        ex_json_4 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_4,
                "data_requirements": [
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
                    "cpus": cpu_count_ex_4,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_4,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_4))

        # Example 5 - requiring all 5 sample datasets
        cpu_count_ex_5 = 8
        ex_json_5 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_5,
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
                        "fulfilled_by": "simple-bmi-cfe-1",
                        "fulfilled_access_at": "simple-bmi-cfe-1",
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
                        "fulfilled_by": "huc01-forcings-demo-1",
                        "fulfilled_access_at": "huc01-forcings-demo-1",
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
                        "fulfilled_by": "huc01-hydrofabric-2021-10-28-part-8",
                        "fulfilled_access_at": "huc01-hydrofabric-2021-10-28-part-8",
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
                    "cpus": cpu_count_ex_5,
                    "mem": 500000,
                    "model_request": {
                        "allocation_paradigm": "SINGLE_NODE",
                        "cpu_count": cpu_count_ex_5,
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
                        },
                    },
                    "user_id": "someone"
                },
                "status": "MODEL_EXEC:AWAITING_DATA_CHECK"
            }
        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_5))

        # Example 6 - requiring all 5 sample datasets, but without fulfillment properties set before deserialization
        cpu_count_ex_6 = 8
        ex_json_6 = \
            {
                "allocation_paradigm": "SINGLE_NODE",
                "allocation_priority": 0,
                "cpu_count": cpu_count_ex_6,
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
                        "cpu_count": cpu_count_ex_5,
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

        self.example_jobs.append(RequestedJob.factory_init_from_deserialized_json(ex_json_6))

    @property
    def ssl_certs_dir(self):
        if self._ssl_certs_dir is None:
            test_dir_name = os.getenv('DMOD_TEST_SSL_CERT_DIR')
            if test_dir_name is not None:
                self._ssl_certs_dir = Path(test_dir_name).resolve()

            # But if this isn't a valid, search the new way
            if self._ssl_certs_dir is None or not self._ssl_certs_dir.is_dir():
                # Find the project root to then get the SSL dir
                self._ssl_certs_dir = self.proj_root.joinpath('ssl').joinpath('local')
                # If still not valid, then we are hosed
                if not self._ssl_certs_dir.is_dir():
                    msg = 'Unable to find test SSL certs directory; cannot continue setUp for {}'
                    raise RuntimeError(msg.format(self.__class__.__name__))
        return self._ssl_certs_dir

    def test_perform_checks_for_job_0_a(self):
        """ Test whether check for fulfilling job requirements for example 0 (requires forcing dataset). """
        ex_num = 0

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)

    def test_perform_checks_for_job_1_a(self):
        """ Test whether check for fulfilling job requirements for example 1 (requires BMI config dataset). """
        ex_num = 1

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)

    def test_perform_checks_for_job_2_a(self):
        """ Test whether check for fulfilling job requirements for example 2 (requires hydrofabric dataset). """
        ex_num = 2

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)

    def test_perform_checks_for_job_3_a(self):
        """ Test whether check for fulfilling job requirements for example 3 (requires partition config dataset). """
        ex_num = 3

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)

    def test_perform_checks_for_job_4_a(self):
        """ Test whether check for fulfilling job requirements for example 4 (requires realization config dataset). """
        ex_num = 4

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)

    def test_perform_checks_for_job_5_a(self):
        """ Test whether check for fulfilling job requirements for example 5 (requires all datasets). """
        ex_num = 5

        job = self.example_jobs[ex_num]
        result = self.loop.run_until_complete(self.manager.perform_checks_for_job(job))

        self.assertTrue(result)
