import unittest
from ..scheduler.scheduler import Scheduler
from . import EmptyResourceManager, MockResourceManager

class TestScheduler(unittest.TestCase):

    def setUp(self) -> None:
        yaml_file = "image_and_domain.yaml"
        self.user_name = 'test'
        self.requested_cpus = 10
        self.requested_memory = 1000000
        #Various resource manager states
        self.empty_resources = EmptyResourceManager()
        self.mock_resources = MockResourceManager()
        #Create a scheduler with no resources
        self.scheduler = Scheduler(images_and_domains_yaml=yaml_file, resource_manager=self.empty_resources)

    def tearDown(self) -> None:
        self.scheduler.docker_client.close()

    def test_return42(self):
        """

        """
        ret = self.scheduler.return42()
        self.assertEqual(ret, 42)

    def test_single_node_1(self):
        """
            Test single node scheduling when no resources are available
        """
        test = self.scheduler.single_node(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_single_node_2(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        test = self.scheduler.single_node(self.user_name, 0, self.requested_memory)
        self.assertIsNone(test)

    def test_single_node_2_a(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        test = self.scheduler.single_node(self.user_name, -1, self.requested_memory)
        self.assertIsNone(test)

    def test_single_node_2_b(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        test = self.scheduler.single_node(self.user_name, 2.5, self.requested_memory)
        self.assertIsNone(test)

    def test_single_node_3(self):
        """
            Test single node scheduling with valid resources for first node
        """
        request_cpus = 5
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.single_node(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation[0]['cpus_allocated'], request_cpus)
        self.assertEqual(allocation[0]['Hostname'], 'hostname1')
        self.assertEqual(allocation[0]['node_id'], 'Node-0001')

    def test_single_node3_a(self):
        """
            Test single node scheduling with valid resources which won't fit on first node
        """
        request_cpus=10
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.single_node(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation[0]['cpus_allocated'], request_cpus)
        self.assertEqual(allocation[0]['Hostname'], 'hostname2')
        self.assertEqual(allocation[0]['node_id'], 'Node-0002')

    def test_single_node_4(self):
        """
            Test single node scheduling with valid resources which cannot satisfy request
        """
        request_cpus=100
        self.scheduler.resource_manager = self.mock_resources
        test = self.scheduler.single_node(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_nodes_1(self):
        """
            Test fill node scheduling when no resources are available
        """
        test = self.scheduler.fill_nodes(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_nodes_2(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        test = self.scheduler.fill_nodes(self.user_name, 0, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_nodes_2_a(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        test = self.scheduler.fill_nodes(self.user_name, -1, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_nodes_2_b(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        test = self.scheduler.fill_nodes(self.user_name, 2.5, self.requested_memory)
        self.assertIsNone(test)

    def test_fill_nodes_3(self):
        """
            Test fill nodes scheduling with valid resources for first node
        """
        request_cpus = 5
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.fill_nodes(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation[0]['cpus_allocated'], request_cpus)
        self.assertEqual(allocation[0]['Hostname'], 'hostname1')
        self.assertEqual(allocation[0]['node_id'], 'Node-0001')

    def test_fill_nodes_3_a(self):
        """
            Test fill nodes scheduling with valid resources for two nodes
        """
        request_cpus = 10
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.fill_nodes(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 2)
        #Validate resources on first node
        self.assertEqual(allocation[0]['cpus_allocated'], 5)
        self.assertEqual(allocation[0]['Hostname'], 'hostname1')
        self.assertEqual(allocation[0]['node_id'], 'Node-0001')
        #Validate resources on second node
        self.assertEqual(allocation[1]['cpus_allocated'], 5)
        self.assertEqual(allocation[1]['Hostname'], 'hostname2')
        self.assertEqual(allocation[1]['node_id'], 'Node-0002')

    def test_fill_nodes_4(self):
        """
            Test fill nodes scheduling with valid resources which cannot satisfy request
        """
        request_cpus=500
        self.scheduler.resource_manager = self.mock_resources
        test = self.scheduler.fill_nodes(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_1(self):
        """
            Test round_robin scheduling when no resources are available
        """
        test = self.scheduler.round_robin(self.user_name, self.requested_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_2(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        test = self.scheduler.round_robin(self.user_name, 0, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_2_a(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        test = self.scheduler.round_robin(self.user_name, -1, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_2_b(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        test = self.scheduler.round_robin(self.user_name, 2.5, self.requested_memory)
        self.assertIsNone(test)

    def test_round_robin_3(self):
        """
            Test round_robin scheduling with valid resources for first node
        """
        request_cpus = 5
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.round_robin(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 3)
        #Validate resources on first node
        self.assertEqual(allocation[0]['cpus_allocated'], 2)
        self.assertEqual(allocation[0]['Hostname'], 'hostname1')
        self.assertEqual(allocation[0]['node_id'], 'Node-0001')
        #Validate resources on second node
        self.assertEqual(allocation[1]['cpus_allocated'], 2)
        self.assertEqual(allocation[1]['Hostname'], 'hostname2')
        self.assertEqual(allocation[1]['node_id'], 'Node-0002')
        #Validate resources on third node
        self.assertEqual(allocation[2]['cpus_allocated'], 1)
        self.assertEqual(allocation[2]['Hostname'], 'hostname3')
        self.assertEqual(allocation[2]['node_id'], 'Node-0003')

    def test_fill_nodes_3_a(self):
        """
            Test round_robin scheduling with valid resources for two nodes
        """
        request_cpus = 10
        self.scheduler.resource_manager = self.mock_resources
        id, allocation = self.scheduler.fill_nodes(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNotNone(id)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 2)
        #Validate resources on first node
        self.assertEqual(allocation[0]['cpus_allocated'], 5)
        self.assertEqual(allocation[0]['Hostname'], 'hostname1')
        self.assertEqual(allocation[0]['node_id'], 'Node-0001')
        #Validate resources on second node
        self.assertEqual(allocation[1]['cpus_allocated'], 5)
        self.assertEqual(allocation[1]['Hostname'], 'hostname2')
        self.assertEqual(allocation[1]['node_id'], 'Node-0002')

    def test_fill_nodes_4(self):
        """
            Test round_robin scheduling with valid resources which cannot satisfy request
        """
        request_cpus=500
        self.scheduler.resource_manager = self.mock_resources
        test = self.scheduler.fill_nodes(self.user_name, request_cpus, self.requested_memory)
        self.assertIsNone(test)

    def test_print_resource_details(self):
        """
            Test print_resource_details when no resources are available
        """
        self.scheduler.print_resource_details()

    #TODO test
    @unittest.skip("Not implemented")
    def test_create_service(self):
        pass
    @unittest.skip("Not implemented")
    def test_from_request(self):
        pass
    @unittest.skip("Not implemented")
    def test_run_job(self):
        pass
    @unittest.skip("Not implemented")
    def test_enqueue(self):
        pass
    @unittest.skip("Not implemented")
    def test_build_host_list(self):
        pass
    @unittest.skip("Not implemented")
    def test_start_jobs(self):
        pass
    @unittest.skip("Not implemented")
    def test_check_jobQ(self):
        pass
    @unittest.skip("Not implemented")
    def test_job_allocation_and_setup(self):
        pass
