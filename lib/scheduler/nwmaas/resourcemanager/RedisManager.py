#!/usr/bin/env python3
from typing import Iterable, Mappable, Union
from abc import ABC, abstractmethod
from redis import Redis, WatchError
import logging

## local imports
from .utils import keynamehelper as keynamehelper
from .utils import generate as generate
from .utils import parsing_nested as pn
from .utils.clean import clean_keys

from .ResourceManager import ResourceManager

Max_Redis_Init = 5

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")

resources = [{'node_id': "Node-0001",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 18,
           'MemoryBytes': 33548128256
          },
          {'node_id': "Node-0002",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 96,
           'MemoryBytes': 540483764224
          },
          {'node_id': "Node-0003",
           'Hostname': "***REMOVED***",
           'Availability': "active",
           'State': "ready",
           'CPUs': 96,
           'MemoryBytes': 540483764224
          }
         ]

class RedisManager(ResourceManager):
    """
        Implementation class for defining a redis backed ResourceManager
    """

    def __init__(self, resource_pool: str):
        # initialize Redis client
        n = 0
        while (n <= Max_Redis_Init):
            try:
                 self.redis = Redis(host=os.environ.get("REDIS_HOST", "myredis"),
                 #self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                              port=os.environ.get("REDIS_PORT", 6379),
                              # db=0, encoding="utf-8", decode_responses=True,
                              db=0, decode_responses=True,
                              #FIXME scrub
                              password='***REMOVED***')
            #FIXME execpt only redis failures here
            except:
                logging.debug("redis connection error")
            time.sleep(1)
            n += 1
            if (self.redis != None):
                break
            # self._jobQ = queue.deque()
            # _MAX_JOBS is set to currently available total number of CPUs
            self._MAX_JOBS = MAX_JOBS
            #Redis configuration and usage setup
            #TODO find a clearer way to set this...probably need to to do it on init of the module, and pull from
            #the env the stack the module is running in (or from the docker API???
            # self.keyname_prefix = "nwm-master" #FIXME parameterize
            #resources is a NON-SCOPED key, global for all "schedulers"
            #FIXME parameterize resource pool, allowing a scheduler to be initialized to use an existing pool in redis
            self.set_prefix("") #A bug in keynamehelper emerges when prefix is not explicitly set to a string
            self.resource_pool = resource_pool #"maas"
            #Key to redis set containing ID's for all resources available to this "pool"
            #These resrouces can be viewed at redis key resource_pool_key:ID
            self.resource_pool_key = keynamehelper.create_key_name("resources", self.resource_pool)

            """ Don't prefix the scheduler instance.  This MIGHT work for partitioning sinilar to the key structure above, not sure...
            self.keyname_prefix = "maas-scheduler" #FIXME parameterize
            self.set_prefix()
            """
            #self.create_resources()


    def set_prefix(self):
        keynamehelper.set_prefix(self.keyname_prefix)

    def set_resources(self, resources: Iterable[ Mapping[ str, Union[ str, int] ] ]):
        """
            Set the provided resources into the manager's resource tracker.

            Parameters
            ----------
            resources
                An iterable of maps defining each resource to set.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

            Returns
            -------
            None
        """
        #Create a global resources set key
        resource_list_key = keynamehelper.create_key_name("resources")
        for resource in resources:
            resource_id = resource['node_id']
            #Create a resource identity key for resource metadata hash map
            resource_metadata_key = keynamehelper.create_key_name("resource", resource_id)
            #Add resource metadata for this resource
            self.redis.hmset(resource_metadata_key, resource)
            #add resource_id to set of all resources
            self.redis.sadd(resource_list_key, resource_id)


    def get_resources(self) -> Iterable[Mappable[str, Union[str, int]]]:
        """ TODO kwarg for ids only vs full metadata
            list or generator???
            Get metadata of all managed resoures.

            Returns
            -------
            resources
                An iterable of maps defining each managed resource.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

        """
        #TODO add a sort_by keyword arg, then the results can be sorted based on
        #some other metadata, i.e. least full... would require an additional DB
        #read to read metadata for each resource in resource_pool_key but would
        #unlock additional scheduling techniques.
        for resource in resources:
            resource_metadata_key = keynamehelper.create_key_name(self.resource_pool_key, resource)
            yield redis.hgetall(resource_metadata_key)


    def get_resource_ids(self) -> Iterable[Union[str, int]]:
        """
            Get the identifiers for all managed resources

            Returns
            -------
            list of resource id's

        """
        #Lookup our resource pool, i.e. the list of resources we can use
        #TODO for large enough resource sets, switch to SSCAN and cursor iteration
        return self.redis.smembers(self.resource_pool_key)

    @abstractmethod
    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory:int =0, partial:bool =False) -> Mappable[str, Union[str, int]]:
      """
        Attemt to allocate the requested resources.  Successful allocation will return
        a non empty map.

        Parameters
        ----------
        resource_id
            Unique ID string of the resource referenceable by the manager

        requested_cpus
            integer numbre of cpus to attempt to allocate

        requested_momory
            integer number of bytes to allocate.  currently optional

        partial
            whether to partially fullfil the requested allocation and return
            an allocation map with less than the requested allocation


      """
      resource_key = keynamehelper.create_key_name(self.resource_pool_key, resource_id)
      hostname = str(redis.hget(resource_key, "Hostname"))
      cpus_allocated = 0

      with self.redis.pipeline() as pipe: #Use the context manager to cleanup connection, i.e. pipe.reset() automatically
          while True: #Attempt the transaction with check and set semantics
              try:
                  redis.watch(resource_key) #Will get WatchError if the value changes between now and pipe.execute()
                  #pipe.execute will use the pipe connection, but execute immediately due to the above watch ^^
                  available_cpus = int(pipe.hget(resource_key, "CPUs"))
                  available_memory = int(pipe.hget(resource_key, "MemoryBytes"))
                  if (available_cpus >= requested_cpus):
                      #Can satisfy full request
                      #Update the redis resource table in atomic pipeline
                      #indicate the atomic operations with multi()
                      pipe.multi()
                      pipe.hincrby(resource_key, "CPUs", -requested_cpus)
                      pipe.hincrby(resource_key, "MemoryBytes", -requested_memory) #TODO/FIXME
                      #req_id, cpus_dict = self.metadata_mgmt(p, e_key, user_id, cpus_alloc, mem, NodeId, index)
                      p.execute() #End transaction
                      allocated_cpus = requested_cpus
                      error = False
                  elif(partial and available_cpus > 0):
                      #Can satisfy partial request
                      #Update the redis resource table in atomic pipeline
                      pipe.multi()
                      pipe.hincrby(resource_key, "CPUs", -available_cpus)
                      pipe.hincrby(resource_key, "MemoryBytes", -requested_memory) #TODO/FIXME
                      #req_id, cpus_dict = self.metadata_mgmt(p, e_key, user_id, cpus_alloc, mem, NodeId, index)
                      pipe.execute()
                      allocated_cpus = available_cpus
                      error = False
                  elif(partial and available_cpus == 0):
                      #No error, just no allocation, no need to hit DB
                      allocated_cpus = 0
                      error = False
                  else:
                      #TODO consider exceptions here?  Let callers catch them and respond???
                      logging.debug("Requested CPUs greater than CPUs available: requested = {}, available = {}, NodeId = {}".format(requested_cpus, available_cpus, hostname))

                  if not error:
                      cpu_allocation_map = {'node_id': resource_id, 'Hostname': hostname, 'cpus_allocated': allocated_cpus,
                                            'mem': requested_memory}
                  #Break the infinite watch error retry loop
                  break
          except WatchError:
              logging.debug("Write Conflict allocate_resource: {}. Retrying...".format(e_key))
              #Try the transaction again
              continue
      #Return the allocation map, {} if failure
      return cpu_allocation_map

    def release_resources(self, allocated_resources: Iterable[ Mappable[ str, Union[ str, int ] ] ]):
        """
            Give back any allocated resources to the manager.

            Parameters
            ----------
            allocated_resources
                An iterable of maps containing the metadata returned by allocate_resources
        """
        #Give back any allocated resources to the master resrouce table
        for resource in allocated_resource:
            resource_id = resource['node_id']
            resource_key = keynamehelper.create_key_name(self.resource_pool_key, resource_id)
            with self.redis.pipeline() as pipe:
                #Don't need to loop since we are reading/writing, just writing
                pipe.hincrby(resource_key, "CPUs", resource['cpus_allocated'])
                pipe.hincrby(resource_key, "MemoryBytes", resource['mem'])
                pipe.execute()

    def get_available_cpu_count(self) -> int:
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        #TODO move total available to redis key by itself, update after all allcoation/release
        total_available = 0
        #Should pipline this for efficiency
        for resource in self.get_resources():
            resource_metadata_key = keynamehelper.create_key_name(self.resource_pool_key, resource)
            CPUs = int(redis.hget(resource_metadata_key, "CPUs"))
            total_CPUs += CPUs
        return total_available

    def create_job_entry(self, cpu_allocation_map):
        """
            Create a job id and add it to the redis instance
            TODO this might be better in a different class
            explictit for job handling, and maybe even an independent
            redis instance.  This may move in the near future.
        """
        
        req_id = generate.order_id()
        #Set to add the running job ID to
        job_state = keynamehelper.create_key_name(self.resource_pool_key, "running")
        self.redis.sadd(job_state, req_id)

        #Job key to store metadata about this job at
        job_key = keynamehelper.create_key_name("job", req_id)
        #map of resources this job is using
        self.redis.hmset(job_key, cpu_allocaion_map)
