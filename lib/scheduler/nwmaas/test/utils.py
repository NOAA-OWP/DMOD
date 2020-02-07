from ..resourcemanager.ResourceManager import ResourceManager

mock_resources = [{'node_id': "Node-0001",
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

class EmptyResourceManager(ResourceManager):
    """
        A mock resource manager implementing the abstract interface for testing
        a set of non-existing resources
    """
    def __init__(self):
        self.resources={}

    def release_resources(self):
        pass
    
    def set_resources(self):
        self.resources={}

    def get_resources(self):
        """
            Get metadata of all managed resoures.
        """
        return [{}]

    def get_resource_ids(self):
        """
            Get the identifiers for all managed resources

        """
        []

    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory:int =0, partial:bool =False):
      """
        Attemt to allocate the requested resources.
      """
      return {}

    def get_available_cpu_count(self):
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        return 0
