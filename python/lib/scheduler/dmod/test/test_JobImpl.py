import unittest
from ..scheduler.job.job import JobImpl, JobStatus, JobExecPhase, JobExecStep
from ..scheduler.resources.resource_allocation import ResourceAllocation
from dmod.communication import NWMRequest
from uuid import UUID

from typing import List


class TestJobImpl(unittest.TestCase):

    def setUp(self) -> None:
        self._nwm_model_request = NWMRequest.factory_init_from_deserialized_json(
            {
                "allocation_paradigm": "SINGLE_NODE",
                "cpu_count": 4,
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
    def test_set_allocation_priority(self):
        """
        Update allocation priority.
        This should implicitly change the instance's `last_updated` field to the current time.
        """
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        outdated_last_updated = job.last_updated
        prior_allocation_priority = job.allocation_priority

        job.set_allocation_priority(prior_allocation_priority + 1)
        self.assertEqual(job.allocation_priority, prior_allocation_priority + 1)
        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_add_allocation(self):
        """
        Test that a resource allocation is added and that the instance's `last_updated` field is implicitly updated.
        """
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        resource_allocation = self._resource_allocations[example_index_job]

        # we should not have any allocations up to this point
        self.assertIsNone(job.allocations)
        outdated_last_updated = job.last_updated

        job.add_allocation(resource_allocation)

        self.assertIsNotNone(job.allocations)
        self.assertIsInstance(job.allocations, tuple)
        self.assertEqual(len(job.allocations), 1) # type: ignore

        self.assertEqual(job.allocations[0], resource_allocation) # type: ignore

        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_allocations(self):
        """
        Test setting resource allocations and that the instance's `last_updated` field is implicitly updated.
        """
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        resource_allocation = self._resource_allocations[example_index_job]

        # we should not have any allocations up to this point
        self.assertIsNone(job.allocations)
        outdated_last_updated = job.last_updated

        job.set_allocations((resource_allocation, ))

        self.assertIsNotNone(job.allocations)
        self.assertIsInstance(job.allocations, tuple)
        self.assertEqual(len(job.allocations), 1) # type: ignore

        self.assertEqual(job.allocations[0], resource_allocation) # type: ignore

        # assert `last_updated` was updated and is greater than previous value
        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_data_requirements(self):
        # importing here, not needed elsewhere
        from dmod.core.meta_data import DataRequirement, DataCategory, DataDomain, DataFormat, DiscreteRestriction, StandardDatasetIndex
        example_index_job = 0
        job = self._example_jobs[example_index_job]

        outdated_last_updated = job.last_updated

        domain = DataDomain(
            data_format=DataFormat.NWM_CONFIG,
            discrete=[DiscreteRestriction(variable=StandardDatasetIndex.DATA_ID, values=["42"])]
            )
        data_reqs = [DataRequirement(category=DataCategory.CONFIG, domain=domain, is_input=True)]

        # data requirements should be an empty list at this point
        self.assertFalse(job.data_requirements)
        job.set_data_requirements(data_reqs)

        self.assertTrue(job.data_requirements)
        self.assertIsInstance(job.data_requirements, list)
        self.assertEqual(len(job.data_requirements), 1) # type: ignore

        # assert `last_updated` was updated and is greater than previous value
        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_job_id(self):
        from uuid import UUID
        example_index_job = 0
        job = self._example_jobs[example_index_job]

        fake_job_ids = ["00000000-0000-0000-0000-000000000000", UUID("11111111-1111-1111-1111-111111111111")]

        # test setting with `str` and `UUID`
        for i, job_id in enumerate(fake_job_ids):
            with self.subTest(i=i):
                old_last_updated = job.last_updated
                old_job_id = job.job_id

                self.assertIsInstance(old_job_id, str)

                job.set_job_id(job_id)
                self.assertEqual(str(job_id), job.job_id)

                # assert `last_updated` was updated and is greater than previous value
                self.assertGreater(job.last_updated, old_last_updated)

    def test_set_partition_config(self):
        from dmod.modeldata.hydrofabric import Partition, PartitionConfig

        example_index_job = 0
        job = self._example_jobs[example_index_job]

        partition_config = PartitionConfig(partitions=[Partition(partition_id=42, catchment_ids=["42"], nexus_ids=["42"])])

        # we should not have any partition configs up to this point
        self.assertIsNone(job.partition_config)
        job.set_partition_config(partition_config)
        self.assertEqual(job.partition_config, partition_config)

    def test_set_rsa_key_pair(self):
        from ..scheduler.rsa_key_pair import RsaKeyPair
        from tempfile import TemporaryDirectory
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        outdated_last_updated = job.last_updated

        self.assertIsNone(job.rsa_key_pair)

        with TemporaryDirectory() as dir:
            key_pair = RsaKeyPair(directory=dir)
            job.set_rsa_key_pair(key_pair)
            self.assertEqual(job.rsa_key_pair, key_pair)

            # assert `last_updated` was updated and is greater than previous value
            self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_status(self):
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        outdated_last_updated = job.last_updated

        status = JobStatus(phase=None)
        self.assertNotEqual(status, job.status)
        job.set_status(status)

        self.assertEqual(status, job.status)
        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_status_phase(self):
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        outdated_last_updated = job.last_updated

        new_status_phase = JobExecPhase.MODEL_EXEC
        self.assertNotEqual(job.status_phase, new_status_phase)

        job.set_status_phase(new_status_phase)
        self.assertEqual(job.status_phase, new_status_phase)

        # assert `last_updated` was implicitly updated and is greater than previous value
        self.assertGreater(job.last_updated, outdated_last_updated)

    def test_set_status_step(self):
        example_index_job = 0
        job = self._example_jobs[example_index_job]
        outdated_last_updated = job.last_updated

        new_status_step = JobExecStep.AWAITING_ALLOCATION
        self.assertNotEqual(job.status_phase, new_status_step)

        job.set_status_step(new_status_step)
        self.assertEqual(job.status_step, new_status_step)

        # assert `last_updated` was implicitly updated and is greater than previous value
        self.assertGreater(job.last_updated, outdated_last_updated)
