import unittest
import os
from ..scheduler.resources.redis_manager import RedisManager
from . import mock_resources

class IntegrationTestRedisManager(unittest.TestCase):
    """
        Tests of the redis implementation of the abstract ResourceManager Interface
        Tests some additional functions not in the interface but found in the RedisManager
    """
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
        test_pass = os.environ.get('IT_REDIS_CONTAINER_PASS')
        test_port = os.environ.get('IT_REDIS_CONTAINER_HOST_PORT')

        self.resource_manager = RedisManager(resource_pool = 'test_pool',
                                             redis_host='127.0.0.1',
                                             redis_port=test_port,
                                             redis_pass=test_pass)
        #Set up some intial redis state
        self.redis = self.resource_manager.redis
        self.pool_key = self.resource_manager.resource_pool_key
        self.mock_resources = mock_resources()
        self.clear_redis()

    def tearDown(self) -> None:
        pass

    def test_add_resource_1(self):
        """
            Test that a single well formed resource is correctly added to the redis store
        """
        key = '{}:meta:{}'.format( self.pool_key, self.mock_resources[0]['node_id'] )
        #print("TESTING -- KEY: {}".format(key))
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        validate = self.redis.hgetall(key)

        self.assertDictEqual(self.dict_values_to_string( self.mock_resources[0] ), validate)
        self.assertTrue( self.redis.sismember(self.pool_key, self.mock_resources[0]['node_id']))

    def test_add_resource_1_a(self):
        """
            Test adding an empty resource
        """
        self.assertRaises(KeyError, self.resource_manager.add_resource, {}, self.pool_key)

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
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = self.mock_resources[0]['CPUs']
        allocation = self.resource_manager.allocate_resource(resource_id, cpus)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty
        self.assertEqual(cpus, allocation['cpus_allocated'])
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

    def test_allocate_resource_1_a(self):
        """
            Test partial allocation of single resource
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = self.mock_resources[0]['CPUs'] - 2
        allocation = self.resource_manager.allocate_resource(resource_id, cpus)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty
        self.assertEqual(cpus, allocation['cpus_allocated'])
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs'] - cpus, int(validate))

    def test_allocate_resource_1_b(self):
        """
            Test over allocation of single resource when partial = False
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = self.mock_resources[0]['CPUs'] + 1
        allocation = self.resource_manager.allocate_resource(resource_id, cpus)

        #Verify the allocation
        self.assertFalse(allocation) #Test for empty allocation
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs'], int(validate))

    def test_allocate_resource_1_c(self):
        """
            Test invalid allocation of single resource
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = 0
        allocation = self.resource_manager.allocate_resource(resource_id, cpus)

        #Verify the allocation
        self.assertFalse(allocation) #Test for empty allocation
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs'], int(validate))

    def test_allocate_resource_1_d(self):
        """
            Test over allocation of exhausted resource
        """
        self.mock_resources[0]['CPUs'] = 0

        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = 5
        allocation = self.resource_manager.allocate_resource(resource_id, cpus)

        #Verify the allocation
        self.assertFalse(allocation) #Test forempty allocation

        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

    def test_allocate_resource_2(self):
        """
            Test full allocation of multiple resource using partial = True
        """
        self.resource_manager.set_resources(self.mock_resources[0:2])

        resource_id_1 = self.mock_resources[0]['node_id']
        resource_id_2 = self.mock_resources[1]['node_id']
        cpus = self.mock_resources[0]['CPUs'] + self.mock_resources[1]['CPUs']
        allocation1 = self.resource_manager.allocate_resource(resource_id_1, cpus, partial=True)
        remainin_cpus = cpus - allocation1['cpus_allocated']
        #Verify the allocation for first resource
        self.assertTrue(allocation1) #Test for non-empty
        self.assertEqual(5, allocation1['cpus_allocated'])

        allocation2 = self.resource_manager.allocate_resource(resource_id_2, cpus, partial=True)
        #Verify the allocation for second resource
        self.assertTrue(allocation2) #Test for non-empty
        self.assertEqual(self.mock_resources[1]['CPUs'], allocation2['cpus_allocated'])

        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id_1)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

        key = '{}:meta:{}'.format( self.pool_key, resource_id_2)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

    def test_allocate_resource_2_a(self):
        """
            Test partial allocation of single resource using partial = True
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = self.mock_resources[0]['CPUs'] - 2
        allocation = self.resource_manager.allocate_resource(resource_id, cpus, partial=True)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty
        self.assertEqual(cpus, allocation['cpus_allocated'])
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs'] - cpus, int(validate))

    def test_allocate_resource_2_b(self):
        """
            Test over allocation of single resource when partial = True
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = self.mock_resources[0]['CPUs'] + 1
        allocation = self.resource_manager.allocate_resource(resource_id, cpus, partial=True)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty allocation
        self.assertEqual(self.mock_resources[0]['CPUs'], allocation['cpus_allocated'])

        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

    def test_allocate_resource_2_c(self):
        """
            Test invalid allocation of single resource when partial = True
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = 0
        allocation = self.resource_manager.allocate_resource(resource_id, cpus, partial=True)

        #Verify the allocation
        self.assertFalse(allocation) #Test for empty allocation
        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs'], int(validate))

    def test_allocate_resource_2_d(self):
        """
            Test over allocation of exhausted resource when partial = True
        """
        self.mock_resources[0]['CPUs'] = 0

        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)

        resource_id = self.mock_resources[0]['node_id']
        cpus = 5
        allocation = self.resource_manager.allocate_resource(resource_id, cpus, partial=True)

        #Verify the allocation
        self.assertTrue(allocation) #Test for non-empty allocation
        self.assertEqual(0, allocation['cpus_allocated'])

        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(0, int(validate))

    def test_release_resources_1(self):
        """
            Test releasing "allocated" resource
        """
        resource_id = self.mock_resources[0]['node_id']
        allocated_cpus = 5
        allocated_memory = 100
        allocation = {'node_id': resource_id,
                      'Hostname': self.mock_resources[0]['Hostname'],
                      'cpus_allocated': allocated_cpus,
                      'mem': allocated_memory}
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        self.resource_manager.release_resources([allocation])

        #Verify the redis state for the resource
        key = '{}:meta:{}'.format( self.pool_key, resource_id)
        #print("TEST ALLOCATE RESOURCE -- KEY {}".format(key))
        validate = self.redis.hget(key, 'CPUs')
        self.assertEqual(self.mock_resources[0]['CPUs']+allocated_cpus, int(validate))
        validate = self.redis.hget(key, 'MemoryBytes')
        self.assertEqual(self.mock_resources[0]['MemoryBytes']+allocated_memory, int(validate))

    def test_get_available_cpu_count_1(self):
        """
            Test that all available CPUS are reported with 1 resource
        """
        self.resource_manager.add_resource(self.mock_resources[0], self.pool_key)
        total_cpus = self.resource_manager.get_available_cpu_count()
        self.assertEqual(total_cpus, self.mock_resources[0]['CPUs'])

    def test_get_available_cpu_count_1_a(self):
        """
            Test that all available CPUS are reported with multiple resources
        """
        self.resource_manager.set_resources(self.mock_resources[0:2])
        total_cpus = self.resource_manager.get_available_cpu_count()
        self.assertEqual(total_cpus, self.mock_resources[0]['CPUs']+self.mock_resources[1]['CPUs'])

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
