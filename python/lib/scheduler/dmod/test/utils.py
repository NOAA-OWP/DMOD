from ..scheduler.resources.resource_manager import ResourceManager
from ..scheduler.resources import Resource

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
        self.set_resources(mock_resources())
        self.resource_map = {'Node-0001':0, 'Node-0002':1, 'Node-0003':2}

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
      hostname = self.resources[resource_key]["Hostname"]
      cpus_allocated = 0
      error = True
      cpu_allocation_map={}
      available_cpus = self.resources[resource_key]["CPUs"]
      available_memory = self.resources[resource_key]["MemoryBytes"]
      if (available_cpus >= requested_cpus):
          #Can satisfy full request
          #Update the resource table
          self.resources[resource_key]["CPUs"] -= requested_cpus
          self.resources[resource_key]["MemoryBytes"] -= requested_memory
          allocated_cpus = requested_cpus
          error = False
      elif(partial and available_cpus > 0):
          #Can satisfy partial request
          #Update the resource table
          self.resources[resource_key]["CPUs"] -= requested_cpus
          self.resources[resource_key]["MemoryBytes"] -= requested_memory
          allocated_cpus = available_cpus
          error = False
      elif(partial and available_cpus == 0):
          #No error, just no allocation, no need to hit DB
          allocated_cpus = 0
          error = False
      else:
          #TODO consider exceptions here?  Let callers catch them and respond???
          #logging.debug("Requested CPUs greater than CPUs available: requested = {}, available = {}, NodeId = {}".format(requested_cpus, available_cpus, hostname))
          pass
      if not error:
          cpu_allocation_map = {'node_id': resource_id, 'Hostname': hostname, 'cpus_allocated': allocated_cpus,
                                'mem': requested_memory}

      #Return the allocation map, {} if failure
      return cpu_allocation_map

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
