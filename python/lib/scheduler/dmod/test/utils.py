from ..scheduler.resources.resource_manager import ResourceManager
from ..scheduler.resources import Resource, ResourceAllocation
from copy import deepcopy

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
def mock_resources():
    #return deepcopy(_mock_resources)
    mock_resources_list = list()
    for res in _mock_resources:
        mock_resources_list.append(Resource.factory_init_from_dict(res))
    return mock_resources_list


class MockResourceManager(ResourceManager):
    """
        A mock resource manager implementing the abstract interface for testing
        a set of mock resources
    """

    def __init__(self):
        #Let each test method explicity add its mock resources
        #self.set_resources(mock_resources())
        self.resource_map = {'Node-0001':0, 'Node-0002':1, 'Node-0003':2}

    def request_allocations(self, job):
        pass

    def release_resources(self, allocated_resources):
        pass

    def set_resources(self, resources):
        self.resources = resources

    def get_resources(self):
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
                          requested_memory:int =0, partial:bool =False):
      """
        Attemt to allocate the requested resources.
      """
      resource_key = self.resource_map[resource_id]
      allocation = None

      resource = self.resources[resource_key]
      cpus_allocated, mem_allocated, is_fully = resource.allocate(requested_cpus, requested_memory)

      if is_fully or (partial and cpus_allocated > 0 and (mem_allocated > 0 or requested_memory == 0)):
          self.resources[resource_key] = resource.to_dict()
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
