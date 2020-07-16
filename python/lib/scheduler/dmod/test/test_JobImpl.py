import unittest
from ..scheduler.job.job import JobImpl
from uuid import UUID


class TestJobImpl(unittest.TestCase):

    def setUp(self) -> None:
        self._example_jobs = []
        self._example_jobs.append(JobImpl(4, 1000, parameters={}, allocation_paradigm_str='single-node'))
        self._uuid_str_vals = []
        self._uuid_str_vals.append('12345678-1234-5678-1234-567812345678')

    def tearDown(self) -> None:
        pass

    # Test that the job id property can be set appropriately when a UUID is passed
    def test_job_id_1_a(self):
        example_index = 0

        uuid_as_str = self._uuid_str_vals[example_index]
        uuid_val = UUID('{' + uuid_as_str + '}')
        job = self._example_jobs[example_index]

        self.assertNotEqual(job.job_id, uuid_as_str)

        job.job_id = uuid_val

        self.assertEqual(job.job_id, uuid_as_str)

    # Test that updating the job id property using a UUID object properly adjusts the last_updated property
    def test_job_id_1_b(self):
        example_index = 0

        uuid_as_str = self._uuid_str_vals[example_index]
        uuid_val = UUID('{' + uuid_as_str + '}')
        job = self._example_jobs[example_index]
        initial_last_updated = job.last_updated

        job.job_id = uuid_val

        self.assertLess(initial_last_updated, job.last_updated)

    # Test that the job id property can be set appropriately when a UUID is passed
    def test_job_id_1_c(self):
        example_index = 0

        uuid_as_str = self._uuid_str_vals[example_index]
        job = self._example_jobs[example_index]

        self.assertNotEqual(job.job_id, uuid_as_str)

        job.job_id = uuid_as_str

        self.assertEqual(job.job_id, uuid_as_str)

    # Test that updating the job id property using a UUID object properly adjusts the last_updated property
    def test_job_id_1_d(self):
        example_index = 0

        uuid_as_str = self._uuid_str_vals[example_index]
        job = self._example_jobs[example_index]
        initial_last_updated = job.last_updated

        job.job_id = uuid_as_str

        self.assertLess(initial_last_updated, job.last_updated)
