import unittest
from ..scheduler.job.job import JobImpl
from ..scheduler.resources.resource_allocation import ResourceAllocation
from dmod.communication import NWMRequest
from uuid import UUID

from typing import List


class TestJobImpl(unittest.TestCase):

    def setUp(self) -> None:
        self._nwm_model_request = NWMRequest.factory_init_from_deserialized_json(
            {"model": {"nwm": {"version": 2.0, "output": "streamflow", "domain": "blah", "parameters": {}}},
             "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"})
        self._example_jobs: List[JobImpl]= []
        self._example_jobs.append(JobImpl(4, 1000, model_request=self._nwm_model_request,
                                          allocation_paradigm='single-node'))

        self._uuid_str_vals: List[str] = []
        self._uuid_str_vals.append('12345678-1234-5678-1234-567812345678')

        self._resource_allocations: List[ResourceAllocation] = []
        self._resource_allocations.append(ResourceAllocation('node001', 'node001', 4, 1000))

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

    # Test that add_allocation works
    def test_add_allocation_1_a(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        job = self._example_jobs[example_index_job]
        self.assertIsNone(job.allocations)

        job.add_allocation(allocation)
        self.assertEqual(len(job.allocations), 1)

    # Test that add_allocation adds the expected allocation
    def test_add_allocation_1_b(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        job = self._example_jobs[example_index_job]

        job.add_allocation(allocation)
        self.assertEqual(allocation, job.allocations[0])

    # Test that add_allocation updates last_updated
    def test_add_allocation_1_c(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        job = self._example_jobs[example_index_job]
        initial_last_update = job.last_updated
        job.add_allocation(allocation)

        self.assertLess(initial_last_update, job.last_updated)

    # Test that allocation setter works with list
    def test_allocations_1_a(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = [allocation]
        job = self._example_jobs[example_index_job]

        self.assertIsNone(job.allocations)
        job.allocations = allocations
        self.assertIsNotNone(job.allocations)

    # Test that allocation setter works with tuple
    def test_allocations_1_b(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = (allocation,)
        job = self._example_jobs[example_index_job]

        self.assertIsNone(job.allocations)
        job.allocations = allocations
        self.assertIsNotNone(job.allocations)

    # Test that allocation setter works correctly with list
    def test_allocations_1_c(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = [allocation]
        job = self._example_jobs[example_index_job]
        job.allocations = allocations
        self.assertEqual(len(allocations), len(job.allocations))
        for i in range(len(allocations)):
            self.assertEqual(allocations[i], job.allocations[i])

    # Test that allocation setter works correctly with tuple
    def test_allocations_1_d(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = (allocation,)
        job = self._example_jobs[example_index_job]
        job.allocations = allocations
        self.assertEqual(len(allocations), len(job.allocations))
        for i in range(len(allocations)):
            self.assertEqual(allocations[i], job.allocations[i])

    # Test that allocation setter updates last_updated correctly with list
    def test_allocations_1_e(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = [allocation]
        job = self._example_jobs[example_index_job]
        initial_last_updated = job.last_updated
        job.allocations = allocations
        self.assertLess(initial_last_updated, job.last_updated)

    # Test that allocation setter updates last_updated correctly with tuple
    def test_allocations_1_f(self):
        example_index_job = 0
        example_index_allocation = 0

        allocation = self._resource_allocations[example_index_allocation]
        allocations = (allocation,)
        job = self._example_jobs[example_index_job]
        initial_last_updated = job.last_updated

        job.allocations = allocations
        self.assertLess(initial_last_updated, job.last_updated)

    # TODO: add tests for rest of setters that should update last_updated property

    # TODO: add tests for status_phase and status_step
