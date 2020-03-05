#!/usr/bin/env python3
from typing import Iterable, Mapping, Union, Optional
from abc import ABC, abstractmethod
from redis import Redis, WatchError
import logging
import time

## local imports
from .utils import keynamehelper as keynamehelper
from .utils import generate as generate

from .resource_manager import ResourceManager

Max_Redis_Init = 5

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")

class RedisManager(ResourceManager):
    """
        Implementation class for defining a redis backed ResourceManager
    """

    _DEFAULT_DOCKER_SECRET_REDIS_PASS = 'myredis_pass'
    _DEFAULT_REDIS_PASS = ''
    _ENV_NAME_DOCKER_SECRET_REDIS_PASS = 'DOCKER_SECRET_REDIS_PASS'
    _ENV_NAME_REDIS_PASS = 'REDIS_PASS'

    @classmethod
    def get_docker_secret_redis_pass(cls):
        return os.getenv(cls._ENV_NAME_DOCKER_SECRET_REDIS_PASS, cls._DEFAULT_DOCKER_SECRET_REDIS_PASS)

    @classmethod
    def get_redis_pass(cls):
        password_filename = '/run/secrets/' + cls.get_docker_secret_redis_pass()
        try:
            with open(password_filename, 'r') as redis_pass_secret_file:
                return redis_pass_secret_file.read()
        except:
            pass
        # Fall back to env if no secrets file, further falling back to default if no env value
        return os.getenv(cls._ENV_NAME_REDIS_PASS, cls._DEFAULT_REDIS_PASS)

    def __init__(self, resource_pool: str, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
        # initialize Redis client
        if redis_host is None:
            #Try to read redis host from environment var, else set it default 'redis'
            redis_host = host=os.environ.get("REDIS_HOST", "redis")
        if redis_port is None:
            #Try to read port from environment, else use default 6379
            redis_port = os.environ.get("REDIS_PORT", 6379)
        if redis_pass is None:
            #Read password from environment
            redis_pass = self.get_redis_pass()

        n = 0
        while (n <= Max_Redis_Init):
            try:
                 self.redis = Redis(host=redis_host,
                 #self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                              port=redis_port,
                              # db=0, encoding="utf-8", decode_responses=True,
                              db=0, decode_responses=True,
                              password=redis_pass)
            #FIXME execpt only redis failures here
            except:
                logging.debug("redis connection error")
            time.sleep(1)
            n += 1
            if (self.redis != None):
                break
        if self.redis == None:
            raise RuntimeError("Unable to connect to redis database")

        self.set_prefix("") #A bug in keynamehelper emerges when prefix is not explicitly set to a string
        self.resource_pool = resource_pool #"maas"
        #Key to redis set containing ID's for all resources available to this "pool"
        #These resrouces can be viewed at redis key resource_pool_key:ID
        self.resource_pool_key = keynamehelper.create_key_name("resources", self.resource_pool)

        dev_opt = kwargs.get('type', 'prod')
        if dev_opt == 'dev':
            self._dev_setup()

    def _dev_setup(self):
        from .utils.clean import clean_keys
        clean_keys(self.redis)
        self.set_prefix("dev")
        self.set_resources(resources)

    def set_prefix(self, prefix):
        keynamehelper.set_prefix(prefix)

    def add_resource(self, resource: Mapping[ str, Union[ str, int] ], resource_pool_key: str):
        """
            Add a single resource to this managers pool

            Parameters
            ----------
            resource
            Map defining the resource to add with the following metadata
            {  'node_id': "Node-0001",
               'Hostname': "my-host",
               'Availability': "active",
               'State': "ready",
               'CPUs': 18,
               'MemoryBytes': 33548128256
             }

             resource_pool_key
                string identifying the resource list to associate this resource with
        """
        #FIXME properly validate the existance of meta data at some point in the chain
        resource_id = resource['node_id']
        #Create a resource identity key for resource metadata hash map
        resource_metadata_key = keynamehelper.create_field_name(resource_pool_key,
                                                              "meta", resource_id)
        #print("MANAGER ADD RESOURCE -- METADATA KEY: {}".format(resource_metadata_key))
        #print("MANAGER ADD RESOURCE -- POOL KEY: {}".format(resource_pool_key))
        if self.redis.exists(resource_metadata_key) == 0:
            #Only add resources if they don't already exist
            #Add resource metadata for this resource
            self.redis.hmset(resource_metadata_key, resource)
            #add resource_id to set of all resources
            self.redis.sadd(resource_pool_key, resource_id)

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
        #Assuming all resources set via this method belong to our pool
        #TODO allow a resource manager to get/set from different pools?
        for resource in resources:
            self.add_resource(resource, self.resource_pool_key)

    def get_resources(self) -> Iterable[Mapping[str, Union[str, int]]]:
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
        for resource in self.get_resource_ids():
            #FIXME decide on resource_pool_key usage
            resource_metadata_key = keynamehelper.create_field_name(self.resource_pool_key, 'meta', resource) #(self.resource_pool_key, resource)
            yield self.redis.hgetall(resource_metadata_key)


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

    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory:int =0, partial:bool =False) -> Mapping[str, Union[str, int]]:
      """
        Attemt to allocate the requested resources.  Successful allocation will return
        a non empty map. TODO document return map structure

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
      resource_key = keynamehelper.create_field_name(self.resource_pool_key, 'meta', resource_id)
      #print("MANAGER::ALLOCATE KEY -- {}".format(resource_key))
      if requested_cpus <= 0 or not self.redis.exists(resource_key):
          return {}

      hostname = str(self.redis.hget(resource_key, "Hostname"))
      cpus_allocated = 0
      error = True #Assume error unless explicitly verified allocation occurs
      cpu_allocation_map = {} #assume no allocation until explicitly provided
      with self.redis.pipeline() as pipe: #Use the context manager to cleanup connection, i.e. pipe.reset() automatically
          while True: #Attempt the transaction with check and set semantics
              try:
                  pipe.watch(resource_key) #Will get WatchError if the value changes between now and pipe.execute()
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
                      pipe.execute() #End transaction
                      allocated_cpus = requested_cpus
                      error = False
                  elif(partial and available_cpus > 0):
                      #Can satisfy partial request
                      #Update the redis resource table in atomic pipeline
                      pipe.multi()
                      pipe.hincrby(resource_key, "CPUs", -available_cpus)
                      pipe.hincrby(resource_key, "MemoryBytes", -requested_memory) #TODO/FIXME
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
                  logging.debug("Write Conflict allocate_resource: {}. Retrying...".format(resource_key))
                  #Try the transaction again
                  continue
      #Return the allocation map, {} if failure
      return cpu_allocation_map

    def release_resources(self, allocated_resources: Iterable[ Mapping[ str, Union[ str, int ] ] ]):
        """
            Give back any allocated resources to the manager.

            Parameters
            ----------
            allocated_resources
                An iterable of maps containing the metadata returned by allocate_resources
        """
        #Give back any allocated resources to the master resrouce table
        for resource in allocated_resources:
            resource_id = resource['node_id']
            resource_key = keynamehelper.create_field_name(self.resource_pool_key, 'meta', resource_id)
            if not self.redis.exists(resource_key):
                raise RuntimeError("RedisManager::release_resources -- No key {} exists to release resources to".format(resource_key))
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
        for resource in self.get_resource_ids():
            resource_metadata_key = keynamehelper.create_field_name(self.resource_pool_key, "meta", resource)
            CPUs = int(self.redis.hget(resource_metadata_key, "CPUs"))
            total_available += CPUs
        return total_available

    def create_job_entry(self, allocations: Iterable[ Mapping[ str, Union[ str, int ] ]]) -> str:
        """
            FIXME cpu_allocation_map should be list of maps!  Store all allocs in redis
            Create a job id and add it to the redis instance
            TODO this might be better in a different class
            explictit for job handling, and maybe even an independent
            redis instance.  This may move in the near future.

            Returns
            -------
            job_id identifier for the job which can be used to query the redis instance managing
                   the job meta data
        """

        job_id = generate.order_id()
        #Set to add the running job ID to
        job_state = keynamehelper.create_field_name(self.resource_pool_key, "running")
        self.redis.sadd(job_state, job_id)

        for i, cpu_allocation_map in enumerate(allocations):
            #Job key to store metadata about this job at
            job_key = keynamehelper.create_key_name("job", job_id, str(i))
            #map of resources this job is using
            #print("MANAGER CREATE JOB ENTRY -- KEY {}".format(job_key))
            self.redis.hmset(job_key, cpu_allocation_map)
        return job_id
    """
        FIXME parking this function here since it is closely related to the
        the creat_job_entry function.  I don't think the user_id centric pinning
        is the best way, nor I think requests should be the targer, should be
        jobs.  This starts to hint at a "job manager" set of classes/interfaces
        this allows to decouple the concetps of requests, allocations, and jobs.

        The following function should be more througuly reviewed and designed.
    """
    def retrieve_job_metadata(self, user_id):
        """
        Retrieve queued job info from the database using user_id as a key to the job_id list
        Using job_id to uniquely retrieve the job request dictionary: cpus_dict
        Build nested cpusList from cpus_dict
        The code only retrieve one job that make up cpusList. Complete job list is handled in check_jobQ
        For comprehensive info on all jobs by a user in the database, a loop can be used to call this method
        """
        return #DEACIVATING THIS FUNCTION TILL FIXME ABOVE SORTED
        redis = self.redis
        cpusList = []
        user_key = keynamehelper.create_key_name(user_id)

        # case for index = 0, the first popped index is necessarily 0
        # lpop and rpush are used to guaranttee that the earlist queued job gets to run first
        job_id = redis.lpop(user_key)
        if (job_id != None):
            print("In retrieve_job_metadata: user_key", user_key, "job_id = ", job_id)
            req_key = keynamehelper.create_key_name("job_request", job_id)
            cpus_dict = redis.hgetall(req_key)
            cpusList.append(cpus_dict)
            index = cpus_dict['index']             # index = 0
            if (int(index) != 0):
                raise Exception("Metadata access error, index = ", index, " job_id = ", job_id)

        # cases for the rest of index != 0, job belongs to a different request if index = 0
        while (job_id != None):                    # previous job_id
            job_id = redis.lpop(user_key)          # new job_id
            if (job_id != None):
                req_key = keynamehelper.create_key_name("job_request", job_id)
                cpus_dict = redis.hgetall(req_key)
                index = cpus_dict['index']         # new index
                if (int(index) == 0):
                    redis.lpush(user_key, job_id)  # return the popped value, the job request belongs to a different request if index = 0
                    break
                else:
                    cpusList.append(cpus_dict)
                print("In retrieve_job_metadata: user_key", user_key, "job_id = ", job_id)
        print("\nIn retrieve_job_metadata: cpusList:\n", *cpusList, sep = "\n")
        print("\nIn retrieve_job_metadata:")
        print("\n")
        return cpusList
