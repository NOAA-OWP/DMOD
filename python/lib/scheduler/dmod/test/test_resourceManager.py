import unittest

from . import EmptyResourceManager, MockResourceManager, mock_resources

class TestResourceManagerBase(unittest.TestCase):


    def setUp(self) -> None:
        #Test the base class under a MockResourceManager
        #All subclasses will set a new manager state
        #that these tests will run over
        self.resource_manager = MockResourceManager()

    def tearDown(self) -> None:
        pass

    def test_allocate_single_node_validation(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = 0
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)

    def test_allocate_single_node_validation_a(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = -1
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)

    def test_allocate_single_node_validation_b(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = 2.5
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)

    def test_allocate_fill_nodes_validation(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        cpus = 0
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_fill_nodes, cpus, mem)

    def test_allocate_fill_nodes_validation_a(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        cpus = -1
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_fill_nodes, cpus, mem)


    def test_allocate_fill_nodes_validation_b(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        cpus = 2.5
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_fill_nodes, cpus, mem)

    def test_allocate_round_robin_validation(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        cpus = 0
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_round_robin, cpus, mem)

    def test_allocate_round_robin_validation_a(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        cpus = -1
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_round_robin, cpus, mem)

    def test_allocate_round_robin_validation_b(self):
        """
            Test round_robin scheduling when invalid cpus are requested
        """
        cpus = 2.5
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_round_robin, cpus, mem)

