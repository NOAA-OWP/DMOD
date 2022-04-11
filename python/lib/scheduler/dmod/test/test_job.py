import unittest
from ..scheduler.job.job import Job, JobImpl, RequestedJob
from dmod.communication import NWMRequest, SchedulerRequestMessage


class TestJob(unittest.TestCase):

    def setUp(self) -> None:
        self._example_jobs = []
        model_request_0 = NWMRequest.factory_init_from_deserialized_json(
            {"model": {"nwm": {"config_data_id": "1", "data_requirements": [{"domain": {
                "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["1"]}]},
                "is_input": True,
                "category": "CONFIG"}]}},
             "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"})
        self._example_jobs.append(JobImpl(cpu_count=4, memory_size=1000, model_request=model_request_0,
                                          allocation_paradigm='single-node'))

        scheduler_request = SchedulerRequestMessage(
            model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"config_data_id": "2", "data_requirements": [{"domain": {
                    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["2"]}]},
                    "is_input": True,
                    "category": "CONFIG"}]}},
                 "session-secret": "123f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='single-node')
        self._example_jobs.append(RequestedJob(job_request=scheduler_request))

    def tearDown(self) -> None:
        pass

    # Test that JobImpl serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_1_a(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job.__class__, deserialized_job.__class__)

    # Test that JobImpl serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_1_a_2(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(JobImpl, deserialized_job.__class__)

    # Test that JobImpl serialize deserializes to different object
    def test_factory_init_from_deserialized_json_1_b(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertFalse(base_job is deserialized_job)

    # Test that JobImpl serialize deserializes to equal object
    def test_factory_init_from_deserialized_json_1_c(self):
        example_index = 0

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job, deserialized_job)

    # Test that RequestedJob serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_2_a(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job.__class__, deserialized_job.__class__)

    # Test that RequestedJob serialize deserializes to correct type
    def test_factory_init_from_deserialized_json_2_a_2(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(RequestedJob, deserialized_job.__class__)

    # Test that RequestedJob serialize deserializes to different object
    def test_factory_init_from_deserialized_json_2_b(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertFalse(base_job is deserialized_job)

    # Test that RequestedJob serialize deserializes to equal object
    def test_factory_init_from_deserialized_json_2_c(self):
        example_index = 1

        base_job = self._example_jobs[example_index]
        serialized_job = base_job.to_dict()
        deserialized_job = Job.factory_init_from_deserialized_json(serialized_job)
        self.assertEqual(base_job, deserialized_job)

