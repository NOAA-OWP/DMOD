from ..scheduler.job import RequestedJob
from ..scheduler.resources import Resource, ResourceAllocation, ResourceManager
from dmod.communication import NWMRequest, NGENRequest, SchedulerRequestMessage
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement, DiscreteRestriction
from uuid import uuid4
from typing import List

from copy import deepcopy
import logging
import sys

#TODO move this somewhere all test code can borrow it
class logTest():
    """
        Decorator for enabling stream logging of a test function
    """
    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger()
        self.logger.level = log_level

    def __call__(self, func):
        def wrapped(*args):
            stream_handler = logging.StreamHandler(sys.stdout)
            self.logger.addHandler(stream_handler)
            return func(*args)
        return wrapped

_mock_resources = [{'node_id': "Node-0001",
           'Hostname': "hostname1",
           'Availability': "active",
           'State': "ready",
           'CPUs': 5,
           'MemoryBytes': 30000000000
          },
          {'node_id': "Node-0002",
           'Hostname': "hostname2",
           'Availability': "active",
           'State': "ready",
           'CPUs': 96,
           'MemoryBytes': 500000000000
          },
          {'node_id': "Node-0003",
           'Hostname': "hostname3",
           'Availability': "active",
           'State': "ready",
           'CPUs': 42,
           'MemoryBytes': 200000000000
          }
         ]

_request_json = {
    "model": None,
    "session-secret": "f21f27ac3d443c0948aab924bddefc64891c455a756ca77a4d86ec2f697cd13c", "user_id": "someone",
                           "cpus": 4, "mem": 500000, "allocation":"SINGLE_NODE"}
_nwm_model = {"nwm": {"config_data_id": "1", "data_requirements": [{"domain": {
    "data_format": "NWM_CONFIG", "continuous": [], "discrete": [{"variable": "data_id", "values": ["1"]}]},
    "is_input": True,
    "category": "CONFIG"}]}}
_time_range = {"variable": "time", "subclass": "TimeRange", "datetime_pattern": "%Y-%m-%d %H:%M:%S", "begin": "2022-01-01 00:00:00", "end": "2022-02-01 00:00:00"}
_ngen_model = {"name": "ngen",
               "time_range": _time_range,
               "hydrofabric_data_id": "00000000-0000-0000-0000-000000000000",
               "hydrofabric_uid": "00000000-0000-0000-0000-000000000001",
               "config_data_id": "00000000-0000-0000-0000-000000000002",
               "bmi_config_data_id": "00000000-0000-0000-0000-000000000003",
               "catchments": {"variable": "catchment-id", "values": []},
               "version": 4.0}

def mock_job(model: str = 'nwm', cpus: int = 4, mem: int = 500000, strategy: str = "single_node", allocations: int = 0) -> RequestedJob:
    """
        Generate a mock job with given cpu request
    """

    request_json = _request_json
    request_json['cpus'] = cpus
    request_json['mem'] = mem

    if model == 'nwm':
        request_json['model'] = _nwm_model
        model_request = NWMRequest.factory_init_from_deserialized_json(request_json)
        output_requirement = None
    elif model == 'ngen':
        request_json['model'] = _ngen_model
        dataset_name = 'test_output_dataset_1'
        model_request = NGENRequest.factory_init_from_deserialized_json(request_json)
        data_domain = DataDomain(data_format=DataFormat.NGEN_CSV_OUTPUT,
                                 discrete_restrictions=[DiscreteRestriction(variable='id', values=[])])
        output_requirement = DataRequirement(domain=data_domain, is_input=False, category=DataCategory.OUTPUT,
                                             fulfilled_by=dataset_name)
    else:
        raise(ValueError("Unsupported mock model {}".format(model)))

    schedule_request = SchedulerRequestMessage(model_request=model_request,
                                user_id=request_json['user_id'],
                                cpus=cpus,
                                mem=mem,
                                allocation_paradigm=strategy)
    mock_job = RequestedJob(schedule_request)
    if output_requirement is not None:
        mock_job.data_requirements.append(output_requirement)
    #mock_job.job_id = uuid4()
    allocs = []
    for i in range(1, allocations+1):
        allocs.append( ResourceAllocation(str(i), 'hostname{}'.format(i), cpus, mem) )
    mock_job.allocations = allocs

    return mock_job


def mock_resources() -> List[Resource]:
    #return deepcopy(_mock_resources)
    mock_resources_list: List[Resource] = [Resource.factory_init_from_dict(res) for res in _mock_resources]
    if None in mock_resources_list:
        raise RuntimeError("Found 'None' in deserialized mock resources")
    return mock_resources_list


class MockResourceManager(ResourceManager):
    """
        A mock resource manager implementing the abstract interface for testing
        a set of mock resources
    """

    def __init__(self):
        #Let each test method explicity add its mock resources
        #self.set_resources(mock_resources())
        self.resource_map = {'Node-0001': 0, 'Node-0002': 1, 'Node-0003': 2}
        self.resources: List[Resource] = []

    def request_allocations(self, job):
        pass

    def release_resources(self, allocated_resources):
        pass

    def set_resources(self, resources: List[Resource]):
        self.resources = resources

    def get_resources(self) -> List[Resource]:
        """
            Get metadata of all managed resoures.
        """
        return self.resources

    def get_resource_ids(self):
        """
            Get the identifiers for all managed resources

        """
        for resource in self.resources:
            yield resource['node_id']

    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory: int = 0, partial: bool = False):
      """
      Attempt to allocate the requested resources.
      """
      if resource_id not in self.resource_map:
          raise RuntimeError('Bad resource id to {}: {}'.format(self.__class__.__name__, resource_id))

      resource_key = self.resource_map[resource_id]
      allocation = None

      if resource_key > len(self.resources):
          raise RuntimeError('Bad resource list index from mapping in {}: {}'.format(self.__class__.__name__, resource_key))

      resource: Resource = self.resources[resource_key]
      print('Class type is {}'.format(resource.__class__.__name__))
      cpus_allocated, mem_allocated, is_fully = resource.allocate(requested_cpus, requested_memory)

      if is_fully or (partial and cpus_allocated > 0 and (mem_allocated > 0 or requested_memory == 0)):
          self.resources[resource_key] = resource
          allocation = ResourceAllocation(resource_id, resource.hostname, cpus_allocated, mem_allocated)
      else:
          resource.release(cpus_allocated, mem_allocated)

      return allocation

    def get_available_cpu_count(self):
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        count = 0
        for id in self.get_resource_ids():
            count += self.resources[ self.resource_map[id] ]['CPUs']
        return count

    def create_job_entry(self, allocation_map):
        return "42"

class EmptyResourceManager(MockResourceManager):
    """
        A mock resource manager implementing the abstract interface for testing
        a set of non-existing resources
    """
    def __init__(self):
        self.resources = mock_resources()
        mock_resources_list = list()
        for res in _mock_resources:
            local = deepcopy(res)
            local['CPUs'] = 0
            mock_resources_list.append(Resource.factory_init_from_dict(local))
        self.set_resources(mock_resources_list)
