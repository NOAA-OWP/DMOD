import unittest
from ..scheduler.scheduler import Scheduler
from ..scheduler.job import RequestedJob, JobAllocationParadigm
from dmod.communication.scheduler_request import SchedulerRequestMessage
from dmod.communication.maas_request import NWMRequest

from . import EmptyResourceManager, MockResourceManager, mock_resources

class TestResourceManagerBase(unittest.TestCase):
    _request_string = '{{"model_request": {{"model": {{"NWM": {{"version": 2.0, "output": "streamflow", "parameters": {{}}}}}}, "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}}, "user_id": "someone", "cpus": {cpus}, "mem": {mem}'
    _request_json = {"model_request": {
        "model": {"NWM": {"version": 2.0, "output": "streamflow", "parameters": {}}},
        "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c"}, "user_id": "someone",
                               "cpus": 4, "mem": 500000, "allocation":"SINGLE_NODE"}

    def mock_job(self, cpus: int = 4, mem: int = 500000, strategy: str = "single_node") -> RequestedJob:
        """
            Generate a mock job with given cpu request
        """
        # Example 0
        request_string = self._request_string.format(cpus=cpus, mem=mem)
        request_json = self._request_json
        request_json['cpus'] = cpus
        request_json['mem'] = mem
        model_request = NWMRequest.factory_init_from_deserialized_json(request_json)
        schedule_request = SchedulerRequestMessage(model_request=model_request,
                                    user_id=request_json['user_id'],
                                    cpus=cpus,
                                    mem=mem,
                                    allocation_paradigm=strategy)
        mock_job = RequestedJob(schedule_request)
        return mock_job

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


    def test_fill_nodes_validation_b(self):
        """
            Test fill node scheduling when invalid cpus are requested
        """
        cpus = 2.5
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_fill_nodes, cpus, mem)


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


class TestValidResources(TestResourceManagerBase):

    def setUp(self) -> None:

        self.requested_cpus = 10
        self.requested_memory = 1000000

        self.resource_manager = MockResourceManager()
        self.mock_resources = mock_resources()

    def tearDown(self) -> None:
        pass

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

