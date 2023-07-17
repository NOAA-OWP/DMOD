import unittest
from ..scheduler.job.job import Job, JobImpl, RequestedJob
from dmod.core.meta_data import TimeRange
from dmod.communication import NWMRequest, NGENRequest, SchedulerRequestMessage
from typing import Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from dmod.communication import ModelExecRequest


class TestJob(unittest.TestCase):

    def setUp(self) -> None:
        self._example_jobs: List[Job] = []
        self._model_requests: List["ModelExecRequest"]= []
        self._model_requests_json: List[Any] = []

        # Example 0 - simple JobImpl instance based on NWMRequest for model_request value
        self._model_requests_json.append({
            "allocation_paradigm": "ROUND_ROBIN",
            "cpu_count": 1,
            "job_type": "nwm",
            "request_body": {
                "nwm": {
                    "config_data_id": "1",
                    "data_requirements": [
                        {
                            "category": "CONFIG",
                            "domain": {
                                "continuous": [],
                                "data_format": "NWM_CONFIG",
                                "discrete": [{"values": ["1"], "variable": "DATA_ID"}]
                            },
                            "is_input": True
                        }
                    ]
                }
            },
            "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"})
        self._model_requests.append(NWMRequest.factory_init_from_deserialized_json(self._model_requests_json[0]))
        self._example_jobs.append(JobImpl(cpu_count=1, memory_size=1000, model_request=self._model_requests[0],
                                          allocation_paradigm='single-node'))
        # Example 1 - Requested job based on NWMRequest
        self._model_requests_json.append({
            "allocation_paradigm": "ROUND_ROBIN",
            "cpu_count": 1,
            "job_type": "nwm",
            "request_body": {
                "nwm": {
                    "config_data_id": "2",
                    "data_requirements": [
                        {
                            "category": "CONFIG",
                            "domain": {
                                "continuous": [],
                                "data_format": "NWM_CONFIG",
                                "discrete": [{"values": ["2"], "variable": "DATA_ID"}]
                            },
                            "is_input": True
                        }
                    ]
                }
            },
            "session_secret": "123f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"
        })
        mod_req = NWMRequest.factory_init_from_deserialized_json(self._model_requests_json[1])
        scheduler_request = SchedulerRequestMessage(
            model_request=mod_req,
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='single-node')
        self._example_jobs.append(RequestedJob(job_request=scheduler_request))

        # Example 2 - NGENRequest based RequestedJob instance
        cpu_count_ex_2 = 4
        def create_time_range(begin, end, var=None) -> TimeRange:
            serialized = {'begin': begin, 'end': end, 'datetime_pattern': '%Y-%m-%d %H:%M:%S',
                          'subclass': TimeRange.__name__, 'variable': 'Time'}
            return TimeRange.factory_init_from_deserialized_json(serialized)

        time_range = create_time_range('2022-01-01 00:00:00', '2022-03-01 00:00:00')

        self._model_requests_json.append({
            "allocation_paradigm": "SINGLE_NODE",
            "cpu_count": cpu_count_ex_2,
            "job_type": "ngen",
            'request_body': {
                'bmi_config_data_id': '02468',
                'composite_config_data_id': 'composite02468',
                'hydrofabric_data_id': '9876543210',
                'hydrofabric_uid': '0123456789',
                'realization_config_data_id': '02468',
                'time_range': time_range.to_dict()
            },
            'session_secret': 'f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c'
        })
        mod_req_2 = NGENRequest.factory_init_from_deserialized_json(self._model_requests_json[2])
        scheduler_request = SchedulerRequestMessage(
            model_request=mod_req_2,
            user_id='someone',
            cpus=cpu_count_ex_2,
            mem=500000,
            allocation_paradigm='single-node')
        self._example_jobs.append(RequestedJob(job_request=scheduler_request))

    def tearDown(self) -> None:
        pass

    # Test that JobImpl serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_0_a(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job.__class__, deserialized_job.__class__)

    # Test that JobImpl serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_0_a_2(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(JobImpl, deserialized_job.__class__)

    # Test that JobImpl serialize deserializes to different object
    def test_factory_init_from_deserialized_json_0_b(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertFalse(base_job is deserialized_job)

    # Test that JobImpl serialize deserializes to equal object
    def test_factory_init_from_deserialized_json_0_c(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job, deserialized_job)

    # Test that RequestedJob serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_1_a(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job.__class__, deserialized_job.__class__)

    # Test that RequestedJob serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_1_a_2(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(RequestedJob, deserialized_job.__class__)

    # Test that RequestedJob serialize deserializes to different object
    def test_factory_init_from_deserialized_json_1_b(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertFalse(base_job is deserialized_job)

    # Test that RequestedJob serialize deserializes to equal object
    def test_factory_init_from_deserialized_json_1_c(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job, deserialized_job)

    def test_factory_init_from_deserialized_json_2_a(self):
        """
        Basic test of example 2.
        """
        example_index = 2

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job.__class__, deserialized_job.__class__)

    def test_factory_init_from_deserialized_json_2_b(self):
        """
        Test that data requirement `fulfilled_by` is not lost during deserialization.
        """
        example_index = 2

        base_job = self._example_jobs[example_index]

        index_val = 0
        for req in base_job.data_requirements:
            req.fulfilled_by = 'imaginary-dataset-{}'.format(index_val)
            index_val += 1

        for f in [req.fulfilled_by for req in base_job.data_requirements]:
            self.assertIsNotNone(f)

        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)

        for f in [req.fulfilled_by for req in deserialized_job.data_requirements]:
            self.assertIsNotNone(f)
