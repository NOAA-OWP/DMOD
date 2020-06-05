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

    def test_single_node_validation(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = 0
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)

    def test_single_node_validation_a(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = -1
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)

    def test_single_node_validation_b(self):
        """
            Test single node scheduling when invalid cpus are requested
        """
        cpus = 2.5
        mem = 1000000
        self.assertRaises(ValueError, self.resource_manager.allocate_single_node, cpus, mem)
