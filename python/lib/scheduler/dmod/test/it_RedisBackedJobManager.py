import os
import unittest
from ..scheduler.job.job import Job, JobStatus, JobExecPhase, JobExecStep, RequestedJob, SchedulerRequestMessage
from ..scheduler.job.job_manager import RedisBackedJobManager
from ..scheduler.rsa_key_pair import RsaKeyPair
from . import MockResourceManager, mock_resources
from dmod.communication import NWMRequest
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID


# TODO: also add another test for the job manager factory and its factory method

try:
    import pytest
    import os
    # https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables
    in_ci = os.environ.get("CI", False) == "true"
    skip_in_ci = pytest.mark.skipif(in_ci, reason="Tests require access to Docker Daemon. Do not have access to Docker Daemon in GH Actions.")
except ImportError:
    def skip_in_ci(fn):
        return fn


@skip_in_ci
class IntegrationTestRedisBackedJobManager(unittest.TestCase):

    _TEST_ENV_FILE_BASENAME = ".test_env"

    @classmethod
    def find_project_root_directory(cls, current_directory: Optional[Path]) -> Optional[Path]:
        """
        Given a directory (with ``None`` implying the current directory) assumed to be at or under this project's root,
        find the project root directory.

        This implementation attempts to find a directory having both a ``.git/`` child directory and a ``.env`` file.

        Parameters
        ----------
        current_directory

        Returns
        -------
        Optional[Path]
            The project root directory, or ``None`` if it fails to find it.
        """
        abs_root = Path(current_directory.absolute().root)
        while current_directory.absolute() != abs_root:
            if not current_directory.is_dir():
                current_directory = current_directory.parent
                continue
            git_sub_dir = current_directory.joinpath('.git')
            child_env_file = current_directory.joinpath('.env')
            if git_sub_dir.exists() and git_sub_dir.is_dir() and child_env_file.exists() and child_env_file.is_file():
                return current_directory
            current_directory = current_directory.parent
        return None

    @classmethod
    def source_env_files(cls, env_file_basename: str):
        current_dir = Path().absolute()

        # Find the global .test_env file from project root, and source
        proj_root = cls.find_project_root_directory(current_dir)
        if proj_root is None:
            raise RuntimeError("Error: unable to find project root directory for integration testing.")

        global_test_env = proj_root.joinpath(env_file_basename)
        if global_test_env.exists():
            load_dotenv(dotenv_path=str(global_test_env.absolute()))

        # Also, search for any other .test_env files, but only source if they are in the same directory as this file
        this_test_file_parent_directory = Path(__file__).parent.absolute()
        for test_env_file in proj_root.glob('**/' + env_file_basename):
            if test_env_file.parent.absolute() == this_test_file_parent_directory:
                load_dotenv(dotenv_path=str(test_env_file))
                # Also, since there can be only one, go ahead and return here
                break

    @classmethod
    def source_env_property(cls, env_var_name: str):
        value = os.getenv(env_var_name, None)
        if value is None:
            cls.source_env_files(cls._TEST_ENV_FILE_BASENAME)
            value = os.getenv(env_var_name, None)
        return value

    def __init__(self, methodName='runTest'):
        super().__init__(methodName=methodName)
        self._redis_test_pass = None
        self._redis_test_port = None
        self._rsa_key_pairs: List[RsaKeyPair] = [None]

    def _create_example_job_for_index(self, example_index: int):
        request = self._sample_job_requests[example_index]
        uuid_str = self._uuid_str_vals[example_index]
        uuid_val = UUID(uuid_str)
        job = RequestedJob(request)
        job.set_job_id(uuid_val)

        self._generate_rsa_keys()
        # Only do this when not None
        if self._rsa_key_pairs[example_index] is not None:
            job.set_rsa_key_pair(self._rsa_key_pairs[example_index])
        return job

    def _exec_job_manager_create_from_expected(self, example_index: int) -> Tuple[Job, Job]:
        """
        Create a pair of job objects from the "expected" example set at the particular index, using the job manager
        member to create the persisted job object, and returning the ``expected`` and ``created`` objects as a tuple.

        Parameters
        ----------
        example_index: int
            The index of the particular example from the example set that should be used/created.

        Returns
        -------
        Tuple[Job, Job]
            The manually-initialized ``expected`` job and the job-manager-created ``saved`` job, in that order.
        """
        expected_job = self._create_example_job_for_index(example_index)
        saved_job = self._job_manager.create_job(request=expected_job.originating_request, job_id=expected_job.job_id)
        return expected_job, saved_job

    def _generate_rsa_keys(self):
        self._rsa_key_pairs.append(RsaKeyPair(directory='.', name='test_rsa_key_1'))
        self._rsa_key_pairs.append(RsaKeyPair(directory='.', name='test_rsa_key_2'))
        self._rsa_key_pairs.append(RsaKeyPair(directory='.', name='test_rsa_key_3'))

    @property
    def redis_test_pass(self):
        if not self._redis_test_pass:
            self._redis_test_pass = self.source_env_property('IT_REDIS_CONTAINER_PASS')
        return self._redis_test_pass

    @property
    def redis_test_port(self):
        if not self._redis_test_port:
            self._redis_test_port = self.source_env_property('IT_REDIS_CONTAINER_HOST_PORT')
        return self._redis_test_port

    def setUp(self) -> None:
        self._resource_manager = MockResourceManager()
        self._resource_manager.set_resources(mock_resources())
        # TODO: make sure this doesn't cause a problem
        self._launcher = None

        self._sample_job_requests = []
        self._sample_job_requests.append(SchedulerRequestMessage(
            model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"config_data_id": "0", "data_requirements": [{"domain": {
                    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["0"]}]},
                    "is_input": True,
                    "category": "CONFIG"}]}},
                "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='single-node'))

        self._sample_job_requests.append(SchedulerRequestMessage(
            model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"config_data_id": "1", "data_requirements": [{"domain": {
                    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["1"]}]},
                    "is_input": True,
                    "category": "CONFIG"}]}},
                 "session_secret": "123f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='single-node'))

        # indexes 2 and 3 are the same as the job at index 0, except with the two other allocation paradigms
        self._sample_job_requests.append(SchedulerRequestMessage(
            model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"config_data_id": "2", "data_requirements": [{"domain": {
                    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["2"]}]},
                    "is_input": True,
                    "category": "CONFIG"}]}},
                 "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='fill-nodes'))

        self._sample_job_requests.append(SchedulerRequestMessage(
            model_request=NWMRequest.factory_init_from_deserialized_json(
                {"model": {"nwm": {"config_data_id": "3", "data_requirements": [{"domain": {
                    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["3"]}]},
                    "is_input": True,
                    "category": "CONFIG"}]}},
                 "session_secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}),
            user_id='someone',
            cpus=4,
            mem=500000,
            allocation_paradigm='round-robin'))

        self._uuid_str_vals = []
        #self._uuid_str_vals.append('12345678-1234-5678-1234-567812345678')
        self._uuid_str_vals.append('00000000-0000-0000-0000-000000000000')
        self._uuid_str_vals.append('00000000-0000-0000-0000-000000000001')
        self._uuid_str_vals.append('00000000-0000-0000-0000-000000000002')
        self._uuid_str_vals.append('00000000-0000-0000-0000-000000000003')

        # TODO: set these correctly
        self.redis_test_host = '127.0.0.1'

        self._env_type = 'test'
        self._job_manager = RedisBackedJobManager(resource_manager=self._resource_manager,
                                                  launcher=self._launcher,
                                                  redis_host=self.redis_test_host,
                                                  redis_port=self.redis_test_port,
                                                  redis_pass=self.redis_test_pass,
                                                  type=self._env_type)

    def tearDown(self) -> None:
        for key_pair in self._rsa_key_pairs:
            if key_pair is not None:
                if key_pair.private_key_file.exists():
                    key_pair.private_key_file.unlink()
                if key_pair.public_key_file.exists():
                    key_pair.public_key_file.unlink()

        self._job_manager._clean_keys(prefix=self._env_type)
        all_keys = self._job_manager.redis.keys('*')

    # Test creating a job actually gets back a job object
    def test_create_job_1_a(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self.assertTrue(isinstance(created_job, Job))

    # Test creating a job actually gets back the expected job object
    def test_create_job_1_b(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self.assertEqual(expected_job, created_job)

    # Test creating two job actually gets back two different job objects
    def test_create_job_1_c(self):
        example_index_1 = 0
        example_index_2 = 1
        expected_job_1, created_job_1 = self._exec_job_manager_create_from_expected(example_index_1)
        expected_job_2, created_job_2 = self._exec_job_manager_create_from_expected(example_index_2)
        self.assertNotEqual(expected_job_1, expected_job_2)
        self.assertNotEqual(created_job_1, created_job_2)

    # Test creating a job actually gets back a job object
    def test_create_job_2_a(self):
        example_index = 1
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self.assertTrue(isinstance(created_job, Job))

    # Test creating a job actually gets back the expected job object
    def test_create_job_2_b(self):
        example_index = 1
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self.assertEqual(expected_job, created_job)

    # Test deleting a job deletes a job that exists
    def test_delete_job_1_a(self):
        example_index = 0
        # Assume this works as expected ... which is verified in separate tests
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self._job_manager.delete_job(created_job.job_id)
        # Also assume does_job_exist works as expected ... which again is verified in separate tests
        self.assertFalse(self._job_manager.does_job_exist(created_job.job_id))

    # Test deleting a job deletes a job that exists, but does not delete a different job
    def test_delete_job_1_b(self):
        example_index_1 = 0
        example_index_2 = 1
        expected_job_1, created_job_1 = self._exec_job_manager_create_from_expected(example_index_1)
        expected_job_2, created_job_2 = self._exec_job_manager_create_from_expected(example_index_2)
        # Delete just the first job
        self._job_manager.delete_job(created_job_1.job_id)
        # Now make sure the second job is unaffected
        self.assertTrue(self._job_manager.does_job_exist(created_job_2.job_id))

    # Test that an arbitrary job_id doesn't exist for a new manager with no jobs added to it yet
    def test_does_job_exist_1_a(self):
        job_id = 1
        does_exist = self._job_manager.does_job_exist(job_id=job_id)
        self.assertFalse(does_exist)

    # Test that an added job_id does exist
    def test_does_job_exist_2_a(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        does_exist = self._job_manager.does_job_exist(job_id=expected_job.job_id)
        self.assertTrue(does_exist)

    # Test that an added job_id does not exist before being added/created/saved
    def test_does_job_exist_2_b(self):
        example_index = 0
        uuid_str = self._uuid_str_vals[example_index]
        self.assertFalse(self._job_manager.does_job_exist(uuid_str))
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # Also ensure the id is equal
        self.assertEqual(uuid_str, created_job.job_id)
        # Finally ...
        does_exist = self._job_manager.does_job_exist(job_id=expected_job.job_id)
        self.assertTrue(does_exist)

    # Test that an added job_id does exist
    def test_does_job_exist_3_a(self):
        example_index = 1
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        does_exist = self._job_manager.does_job_exist(job_id=expected_job.job_id)
        self.assertTrue(does_exist)

    # Test getting all active jobs before there are any saved active jobs to get
    def test_get_all_active_jobs_1_a(self):
        active_jobs = self._job_manager.get_all_active_jobs()
        self.assertEqual(len(active_jobs), 0)

    # Test getting all active jobs after some have been saved
    def test_get_all_active_jobs_2_a(self):
        #all_keys = self._job_manager.redis.keys('*')
        jobs = []
        job_ids = []
        for i in range(2):
            jobs.append(self._create_example_job_for_index(i))
            job_ids.append(jobs[i].job_id)
            self._job_manager.save_job(jobs[i])
        job_ids.sort()

        active_jobs = self._job_manager.get_all_active_jobs()
        active_job_ids = []
        for aj in active_jobs:
            aj_id = aj.job_id
            active_job_ids.append(aj_id)
        active_job_ids.sort()

        self.assertEqual(job_ids, active_job_ids)

    # Test save_job saves a record (i.e., it later exists)
    def test_save_job_1_a(self):
        example_index = 0
        job = self._create_example_job_for_index(example_index)
        self.assertFalse(self._job_manager.does_job_exist(job.job_id))
        self._job_manager.save_job(job)
        self.assertTrue(self._job_manager.does_job_exist(job.job_id))

    # Test save_job saves a record and saves the property values correctly
    def test_save_job_1_b(self):
        example_index = 0
        job = self._create_example_job_for_index(example_index)
        self._job_manager.save_job(job)
        saved_job = self._job_manager.retrieve_job(job.job_id)
        # Should be able to rely on dictionary equality test for this
        self.assertEqual(job.to_dict(), saved_job.to_dict())

    # Test save_job saves changes to a record
    def test_save_job_1_c(self):
        example_index = 0
        # Build and then save a job
        job = self._create_example_job_for_index(example_index)
        self._job_manager.save_job(job)
        original_cpu_count = job.cpu_count
        # Then update the record
        job.cpu_count += 100
        self._job_manager.save_job(job)
        updated_cpu_count = job.cpu_count
        # Get the updated record
        updated_job = self._job_manager.retrieve_job(job.job_id)
        # Confirm the updated record has the updated value
        self.assertNotEqual(original_cpu_count, updated_cpu_count)
        self.assertEqual(updated_cpu_count, updated_job.cpu_count)

    # Test save_job saves a record (i.e., it later exists) that has an RsaKeyPair
    def test_save_job_2_a(self):
        example_index = 1
        job = self._create_example_job_for_index(example_index)

        self.assertFalse(self._job_manager.does_job_exist(job.job_id))
        self._job_manager.save_job(job)
        self.assertTrue(self._job_manager.does_job_exist(job.job_id))

    # Test save_job saves a record that has an RsaKeyPair, and saves the key pair object correctly
    def test_save_job_2_b(self):
        example_index = 1
        job = self._create_example_job_for_index(example_index)
        self._job_manager.save_job(job)
        saved_job = self._job_manager.retrieve_job(job.job_id)
        self.assertEqual(job.rsa_key_pair, saved_job.rsa_key_pair)

    # Test retrieve_job retrieves the expected Job object
    def test_retrieve_job_1_a(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        retrieved_job = self._job_manager.retrieve_job(expected_job.job_id)
        self.assertEqual(expected_job, retrieved_job)

    # Test retrieve_job retrieves the expected Job object
    def test_retrieve_job_2_a(self):
        example_index = 1
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        retrieved_job = self._job_manager.retrieve_job(expected_job.job_id)
        self.assertEqual(expected_job, retrieved_job)

    # Note that retrieve_job_by_redis_key() function is always exercised by retrieve_job(), and thus implicitly tested

    # TODO: tests for request_allocations
    # Test request_allocations for a job with a single-node allocation paradigm fails with default status after creation
    def test_request_allocations_1_a(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        self.assertNotEqual(created_job.status, JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self.assertFalse(self._job_manager.request_allocations(created_job))

    # Test request_allocations for a job with a single-node allocation paradigm succeeds
    def test_request_allocations_1_b(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self.assertTrue(self._job_manager.request_allocations(created_job))

    # Test request_allocations for a job with a single-node allocation paradigm gets back a tuple
    def test_request_allocations_1_c(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        # Should be one allocation for single-node
        self.assertTrue(isinstance(created_job.allocations, tuple))

    def test_request_allocations_1_d(self):
        """ Test request_allocations for job w/ single-node paradigm gets back tuple with only one allocation host. """
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        # Should be only one unique host value among all allocation for single-node
        self.assertEqual(1, len(set(alloc.hostname for alloc in allocations)))

    # Test request_allocations for a job with a single-node allocation paradigm gets back a proper allocation of cpus
    def test_request_allocations_1_e(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(created_job.cpu_count, sum(alloc.cpu_count for alloc in allocations))

    # Test request_allocations for a job with a single-node allocation paradigm gets back a proper allocation of memory
    def test_request_allocations_1_f(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(created_job.memory_size, sum(alloc.memory for alloc in allocations))

    # Test request_allocations for a job with a fill-nodes allocation paradigm succeeds
    def test_request_allocations_2_a(self):
        example_index = 2
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self.assertTrue(self._job_manager.request_allocations(created_job))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a tuple
    def test_request_allocations_2_b(self):
        example_index = 2
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        # Should be one allocation for fill-nodes
        self.assertTrue(isinstance(allocations, tuple))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a tuple with one node
    def test_request_allocations_2_c(self):
        """ Test request_allocations for job w/ fill-nodes gets back allocations on same host when they all fit. """
        example_index = 2
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        # Should be only one unique host value among all allocation for fill-nodes in this example (they should all fit)
        self.assertEqual(1, len(set(alloc.hostname for alloc in allocations)))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a proper allocation of cpus
    def test_request_allocations_2_d(self):
        example_index = 2
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(created_job.cpu_count, sum(alloc.cpu_count for alloc in allocations))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a proper allocation of memory
    def test_request_allocations_2_e(self):
        example_index = 2
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(created_job.memory_size, sum(alloc.memory for alloc in allocations))

    # Test request_allocations for a job with a round-robin allocation paradigm succeeds
    def test_request_allocations_3_a(self):
        example_index = 3
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self.assertTrue(self._job_manager.request_allocations(created_job))

    # Test request_allocations for a job with a round-robin allocation paradigm gets back a tuple
    def test_request_allocations_3_b(self):
        example_index = 3
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertTrue(isinstance(allocations, tuple))

    # Test request_allocations for a job with a round-robin allocation paradigm gets back a tuple with multiple nodes
    def test_request_allocations_3_c(self):
        example_index = 3
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(3, len(set(alloc.hostname for alloc in allocations)))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a proper allocation of cpus
    def test_request_allocations_3_d(self):
        example_index = 3
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        self.assertEqual(created_job.cpu_count, sum(alloc.cpu_count for alloc in allocations))

    # Test request_allocations for a job with a fill-nodes allocation paradigm gets back a proper allocation of memory
    def test_request_allocations_3_e(self):
        example_index = 3
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        allocations = created_job.allocations
        # FIXME: for now, resource allocation does not properly handle memory across multiple nodes, instead getting the
        #  required amount from every node that provides an allocation ... so for now, just check the first one
        #mem_total = 0
        #for a in allocations:
        #    mem_total += a.memory
        mem_total = allocations[0].memory
        self.assertEqual(created_job.memory_size, sum(alloc.memory for alloc in allocations))

    def test_release_allocations_1_a(self):
        """ Test that release fails if the job has the wrong status. """
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        self._job_manager.save_job(created_job)
        retrieved_job_1 = self._job_manager.retrieve_job(created_job.job_id)
        self.assertEqual(retrieved_job_1.allocations, created_job.allocations)
        result = self._job_manager.release_allocations(retrieved_job_1)
        self.assertFalse(result.success)

    def test_release_allocations_1_b(self):
        """ Test that resources are not released if the job has the wrong status. """
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        self._job_manager.save_job(created_job)
        retrieved_job_1 = self._job_manager.retrieve_job(created_job.job_id)
        self.assertEqual(retrieved_job_1.allocations, created_job.allocations)
        result = self._job_manager.release_allocations(retrieved_job_1)
        self.assertEqual(retrieved_job_1.allocations, created_job.allocations)

    def test_release_allocations_1_c(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        self._job_manager.save_job(created_job)
        retrieved_job_1 = self._job_manager.retrieve_job(created_job.job_id)
        # Now adjust the status again
        retrieved_job_1.set_status_step(JobExecStep.COMPLETED)
        self._job_manager.save_job(retrieved_job_1)
        retrieved_job_2 = self._job_manager.retrieve_job(created_job.job_id)
        self.assertEqual(retrieved_job_2.allocations, created_job.allocations)
        result = self._job_manager.release_allocations(retrieved_job_2)
        self.assertTrue(result.success)
        #self.assertIsNone(retrieved_job_2.allocations)

    def test_release_allocations_1_d(self):
        example_index = 0
        expected_job, created_job = self._exec_job_manager_create_from_expected(example_index)
        # We will need to adjust the status
        created_job.set_status(JobStatus(JobExecPhase.MODEL_EXEC, JobExecStep.AWAITING_ALLOCATION))
        self._job_manager.request_allocations(created_job)
        self._job_manager.save_job(created_job)
        retrieved_job_1 = self._job_manager.retrieve_job(created_job.job_id)
        # Now adjust the status again
        retrieved_job_1.set_status_step(JobExecStep.COMPLETED)
        self._job_manager.save_job(retrieved_job_1)
        retrieved_job_2 = self._job_manager.retrieve_job(created_job.job_id)
        self.assertEqual(retrieved_job_2.allocations, created_job.allocations)
        result = self._job_manager.release_allocations(retrieved_job_2)
        self.assertIsNone(retrieved_job_2.allocations)

    # TODO: tests for manage_job_processing (maybe ... async so this might be too difficult)