class TestEmptyResources(TestResourceManagerBase):

    def setUp(self) -> None:
        self.resource_manager = EmptyResourceManager()

    def tearDown(self) -> None:
        pass

    def test_allocate_single_node_empty(self):
        """
            Test single node scheduling when no resources are available
        """
        cpus = 5
        mem = 1000000
        #job = self.mock_job(cpus=self.requested_cpus, mem=self.requested_memory, strategy='SINGLE_NODE')
        allocation = self.resource_manager.allocate_single_node(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNone(allocation[0])

    def test_allocate_fill_nodes_empty(self):
        """
            Test fill node scheduling when no resources are available
        """
        cpus = 5
        mem = 1000000
        allocation = self.resource_manager.allocate_fill_nodes(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNone(allocation[0])

    def test_allocate_round_robin_empty(self):
        """
            Test round_robin scheduling when no resources are available
        """
        cpus = 5
        mem = 1000000
        allocation = self.resource_manager.allocate_round_robin(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNone(allocation[0])


class TestValidResources(TestResourceManagerBase):

    def setUp(self) -> None:

        self.requested_cpus = 10
        self.requested_memory = 1000000

        self.resource_manager = MockResourceManager()
        self.mock_resources = mock_resources()

    def tearDown(self) -> None:
        pass

    @unittest.skip("Test no longer reflects design and behavior of SINGLE_NODE paradigm")
    def test_allocate_single_node_valid(self):
        """
            Test single node scheduling with valid resources for first node
        """
        request_cpus = 5
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:1])
        #job = self.mock_job(cpus=request_cpus, strategy='SINGLE_NODE')
        allocation = self.resource_manager.allocate_single_node(request_cpus, mem)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation[0].cpu_count, request_cpus)
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')

    @unittest.skip("Test no longer reflects design and behavior of SINGLE_NODE paradigm")
    def test_allocate_single_node_valid_a(self):
        """
            Test single node scheduling with valid resources which won't fit on first node
        """
        request_cpus=10
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:2])
        allocation = self.resource_manager.allocate_single_node(request_cpus, mem)
        self.assertIsNotNone(allocation)
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation[0].cpu_count, request_cpus)
        self.assertEqual(allocation[0].hostname, 'hostname2')
        self.assertEqual(allocation[0].pool_id, 'Node-0002')

    @unittest.skip("Test no longer reflects design and behavior of SINGLE_NODE paradigm")
    def test_allocate_single_node_unsatisfied(self):
        """
            Test single node scheduling with valid resources which cannot satisfy request
        """
        request_cpus=100
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources)
        test = self.resource_manager.allocate_single_node(request_cpus, mem)
        self.assertEqual(len(test), 1)
        self.assertIsNone(test[0])

    @unittest.skip("Test no longer reflects design and behavior of FILL_NODES paradigm")
    def test_allocate_fill_nodes_valid(self):
        """
            Test fill nodes scheduling with valid resources for first node
        """
        cpus = 5
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:1])
        allocation = self.resource_manager.allocate_fill_nodes(cpus, mem)

        self.assertEqual(len(allocation), 1)
        self.assertIsNotNone(allocation[0])
        self.assertEqual(allocation[0].cpu_count, cpus)
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')

    @unittest.skip("Test no longer reflects design and behavior of FILL_NODES paradigm")
    def test_allocate_fill_nodes_valid_a(self):
        """
            Test fill nodes scheduling with valid resources for two nodes
        """
        cpus = 10
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:2])
        allocation = self.resource_manager.allocate_fill_nodes(cpus, mem)

        self.assertEqual(len(allocation), 2)
        self.assertIsNotNone(allocation[0])
        self.assertIsNotNone(allocation[1])
        #Validate resources on first node
        self.assertEqual(allocation[0].cpu_count, 5)
        #TODO this assumes an order of resources, may not be appropriate for all subclasses
        #However, we can be confident that 2 are returned, since we are only using two resources
        #and one of them only has 5 cpus.  We can maket this testing more clear
        #if we derive the mock resource explicitly and then set them on the manager
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')
        #Validate resources on second node
        self.assertEqual(allocation[1].cpu_count, 5)
        self.assertEqual(allocation[1].hostname, 'hostname2')
        self.assertEqual(allocation[1].pool_id, 'Node-0002')

    @unittest.skip("Test no longer reflects design and behavior of FILL_NODES paradigm")
    def test_allocate_fill_nodes_unsatisfied(self):
        """
            Test fill nodes scheduling with valid resources which cannot satisfy request
        """
        cpus=500
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources)
        allocation = self.resource_manager.allocate_fill_nodes(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNone(allocation[0])

    @unittest.skip("Test no longer reflects design and behavior of ROUND_ROBIN paradigm")
    def test_allocate_round_robin_valid(self):
        """
            Test round_robin scheduling with valid resources for first node
        """
        cpus = 5
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:1])
        allocation = self.resource_manager.allocate_round_robin(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNotNone(allocation[0])
        self.assertEqual(allocation[0].cpu_count, cpus)
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')

    @unittest.skip("Test no longer reflects design and behavior of ROUND_ROBIN paradigm")
    def test_allocate_round_robin_valid_a(self):
        """
            Test round_robin scheduling with valid resources for two nodes
        """
        cpus = 10
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources[0:2])
        allocation = self.resource_manager.allocate_round_robin(cpus, mem)
        self.assertEqual(len(allocation), 2)

        #Validate resources on first node
        self.assertIsNotNone(allocation[0])
        self.assertEqual(allocation[0].cpu_count, 5)
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')
        #Validate resources on second node
        self.assertIsNotNone(allocation[1])
        self.assertEqual(allocation[1].cpu_count, 5)
        self.assertEqual(allocation[1].hostname, 'hostname2')
        self.assertEqual(allocation[1].pool_id, 'Node-0002')

    @unittest.skip("Test no longer reflects design and behavior of ROUND_ROBIN paradigm")
    def test_allocate_round_robin_valid_b(self):
        """
            Test round_robin scheduling with valid resources for multiple nodes
        """
        cpus = 5
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources)
        allocation = self.resource_manager.allocate_round_robin(cpus, mem)
        self.assertEqual(len(allocation), 3)


        #Validate resources on first node
        self.assertIsNotNone(allocation[0])
        self.assertEqual(allocation[0].cpu_count, 2)
        self.assertEqual(allocation[0].hostname, 'hostname1')
        self.assertEqual(allocation[0].pool_id, 'Node-0001')
        #Validate resources on second node
        self.assertIsNotNone(allocation[1])
        self.assertEqual(allocation[1].cpu_count, 2)
        self.assertEqual(allocation[1].hostname, 'hostname2')
        self.assertEqual(allocation[1].pool_id, 'Node-0002')
        #Validate resources on third node
        self.assertIsNotNone(allocation[2])
        self.assertEqual(allocation[2].cpu_count, 1)
        self.assertEqual(allocation[2].hostname, 'hostname3')
        self.assertEqual(allocation[2].pool_id, 'Node-0003')

    @unittest.skip("Test no longer reflects design and behavior of ROUND_ROBIN paradigm")
    def test_allocate_round_robin_unsatisfied(self):
        """
            Test round_robin scheduling with valid resources which cannot satisfy request
        """
        cpus=500
        mem = 1000000
        self.resource_manager.set_resources(self.mock_resources)
        allocation = self.resource_manager.allocate_round_robin(cpus, mem)
        self.assertEqual(len(allocation), 1)
        self.assertIsNone(allocation[0])
