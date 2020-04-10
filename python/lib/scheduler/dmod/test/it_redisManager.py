import unittest
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
from ..scheduler.resources.redis_manager import RedisManager
from ..scheduler.resources.resource import Resource
from ..scheduler.resources.resource_allocation import ResourceAllocation
from . import mock_resources


class IntegrationTestRedisManager(unittest.TestCase):
    """
        Tests of the redis implementation of the abstract ResourceManager Interface
        Tests some additional functions not in the interface but found in the RedisManager
    """

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

    def dict_values_to_string(self, dict):
        """
            Helper function that converts all dict values to string
            Useful when comparing to returns of raw redis queries, since
            everything in redis is a string
        """
        for k, v in dict.items(): #todo could be nice and recurse for nested dicts
            dict[k] = str(v)
        return dict

    def clear_redis(self):
        """
            Helper function to clear the redis instance of all keys
            Returns
            -------
            count The number of removed keys
        """
        count = 0
        for k in self.redis.scan_iter("*"):
          self.redis.delete(k)
          count += 1
        return count

    def setUp(self) -> None:
        self.resource_manager = RedisManager(resource_pool='test_pool',
                                             redis_host='127.0.0.1',
                                             redis_port=self.redis_test_port,
                                             redis_pass=self.redis_test_pass)
        #Set up some intial redis state
        self.redis = self.resource_manager.redis
        self.pool_key = self.resource_manager.resource_pool_key
        self.clear_redis()
        self.mock_resources = mock_resources()

    def tearDown(self) -> None:
        pass

    def _make_resource_allocation(self, mock_index: int, cpus_remaining: Optional[int], partial: bool = False,
                                  skip_add_resource: bool = False) -> tuple:
        """
        Add the mock resource from the ::attr:`mock_resources` list at the given index to ::attr:`resource_manager` and
        then create an allocation, requesting an amount of CPUs relative to the total such that the provided number of
        CPUs remain unused.

        The number of CPUs to request in the allocation is controlled by the ``cpus_remaining`` parameter.  The basic
        idea is that this is the number of CPUs that should remain available in the ::class:`Resource` after the
        allocation, assuming there were zero allocated to start with.  This is extended by the use of negative argument
        values to imply that the requested number of CPUs for the allocation is larger than total available, which
        may or may not be allowed.  Regardless, the number of requested CPUs for the allocation is determined by
        subtracting the argument from the total number of CPUs for the resource.

        Additionally, ``cpus_remaining`` can be set to ``None`` to indicate the CPU count for the allocation is ``0``.
        While not valid, this is useful for testing.

        Note that the returned ::class:`Resource` object is the mock object, not the deserialized object retrieved from
        the Redis instance, and thus reflecting the current state of the resource after allocation has been performed.

        Parameters
        ----------
        mock_index : int
            The index within ::attr:`mock_resources` of the mock resource to work with.

        cpus_remaining : Optional[int]
            A relative representation of the amount of CPUs to allocate, where the requested number is the total number
            of CPUs for the ::class:`Resource` minus this amount (yielding over-allocation for negative numbers), or
            ``0`` if the value is ``None``.

        partial : bool
            Whether during the allocation step a partial allocation should be allowed, which by default is ``False``.

        skip_add_resource : bool
            Whether to skip the step of adding the mock resource to the resource manager (i.e., because it has already
            been added), which by default is set to `False`.

        Returns
        -------
        tuple
            A tuple of size 3, containing the selected mock resource from ::attr:`mock_resources`, EITHER the
            ::class:`ResourceAllocation` object for the allocation OR the encountered exception during allocation
            failure, and the calculated number of requested CPUs for the allocation.

        """
        resource = self.mock_resources[mock_index]
        if not skip_add_resource:
            self.resource_manager.add_resource(resource, self.pool_key)
        requested_cpu_count = 0 if cpus_remaining is None else resource.total_cpu_count - cpus_remaining
        try:
            allocation = self.resource_manager.allocate_resource(resource.resource_id, requested_cpu_count,
                                                                 partial=partial)
        except Exception as e:
            allocation = e
        return resource, allocation, requested_cpu_count

    def test_add_resource_1(self):
        """
            Test that a single well formed resource is correctly added to the redis store
        """
        test_resource = self.mock_resources[0]
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        retrieved_hash = self.redis.hgetall(test_resource.unique_id)
        looked_up_resource = Resource.factory_init_from_dict(retrieved_hash)

        self.assertEqual(test_resource, looked_up_resource)
        self.assertTrue(self.redis.sismember(self.pool_key, self.mock_resources[0].unique_id))

    def test_add_resource_2(self):
        """
            Test adding a resource that already exists
        """
        pass #FIXME

    def test_set_resources(self):
        """
            This function is currently just an interator around add_resource.
            Simply test that it works without exception
        """
        self.resource_manager.set_resources(self.mock_resources)

    def test_get_resources(self):
        """
            Test the correct number of non-empty resources are returned

            TODO These would be a good place to test some of the partitioning, i.e.
            test that I cannot access a pool_key that I haven't been given
        """
        self.resource_manager.set_resources(self.mock_resources)
        resources = list( self.resource_manager.get_resources() )
        self.assertEqual(len(resources), len(self.mock_resources))
        for r in resources:
            #Testing metadata integrity isn't a bad idea, but redis doesn't give guarantee order
            #with the constructs we are using.  This could be manually done though for testing
            #self.assertDictEqual(self.dict_values_to_string(self.mock_resources[i]), r)
            #For now, just verify the dict isn't empty
            self.assertTrue(r) #Testing non-empty resource

    def test_get_resource_ids(self):
        """
            Simple interface to redis, test that it gives back the number of ids we expect
        """
        self.resource_manager.set_resources(self.mock_resources)
        ids = self.resource_manager.get_resource_ids()
        self.assertEqual(len(ids), len(self.mock_resources))

    def test_allocate_resource_1(self):
        """
            Test full allocation of single resource
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated
        cpus_left_free = 0
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free)

        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty
        self.assertEqual(requested_cpu_count, allocation.cpu_count)

        #Verify the redis state for the resource
        self.assertEqual(cpus_left_free, looked_up_resource.cpu_count)

    def test_allocate_resource_1_a(self):
        """
            Test partial allocation of single resource
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated
        cpus_left_free = 2
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty
        self.assertEqual(requested_cpu_count, allocation.cpu_count)

        #Verify the redis state for the resource
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(cpus_left_free, looked_up_resource.cpu_count)

    def test_allocate_resource_1_b(self):
        """
            Test over allocation of single resource when partial = False
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated (here, allocating one more than supported)
        cpus_left_free = -1
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free)

        #V erify the resource still has the total number of CPUs
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.cpu_count, looked_up_resource.total_cpu_count)

    def test_allocate_resource_1_c(self):
        """
            Test invalid allocation of single resource
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated (here, None means don't allocate any)
        cpus_left_free = None
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free)

        # This should fail, so the returned 'allocation' should be an exception object (specifically a ValueError)
        self.assertFalse(isinstance(allocation, ResourceAllocation))
        self.assertTrue(isinstance(allocation, ValueError))

        # Verify the resource still has the total number of CPUs
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.cpu_count, looked_up_resource.total_cpu_count)

    def test_allocate_resource_1_d(self):
        """
            Test over allocation of exhausted resource
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated (here, None means don't allocate any)
        cpus_left_free = 0
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free)

        # Verify the allocation
        self.assertTrue(isinstance(allocation, ResourceAllocation))

        # Verify the redis state for the resource
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.cpu_count, cpus_left_free)

    def test_allocate_resource_2(self):
        """
            Test full allocation of multiple resource using partial = True
        """

        mock_resource_index_1 = 0
        mock_resource_index_2 = 1
        self.resource_manager.set_resources(self.mock_resources[0:2])

        resource_1 = self.mock_resources[mock_resource_index_1]
        resource_2 = self.mock_resources[mock_resource_index_2]

        cpus = resource_1.cpu_count + resource_2.cpu_count

        allocation_1 = self.resource_manager.allocate_resource(resource_1.resource_id, cpus, partial=True)

        # Verify the allocation for first resource
        self.assertTrue(isinstance(allocation_1, ResourceAllocation))
        self.assertEqual(resource_1.total_cpu_count, allocation_1.cpu_count)

        remaining_cpus = cpus - allocation_1.cpu_count
        allocation_2 = self.resource_manager.allocate_resource(resource_2.resource_id, cpus, partial=True)

        # Verify the allocation for second resource
        self.assertTrue(isinstance(allocation_2, ResourceAllocation))
        self.assertEqual(remaining_cpus, allocation_2.cpu_count)

        # Verify the redis state for the resources
        looked_up_resource_1 = Resource.factory_init_from_dict(self.redis.hgetall(resource_1.unique_id))
        looked_up_resource_2 = Resource.factory_init_from_dict(self.redis.hgetall(resource_2.unique_id))
        # Should be 0 left in both if total needed was total between the two
        self.assertEqual(0, looked_up_resource_1.cpu_count)
        self.assertEqual(0, looked_up_resource_2.cpu_count)

    def test_allocate_resource_2_a(self):
        """
            Test partial allocation of single resource using partial = True
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated
        cpus_left_free = 2
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free,
                                                                                   partial=True)
        # Verify the allocation
        self.assertTrue(isinstance(allocation, ResourceAllocation))
        self.assertEqual(requested_cpu_count, allocation.cpu_count)

        # Verify the redis state for the resource
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.cpu_count, cpus_left_free)

    def test_allocate_resource_2_b(self):
        """
            Test over allocation of single resource when partial = True
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated
        cpus_left_free = -1
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free,
                                                                                   partial=True)
        # Verify the allocation
        self.assertTrue(isinstance(allocation, ResourceAllocation))
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.total_cpu_count, allocation.cpu_count)
        self.assertEqual(0, looked_up_resource.cpu_count)

    def test_allocate_resource_2_c(self):
        """
            Test invalid allocation of single resource when partial = True
        """
        mock_resource_index = 0
        # How many cpus to leave free, assuming none currently allocated
        cpus_left_free = None
        resource, allocation, requested_cpu_count = self._make_resource_allocation(mock_resource_index, cpus_left_free,
                                                                                   partial=True)
        # Verify the exception
        self.assertFalse(isinstance(allocation, ResourceAllocation))
        self.assertTrue(isinstance(allocation, ValueError))
        looked_up_resource = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource.cpu_count, looked_up_resource.total_cpu_count)

    def test_allocate_resource_2_d(self):
        """
            Test over allocation of exhausted resource when partial = True
        """
        mock_resource_index = 0
        cpus = 5
        resource = self.mock_resources[mock_resource_index]
        resource.cpu_count = 0
        self.resource_manager.add_resource(resource)
        allocation = self.resource_manager.allocate_resource(resource.resource_id, cpus, partial=True)

        # Verify there was no allocation
        self.assertIsNone(allocation)

    def test_release_resources_1(self):
        """
            Test releasing "allocated" resource
        """
        resource = self.mock_resources[0]
        self.resource_manager.add_resource(resource)
        requested_cpu_count = resource.total_cpu_count
        requested_mem = 100
        allocation = self.resource_manager.allocate_resource(resource.resource_id, requested_cpu_count, requested_mem)

        looked_up_resource_1st = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))

        self.assertTrue(isinstance(allocation, ResourceAllocation))
        self.assertEqual(looked_up_resource_1st.cpu_count, 0)
        self.assertEqual(looked_up_resource_1st.memory, resource.total_memory - requested_mem)

        self.resource_manager.release_resources([allocation])
        looked_up_resource_2nd = Resource.factory_init_from_dict(self.redis.hgetall(resource.unique_id))
        self.assertEqual(looked_up_resource_2nd.cpu_count, looked_up_resource_2nd.total_cpu_count)
        self.assertEqual(looked_up_resource_2nd.memory, looked_up_resource_2nd.total_memory)

    def test_get_available_cpu_count_1(self):
        """
            Test that all available CPUS are reported with 1 resource
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        total_cpus = self.resource_manager.get_available_cpu_count()
        self.assertEqual(total_cpus, self.mock_resources[0].cpu_count)

    def test_get_available_cpu_count_1_a(self):
        """
            Test that all available CPUS are reported with multiple resources
        """
        self.resource_manager.set_resources(self.mock_resources[0:2])
        total_cpus = self.resource_manager.get_available_cpu_count()
        self.assertEqual(total_cpus, self.mock_resources[0].cpu_count + self.mock_resources[1].cpu_count)

    @unittest.skip("Functionality moved to JobManager class")
    def test_create_job_entry_1(self):
        """
            Test job entry creation with single allocation
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        resource_id = self.mock_resources[0]['node_id']
        allocated_cpus = 5
        allocated_memory = 100
        allocation = {'node_id': resource_id,
                      'Hostname': self.mock_resources[0]['Hostname'],
                      'cpus_allocated': allocated_cpus,
                      'mem': allocated_memory}
        job_id = self.resource_manager.create_job_entry([allocation])

        #validate jobid
        self.assertNotEqual(job_id, '') #Test for non empty string ID
        #Validate redis state
        key = '{}:{}'.format(self.pool_key, 'running')
        self.assertTrue(self.redis.sismember(key, job_id))
        key = ':{}:{}:0'.format('job', job_id)
        validate = self.redis.hgetall(key)
        self.assertDictEqual( self.dict_values_to_string(allocation), validate )

    @unittest.skip("Functionality moved to JobManager class")
    def test_create_job_entry_2(self):
        """
            Test job entry creation with multiple allocations
        """
        self.resource_manager.set_resources(self.mock_resources[0:2])
        resource_id_1 = self.mock_resources[0]['node_id']
        resource_id_2 = self.mock_resources[1]['node_id']
        allocated_cpus = 5
        allocated_memory = 100
        allocation1 = {'node_id': resource_id_1,
                      'Hostname': self.mock_resources[0]['Hostname'],
                      'cpus_allocated': allocated_cpus,
                      'mem': allocated_memory}
        allocation2 = {'node_id': resource_id_2,
                      'Hostname': self.mock_resources[0]['Hostname'],
                      'cpus_allocated': allocated_cpus,
                      'mem': allocated_memory}

        job_id = self.resource_manager.create_job_entry([allocation1, allocation2])

        #validate jobid
        self.assertNotEqual(job_id, '') #Test for non empty string ID
        #Validate redis state
        key = '{}:{}'.format(self.pool_key, 'running')
        self.assertTrue(self.redis.sismember(key, job_id))
        key = ':{}:{}:0'.format('job', job_id)
        validate = self.redis.hgetall(key)
        self.assertDictEqual( self.dict_values_to_string(allocation1), validate )
        key = ':{}:{}:1'.format('job', job_id)
        validate = self.redis.hgetall(key)
        self.assertDictEqual( self.dict_values_to_string(allocation2), validate )

    @unittest.skip("Not functional, see comment in class")
    def test_retrieve_job_metadata(self):
        pass
