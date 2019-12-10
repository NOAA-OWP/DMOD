#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import queue
import json, ast
import docker
# from itertools import chain
from pprint import pprint as pp
from redis import Redis, WatchError
import logging
import time

## local imports
from scheduler.utils import keynamehelper as keynamehelper
from scheduler.utils import generate as generate
from scheduler.utils import parsing_nested as pn
from nwmaas.communication import SchedulerRequestMessage, SchedulerRequestResponse
from scheduler.utils.clean import clean_keys

## local imports for unittest
# import scheduler.utils.keynamehelper as keynamehelper
# import scheduler.generate as generate
# import scheduler.parsing_nested as pn
# from scheduler.request import Request
# from scheduler.utils.clean import clean_keys

# client = docker.from_env()
# api_client = docker.APIClient()

MAX_JOBS = 210
Max_Redis_Init = 5

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")

# redis = None

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

resources = [{'node_id': "Node-0002",
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

class Scheduler:
    # def __init__(self, user_id, cpus, mem, resources,
    #              image, constraints, hostname, serv_labels, serv_name,
    #              docker_client=None, api_client=None):
    _jobQ = queue.deque()
    def __init__(self, docker_client=None, api_client=None, redis=None):
        if docker_client:
            self.docker_client = docker_client
            self.api_client = api_client
        else:
            self.checkDocker()
            self.docker_client = docker.from_env()
            self.api_client = docker.APIClient()

        # initialize Redis client
        n = 0
        while (n <= Max_Redis_Init):
            try:
                 self.redis = Redis(host=os.environ.get("REDIS_HOST", "myredis"),
                 #self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                              port=os.environ.get("REDIS_PORT", 6379),
                              # db=0, encoding="utf-8", decode_responses=True,
                              db=0, decode_responses=True,
                              password='***REMOVED***')
            except:
                logging.debug("redis connection error")
            time.sleep(1)
            n += 1
            if (self.redis != None):
                break

        # initialize variables for create_service()
        #self.image = "127.0.0.1:5000/nwm-2.0:latest"
        self.image =  "127.0.0.1:5000/nwm-master:latest"

        self.constraints = []
        self.hostname = "{{.Service.Name}}"
        self.labels =  {"com.docker.stack.image": "127.0.0.1:5000/nwm-2.0",
                        "com.docker.stack.namespace": "nwm"
                       }
        self.name = "nwm_mpi-worker_tmp"
        self.networks = ["mpi-net"]

        # self._jobQ = queue.deque()
        # _MAX_JOBS is set to currently available total number of CPUs
        self._MAX_JOBS = MAX_JOBS
        #TODO find a clearer way to set this...probably need to to do it on init of the module, and pull from
        #the env the stack the module is running in (or from the docker API???
        self.keyname_prefix = "nwm-master" #FIXME parameterize
        self.create_resources()
        self.set_prefix()

    def set_prefix(self):
        keynamehelper.set_prefix(self.keyname_prefix)

    def return42(self):
        return 42

    def create_resources(self):
        """ Create resource from the array of passed resource details"""
        e_set_key = keynamehelper.create_key_name("resources")
        for resource in resources:
            # print("In create_resources: CPUs = ", resource['CPUs'])
            # print("In create_resources: MemoryBytes = ", resource['MemoryBytes'])
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            self.redis.hmset(e_key, resource)
            self.redis.sadd(e_set_key, resource['node_id'])

    def create_user_from_username(self, user_id):
        """
           Get user id from the user input, store in database
           More info may be saved in the future
        """
        try:
            c_key = keynamehelper.create_key_name("user", user_id)
            user = {'user_id': user_id}
            self.redis.hmset(c_key, user)
        except:
            logging.debug("user not created")

    def check_single_node_availability(self, user_id, cpus, mem):
        """
        Check available resources to allocate job request to a single node to optimize
        computation efficiency
        """
        if (cpus <= 0):
            logging.debug("Invalid CPUs request: cpus = {}, CPUs should be an integer > 0".format(cpus))
            return

        if (not isinstance(cpus, int)):
            logging.debug("Invalid CPUs request: cpus = {}, CPUs must be a positive integer".format(cpus))
            return

        redis = self.redis

        index = 0
        cpusList = []
        cpus_dict = {}
        for resource in resources:
            NodeId = resource['node_id']
            e_key = keynamehelper.create_key_name("resource", NodeId)
            # if (cpus != 0):
            if (cpus > 0):
                p = redis.pipeline()
                try:
                    redis.watch(e_key)
                    # CPUs = int(redis.hget(e_key, resource['CPUs']))
                    CPUs = int(redis.hget(e_key, "CPUs"))
                    # MemoryBytes = int(redis.hget(e_key, "MemoryBytes"))
                    MemoryBytes = int(redis.hget(e_key, "MemoryBytes"))
                    if (CPUs < cpus):
                        continue
                    else:
                        cpus_alloc = cpus
                        req_id, cpus_dict = self.metadata_mgmt(p, e_key, user_id, cpus_alloc, mem, NodeId, index)
                        cpusList.append(cpus_dict)
                        p.execute()
                        # index += 1
                        break
                except WatchError:
                    logging.debug("Write Conflict check_single_node_availability: {}".format(e_key))
                finally:
                    p.reset()
                    logging.info("In check_single_node_availability: Allocation complete!")
            else:
                logging.debug("Allocation not performed for NodeId: {}, have {} CPUs, requested {} CPUs".format(NodeId, CPUs, cpus))
        if len(cpusList) == 0:
            logging.info("\nIn check_single_node_availability, allocation not performed: requested {} CPUs too large".format(cpus))
        print("\nIn check_single_node_availability:\ncpusList = {}".format(cpusList))
        return req_id, cpusList

    def check_generalized_round_robin(self, user_id, cpus, mem):
        """
        Check available resources on host nodes and allocate in round robin manner even the request
        can fit in a single node. This can be useful in test cases where large number of CPUs is
        inefficient for small domains and in filling the nodes when they are almost full
        """
        if (cpus <= 0):
            logging.debug("Invalid CPUs request: cpus = {},  CPUs should be an integer > 0".format(cpus))
            return

        if (not isinstance(cpus, int)):
            logging.debug("Invalid CPUs request: cpus = {}, CPUs must be a positive integer".format(cpus))
            return

        redis = self.redis
        num_node = len(resources)
        int_cpus = int(cpus / num_node)
        remain_cpus = cpus % num_node

        allocList = []
        iter = 0
        while iter < num_node:
            if (iter < remain_cpus):
                allocList.append(int_cpus+1)
            else:
                allocList.append(int_cpus)
            iter += 1

        # checking there are enough resources
        iter = 0
        # cpusList = []
        for resource in resources:
            NodeId = resource['node_id']
            e_key = keynamehelper.create_key_name("resource", NodeId)
            CPUs = int(redis.hget(e_key, "CPUs"))
            cpus_alloc = allocList[iter]
            if (cpus_alloc > CPUs):
                logging.debug("\nIn check_generalized_round_robin:")
                logging.debug("Requested CPUs greater than CPUs available: requested = {}, available = {}, NodeId = {}".\
                      format(cpus_alloc, CPUs, NodeId))
                # return cpusList
                return
            iter += 1

        index = 0
        cpusList = []
        cpus_dict = {}
        for resource in resources:
            NodeId = resource['node_id']
            e_key = keynamehelper.create_key_name("resource", NodeId)
            # if (cpus != 0):
            if (cpus > 0):
                p = redis.pipeline()
                try:
                    redis.watch(e_key)
                    # CPUs = int(redis.hget(e_key, resource['CPUs']))
                    CPUs = int(redis.hget(e_key, "CPUs"))
                    # MemoryBytes = int(redis.hget(e_key, "MemoryBytes"))
                    MemoryBytes = int(redis.hget(e_key, "MemoryBytes"))
                    cpus_alloc = allocList[index]

                    # if (cpus_alloc != 0):
                    if (cpus_alloc > 0):
                        req_id, cpus_dict = self.metadata_mgmt(p, e_key, user_id, cpus_alloc, mem, NodeId, index)
                        cpusList.append(cpus_dict)
                        p.execute()
                        index += 1
                except WatchError:
                    logging.debug("Write Conflict check_generalized_round_robin: {}".format(e_key))
                finally:
                    p.reset()
                    logging.info("In check_generalized_round_robin: Allocation complete!")
            else:
                logging.debug("Allocation not performed for NodeId: {}, have {} CPUs, requested {} CPUs".format(NodeId, CPUs, cpus))
        print("\nIn check_generalized_round_robin: \ncpusList:", *cpusList, sep = "\n")
        return req_id, cpusList

    def check_availability_and_schedule(self, user_id, cpus, mem):
        """Check available resources on host node and allocate based on user request"""
        if (cpus <= 0):
            logging.debug("Invalid CPUs request: cpus = {}, CPUs should be an integer > 0".format(cpus))
            return

        if (not isinstance(cpus, int)):
            logging.debug("Invalid CPUs request: cpus = {}, CPUs must be a positive integer".format(cpus))
            return

        redis = self.redis
        total_CPUs = 0
        # cpusList = []
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            CPUs = int(redis.hget(e_key, "CPUs"))
            total_CPUs += CPUs
        if (cpus > total_CPUs):
            print("\nRequested CPUs greater than CPUs available: requested = {}, available = {}".format(cpus, total_CPUs))
            # return cpusList
            return

        index = 0
        cpusList = []
        cpus_dict = {}
        for resource in resources:
            NodeId = resource['node_id']
            e_key = keynamehelper.create_key_name("resource", NodeId)
            # CPUs = int(redis.hget(e_key, resource['CPUs']))
            CPUs = int(redis.hget(e_key, "CPUs"))

            # if (cpus != 0):
            if (cpus > 0):
                p = redis.pipeline()
                try:
                    redis.watch(e_key)
                    # CPUs = int(redis.hget(e_key, resource['CPUs']))
                    CPUs = int(redis.hget(e_key, "CPUs"))
                    MemoryBytes = int(redis.hget(e_key, "MemoryBytes"))
                    if (CPUs <= cpus):             # request needs one or more nodes
                        cpus -= CPUs               # deduct all CPUs currently available on this node
                        cpus_alloc = CPUs
                    elif (cpus > 0):               # CPUS > cpus, request is smaller than CPUs on this node
                        cpus_alloc = cpus
                        cpus = 0
                    else:
                        break

                    if (cpus_alloc > 0):
                        req_id, cpus_dict = self.metadata_mgmt(p, e_key, user_id, cpus_alloc, mem, NodeId, index)
                        cpusList.append(cpus_dict)
                        p.execute()
                        index += 1
                except WatchError:
                    logging.debug("Write Conflict check_availability_and_schedule: {}".format(e_key))
                finally:
                    p.reset()
                    logging.info("In check_availability_and_schedule: Allocation complete!")
            else:
                logging.debug("Allocation not performed for NodeId: {}, have {} CPUs, requested {} CPUs".format(NodeId, CPUs, cpus))
        print("\nIn check_availability_and_schedule:\ncpusList: ", *cpusList, sep = "\n")
        return req_id, cpusList

    def metadata_mgmt(self, p, e_key, user_id, cpus_alloc, mem, NodeId, index):
        """function to manage resources and store job info to dadabase"""
        redis = self.redis
        p.hincrby(e_key, "CPUs", -cpus_alloc)
        p.hincrby(e_key, "MemoryBytes", -mem)
        req_id = generate.order_id()
        req_key = keynamehelper.create_key_name("job_request", req_id)
        req_set_key = keynamehelper.create_key_name("job_request", user_id)
        user_key = keynamehelper.create_key_name(user_id)
        Hostname = str(redis.hget(e_key, "Hostname"))
        cpus_dict = {'req_id': req_id, 'node_id': NodeId, 'Hostname': Hostname, 'cpus_alloc': cpus_alloc,
                     'mem': mem, 'index': index}
        p.hmset(req_key, cpus_dict)
        p.sadd(req_set_key, cpus_dict['req_id'])
        p.rpush(user_key, req_id)
        return req_id, cpus_dict

    def print_resource_details(self):
        """Print the details of remaining resources after allocating the request """
        logging.info("Resources remaining:")
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            logging.info("hgetall(e_key): {}".format(self.redis.hgetall(e_key)))
        logging.info("-" * 20)
        logging.info("\n")

    def service_to_host_mapping(self):
        """find host name based on service info"""
        # This code need split into two

        # docker api
        client = self.docker_client
        api_client = self.api_client

        # test out some service functions
        service_list = client.services.list()
        for service in service_list:
            service_id = service.id
            var = "service:" + service_id

        serviceList = []
        for service in service_list:
            service_id = service.id
            serv_list = client.services.list(filters={'id': service_id})[0]
            service_attrs = serv_list.attrs
            flat_dict = pn.flatten(service_attrs)
            # pp(list(flatten(service_attrs)))
            Name = list(pn.find('Name', service_attrs))[0]
            service_id = serv_list.id
            service_name = serv_list.name
            service_attrs = serv_list.attrs
            flat_dict = pn.flatten(service_attrs)
            Name = list(pn.find('Name', service_attrs))[0]
            if 'nwm_mpi-worker_' not in Name:
                continue
            else:
                Labels = list(pn.find('Labels', service_attrs))[0]
                NameSpace = Labels['com.docker.stack.namespace']
                Hostname = Labels['Hostname']
                cpus_alloc = Labels['cpus_alloc']
                Labels = Labels['com.docker.stack.image']
                (_, Labels) = Labels.split('/')
                Image = list(pn.find('Image', service_attrs))[0]
                (_, HostNode) = ((list(pn.find('Constraints', service_attrs))[0])[0]).split('==')
                service = client.services.get(service_id, insert_defaults=True)
                service_dict = {"Name": Name, "Labels": Labels, "HostNode": HostNode, "NameSpace": NameSpace, "Hostname": Hostname, "cpus_alloc": cpus_alloc}
                serviceList.append(service_dict)
                s_key = keynamehelper.create_key_name("service", Name)
                self.redis.hmset(s_key, service_dict)
                logging.info("In service_to_host_mapping: service_dict = {}".format(service_dict))
        logging.info("-" * 50)
        inspect = api_client.inspect_service(service.id, insert_defaults=True)
        print("\nIn In service_to_host_mapping:\nserviceList: ", *serviceList, sep = "\n")
        return serviceList

    def get_node_info(self):
        client = self.docker_client
        api_client = self.api_client

        logging.info("\nnodes info:")
        nodes_list = client.nodes.list()
        nodeList = []
        for node in nodes_list:
            node_id = node.id
            node = client.nodes.get(node_id)
            node_attrs = node.attrs
            ID = list(pn.find('ID', node_attrs))[0]
            Hostname = list(pn.find('Hostname', node_attrs))[0]
            CPUs = int( list(pn.find('NanoCPUs', node_attrs))[0] ) / 1000000000
            MemoryMB = int( list(pn.find('MemoryBytes', node_attrs))[0] ) / 1000000
            State = list(pn.find('State', node_attrs))[0]
            Addr = list(pn.find('Addr', node_attrs))[0]
            node_dict = {"ID": ID, "HostName": Hostname, "CPUs": CPUs, "MemoryMB": MemoryMB, "State": State, "Addr": Addr}
            nodeList.append(node_dict)
            n_key = keynamehelper.create_key_name("Node", Hostname)
            self.redis.hmset(n_key, node_dict)
            logging.info("In get_node_info: node_dict = {}".format(node_dict))
        logging.info("-" * 50)
        print("\nIn get_node_info:\nnodeList: ", *nodeList, sep = "\n")
        return nodeList

    def create_service(self, user_id, constraints, hostname, serv_labels, serv_name, mounts, idx, cpusLen, host_str):
        """create new service with Healthcheck, host, and other info"""
        # docker api
        client = self.docker_client
        api_client = self.api_client
        image = self.image
        networks = self.networks

        Healthcheck = docker.types.Healthcheck(test = ["CMD-SHELL", 'echo Hello'],
                                               interval = 1000000 * 500,
                                               timeout = 1000000 * 6000,
                                               retries = 5,
                                               start_period = 1000000 * 6000)
        restart = docker.types.RestartPolicy(condition='on-failure')
        if (idx < cpusLen):
            service = client.services.create(image = image,
                                         command = ['sh', '-c', 'sudo /usr/sbin/sshd -D'],
                                         constraints = constraints,
                                         hostname = hostname,
                                         labels = serv_labels,
                                         name = serv_name,
                                         mounts = mounts,
                                         networks = networks,
                                         # user = user_id,
                                         healthcheck = Healthcheck,
                                         restart_policy=restart)
        else:
            args = host_str
            service = client.services.create(image = image,
                                         # command = ['sh', '-c', 'sudo /usr/sbin/sshd -D'],
                                         command = ['/nwm/run_model.sh'],
                                         args = args,
                                         constraints = constraints,
                                         hostname = hostname,
                                         labels = serv_labels,
                                         name = serv_name,
                                         mounts = mounts,
                                         networks = networks,
                                         # user = user_id,
                                         healthcheck = Healthcheck,
                                         restart_policy=restart)

        inspect = api_client.inspect_service(service.id, insert_defaults=True)
        logging.info("Output from inspect_service in create_service():")
        # pp(inspect)
        logging.info("CreatedAt = {}".format(list(pn.find('CreatedAt', inspect))[0]))
        Labels = list(pn.find('Labels', inspect))[0]
        Labels = Labels['com.docker.stack.image']
        (_, Labels) = Labels.split('/')
        (_, HostNode) = ((list(pn.find('Constraints', inspect))[0])[0]).split('==')
        logging.info("HostNode = {}".format(HostNode))
        logging.info("\n")
        # test out some service functions
        serv_list = client.services.list(filters={'name':'nwm_mpi-worker_tmp'})[0]
        service_id = serv_list.id
        logging.info("service_id: {}".format(service_id))
        service_name = serv_list.name
        logging.info("service_name: {}".format(service_name))
        service_attrs = serv_list.attrs
        # pp(service_attrs)
        logging.info("\n")
        return service

    def update_service(self, service, user_id, constraints, hostname, serv_labels, serv_name, mounts):
        """dynamically change a service based on needs"""
        """create new service with Healthcheck, host, and other info"""
        image = self.image
        networks = self.networks

        # docker api
        client = self.docker_client
        api_client = self.api_client

        service.update(image=image,
                        constraints = constraints,
                        hostname = hostname,
                        labels = serv_labels,
                        name = serv_name,
                        mounts = mounts,
                        networks = networks)#,
                        #user = user_id)
        # test out some service functions
        serv_list_tmp = client.services.list(filters={'name':'nwm_mpi-worker_tmp'})
        print("\nservice list:")
        print(serv_list_tmp)
        serv_list = client.services.list(filters={'name':'nwm_mpi-worker_tmp'})[0]
        print("\nservice list")
        print(serv_list)
        print("\nafter updating:")
        service_id = serv_list.id
        print ('service_id: ', service_id)
        service_name = serv_list.name
        print ('service_name: ', service_name)
        service_attrs = serv_list.attrs
        print ("service_attrs:")
        # pp(service_attrs)
        service = client.services.get(service_id, insert_defaults=True)
        task = service.tasks(filters={'name':'nwm_mpi-worker_tmp'})
        print("\ntask:")
        # pp(task)

    def checkDocker(self):
        """Test that docker is up running"""
        try:
            # Check docker client state
            docker.from_env().ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    @classmethod
    def fromRequest(cls, request: SchedulerRequestMessage, idx: int):
        """Perform job queuing based on Request() class object"""
        # user_id = "shengting.cui"
        # cpus = 125
        # mem = 5000000000
        # resources = []
        # image = ""
        # constraints = []
        # hostname = ""
        # serv_labels = {}
        # serv_name = ""
        # scheduler = cls(user_id, cpus, mem, resources, image, constraints,
        #                 hostname, serv_labels, serv_name)
        # if (idx == 0):
        scheduler = cls()
        scheduler.enqueue(request)
        return scheduler

    def runJob(self, request, constraints, hostname, serv_labels, serv_name, cpus_alloc, mounts, idx, cpusLen, host_str):
        """Call create_service to run a job based on request"""
        user_id = request.user_id
        image = self.image
        networks = self.networks
        service = self.create_service(user_id, constraints, hostname, serv_labels, serv_name, mounts, idx, cpusLen, host_str)
        return service

    def enqueue(self, request):
        '''
        Add job request to queue
        '''
        self.__class__._jobQ.append(request)
        # self._jobQ.append(request)

    def build_host_list(self, basename, cpusList, req_id):
        '''
        build a list of strings that contain the container names and the allocated CPUs on the associated hosts
        '''

        idx = 0
        host_str = []
        # basename = 'nwm_mpi-worker_tmp'
        for cpu in cpusList:
            cpus_alloc = str(cpu['cpus_alloc'])
            #FIXME get nameing better orgainized across all functions
            name = basename + str(idx)+"_{}".format(req_id)
            host_tmp = name+':'+cpus_alloc
            host_str.append(str(host_tmp))
            idx += 1
        return host_str

    def write_hostfile(self, basename, cpusList):
        '''
        Write allocated hosts and CPUs to hostfile on the scheduler container
        This can be modified to write to a text file for an additional copy of
        the user job info
        '''

        idx = 0
        host_str = ""
        # basename = "nwm_mpi-worker_tmp"
        for cpu in cpusList:
            cpus_alloc = str(cpu['cpus_alloc'])
            name = basename + str(idx)
            host_str += name+':'+cpus_alloc+'\n'
            idx += 1

        client = self.docker_client
        service_list = client.services.list()
        for service in service_list:
            service_id = service.id
            serv_list = client.services.list(filters={'id': service_id})[0]
            service_attrs = serv_list.attrs
            Name = list(pn.find('Name', service_attrs))[0]
            # if 'nwm_mpi-worker_tmp0' in Name:
            if 'nwm-_scheduler' in Name:
                with open('hostfile', 'w') as hostfile:
                    hostfile.write(host_str)


    def write_to_hostfile(self):
        """write hostname and cpu allocation to hostfile"""
        # docker api
        client = self.docker_client

        # docker service ls
        host_str = ""
        service_list = client.services.list()
        for service in service_list:
            service_id = service.id
            serv_list = client.services.list(filters={'id': service_id})[0]
            service_attrs = serv_list.attrs
            Name = list(pn.find('Name', service_attrs))[0]
            if 'nwm_mpi-worker_' in Name:
                Labels = list(pn.find('Labels', service_attrs))[0]
                Hostname = Labels['Hostname']
                hostname = Hostname.split('.')[0]
                cpus_alloc = Labels['cpus_alloc']
                host_str += Name+':'+cpus_alloc+'\n'

        for service in service_list:
            service_id = service.id
            serv_list = client.services.list(filters={'id': service_id})[0]
            service_attrs = serv_list.attrs
            Name = list(pn.find('Name', service_attrs))[0]
            # if 'nwm_mpi-worker_tmp0' in Name:
            if 'nwm_mpi-worker_' in Name:
                with open('hostfile', 'w') as hostfile:
                    hostfile.write(host_str)

    def retrieve_job_metadata(self, user_id):
        """
        Retrieve queued job info from the database using user_id as a key to the req_id list
        Using req_id to uniquely retrieve the job request dictionary: cpus_dict
        Build nested cpusList from cpus_dict
        The code only retrieve one job that make up cpusList. Complete job list is handled in check_jobQ
        For comprehensive info on all jobs by a user in the database, a loop can be used to call this method
        """

        redis = self.redis
        cpusList = []
        user_key = keynamehelper.create_key_name(user_id)

        # case for index = 0, the first popped index is necessarily 0
        # lpop and rpush are used to guaranttee that the earlist queued job gets to run first
        req_id = redis.lpop(user_key)
        if (req_id != None):
            print("In retrieve_job_metadata: user_key", user_key, "req_id = ", req_id)
            req_key = keynamehelper.create_key_name("job_request", req_id)
            cpus_dict = redis.hgetall(req_key)
            cpusList.append(cpus_dict)
            index = cpus_dict['index']             # index = 0
            if (int(index) != 0):
                raise Exception("Metadata access error, index = ", index, " req_id = ", req_id)

        '''
        # case for index = 0 or 1, job belongs to a different request if index = 0
        req_id = redis.lpop(user_key)
        if (req_id != None):
            print("In retrieve_job_metadata: user_key", user_key, "req_id = ", req_id)
            req_key = keynamehelper.create_key_name("job_request", req_id)
            cpus_dict = redis.hgetall(req_key)
            index = cpus_dict['index']             # index = 0 or 1
            if (str(index) == '0'):
                redis.lpush(user_key, req_id)      # return the popped value, the job request belongs to a different request if index = 0
            else:
                cpusList.append(cpus_dict)
        '''

        # cases for the rest of index != 0, job belongs to a different request if index = 0
        while (req_id != None):                    # previous req_id
            req_id = redis.lpop(user_key)          # new req_id
            if (req_id != None):
                req_key = keynamehelper.create_key_name("job_request", req_id)
                cpus_dict = redis.hgetall(req_key)
                index = cpus_dict['index']         # new index
                if (int(index) == 0):
                    redis.lpush(user_key, req_id)  # return the popped value, the job request belongs to a different request if index = 0
                    break
                else:
                    cpusList.append(cpus_dict)
                print("In retrieve_job_metadata: user_key", user_key, "req_id = ", req_id)
        print("\nIn retrieve_job_metadata: cpusList:\n", *cpusList, sep = "\n")
        print("\nIn retrieve_job_metadata:")
        print("\n")
        return cpusList


    def startJobs(self, user_id, cpus, mem, constraints, hostname, serv_labels, serv_name, cpus_alloc, mounts, idx, cpusLen, host_str):
        """
        Using the set max jobs and max cpus spawn docker containers
        until the queue has been exhausted.
        """
        client = self.docker_client
        # Check if number of running jobs is greater than allowed
        if len(client.services.list()) > self._MAX_JOBS:
            raise Exception('System already has too many running containers. '
                            'Either kill containers or adjust the max_jobs '
                            'attribute.')
        # que = self._jobQ
        # for q in que:
            # print("In startJobs, _jobQ: user_id, cpus, mem: {} {} {}".format(q.user_id, q.cpus, q.mem))
        print("Starting Job Outside Q Loop")
        while len(self._jobQ) != 0:
        # if len(self._jobQ) != 0:
            # if len(self.check_availability_and_schedule()) != 0:
            req = self._jobQ.popleft()
            print("startJobs inside Q loopo, calling runJob")
            service = self.runJob(req, constraints, hostname, serv_labels, serv_name, cpus_alloc, mounts, idx, cpusLen, host_str)

    def check_jobQ(self):
        """ Check jobs in the waiting queue """
        print("In check_jobQ, length of jobQ:", len(self._jobQ))
        que = self._jobQ
        # print("In check_jobQ, que = ", que)
        for job in que:
            print("In check_jobQ: user_id, cpus, mem: {} {} {}".format(job.user_id, job.cpus, job.mem))

    def check_runningJobs(self):
        """
        Check the running job queue
        Running job snapshot is needed for restart
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client

        # test out some service functions
        service_list = client.services.list()
        runningJobList = []
        for service in service_list:
            # iterate through entire service list
            service_id = service.id
            # print("In check_runningJobs: service_id = {}".format(service_id))
            # serv_list = client.services.list(filters={'id': service_id})[0]
            # service_attrs = serv_list.attrs
            service_attrs = service.attrs
            flat_dict = pn.flatten(service_attrs)
            Name = list(pn.find('Name', service_attrs))[0]
            # print("In check_runningJobs: Name = {}".format(Name))
            # service_id = serv_list.id
            # print("In check_runningJobs: service_id = {}".format(service_id))
            # service_name = serv_list.name
            service_name = service.name
            # print("In check_runningJobs: service_name = {}".format(service_name))
            # service_attrs = serv_list.attrs
            # flat_dict = pn.flatten(service_attrs)
            # Name = list(pn.find('Name', service_attrs))[0]
            # Name should be in the form: nwm_mpi-worker_user-id_job-id
            # Select only the service with "nwm-mpi-worker_" in the service name
            if 'nwm_mpi-worker_tmp' in Name:
                Labels = list(pn.find('Labels', service_attrs))[0]
                NameSpace = Labels['com.docker.stack.namespace']
                Hostname = Labels['Hostname']
                cpus_alloc = Labels['cpus_alloc']
                print("In check_runningJobs: Hostname = {}".format(Hostname))
                print("In check_runningJobs: cpus_alloc = {}".format(cpus_alloc))
                Labels = Labels['com.docker.stack.image']
                (_, Labels) = Labels.split('/')
                print("In check_runningJobs: Labels = {}".format(Labels))
                (_, HostNode) = ((list(pn.find('Constraints', service_attrs))[0])[0]).split('==')
                print("In check_runningJobs: HostNode = {}".format(HostNode))
                service = client.services.get(service_id, insert_defaults=True)
                service_dict = {"Name": Name, "Labels": Labels, "HostNode": HostNode, "NameSpace": NameSpace, "Hostname": Hostname, "cpus_alloc": cpus_alloc}
                runningJobList.append(service_dict)
                s_key = keynamehelper.create_key_name("service", Name)
                self.redis.hmset(s_key, service_dict)
                print("-" * 30)
                print("\n")
        print("-" * 50)
        logging.info("\n")
        return runningJobList


    def clean_redisKeys(self):
        '''
        """ initialize Redis client """
        # from utils.clean import clean_keys

        global redis
        n = 0
        while (n <= Max_Redis_Init):
            try:
                redis = Redis(host=os.environ.get("REDIS_HOST", "myredis"),
                # redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
                              port=os.environ.get("REDIS_PORT", 6379),
                              db=0, decode_responses=True,
                              password='***REMOVED***')
            except:
                logging.debug("redis connection error")
            time.sleep(1)
            n += 1
            if (redis != None):
                break

        # time.sleep(5)
        '''
        clean_keys(self.redis)
        self.set_prefix()
        self.create_resources()
        # self.redis.flushdb()
        # self.redis.flushall()

    def check_for_incoming_req(self):
        '''
        Place holder for codes checking incoming job request
        '''
        time.sleep(5)
        recvJobReq = 1
        return recvJobReq


    def job_allocation_and_setup(self, user_id, cpus, mem):
        """
        check_availability_and_schedule() returns cpusList which contains CPU allocation on one or multiple nodes
        based on user request
        It also saves the cpusList to the database as well as req_id as a key for finding the job request
        for later use

        check_single_node_availability() find the first node with enough CPUs to accomodate a job request, loading a
        job request to a single node optimize the computation efficiency

        check_generalized_round_robin() distributes a compute job among a set of nodes, even though the job can fit in
        a single node. This is useful in some special cases
        """
        print("Len of Q at star of job_allocation_and_setup: {}".format(len(self._jobQ)))


        idx = 0
        recvJobReq = 1
        # recvJobReq = self.check_for_incoming_req()
        #while (recvJobReq != 0):
        # create and save user info to database
        self.create_user_from_username(user_id)

        # First try schedule the job on a single node. If for some reason, job cannot be allocated on a single node,
        # an empty list is returned, we try the check_generalized_round_robin() method. If this is not successful,
        # we try the more general check_availability_and_schedule() method

        # run_option is set based on request
        # currently this is manually set
        run_option = 1 

        if (run_option == 1):
            cpus = 4
            req_id, cpusList = self.check_single_node_availability(user_id, cpus, mem)

        elif (run_option == 2):
            cpus = 10
            req_id, cpusList = self.check_generalized_round_robin(user_id, cpus, mem)

        else:
            cpus = 140
            req_id, cpusList = self.check_availability_and_schedule(user_id, cpus, mem)

        if (len(cpusList) == 0):
            print("Illegitimate request not scheduled")
            return

        cpusList = self.retrieve_job_metadata(user_id)
        print("\nIn job_allocation_and_setup: cpusList:\n", *cpusList, sep = "\n")
        self.print_resource_details()

        # basename = 'nwm_mpi-worker_tmp'
        basename = self.name
        host_str = self.build_host_list(basename, cpusList, req_id)
        self.write_hostfile(basename, cpusList)

        # # initialize variables for create_service()
        image = self.image
        constraints = self.constraints
        hostname = self.hostname
        labels = self.labels
        name = self.name
        networks = self.networks

        # idx = 0
        cpusLen = len(cpusList)
        for cpu in cpusList:
            constraints = "node.hostname == "
            NodeId = cpu['node_id']
            if (NodeId == "Node-0001"):
                mounts = ['/opt/nwm_c/domains:/nwm/domains:rw']
            else:
                mounts = ['/local:/nwm/domains:rw']
            cpus_alloc = str(cpu['cpus_alloc'])
            Hostname = cpu['Hostname']
            logging.info("Hostname: {}".format(Hostname))
            labels_tmp = {"Hostname": Hostname, "cpus_alloc": cpus_alloc}
            labels.update(labels_tmp)
            constraints += Hostname
            constraints = list(constraints.split("/"))
            serv_name = name + str(idx)+"_{}".format(req_id)
            idx += 1
            print("Len of Q before fromRequest: {}".format(len(self._jobQ)))
            schedule = self.fromRequest(user_id, cpus_alloc, mem, idx)
            print("Len of Q after fromRequest: {}".format(len(self._jobQ)))
            # schedule.check_jobQ()
            print("Allocate and Setup about to startJobs")
            schedule.startJobs(user_id, cpus, mem, constraints, hostname, labels, serv_name, cpus_alloc, mounts, idx, cpusLen, host_str)
            print("Allocate and Setup started job")
        logging.info("\n")
        schedule.check_jobQ()
        jobQ = self._jobQ
        for job in jobQ:
            logging.info("In job_allocation_and_setup: user_id, cpus, mem: {} {} {}".format(job.user_id, job.cpus, job.mem))
        self.service_to_host_mapping()
        runningJobs = self.check_runningJobs()
        recvJobReq -= 1
        #end while
        return req_id

def test_scheduler():
    """
    Test the scheduler using on the fly cpusList 
    or the metadata from the saved database
    """

    # instantiate the scheduler
    scheduler = Scheduler()

    # initialize redis client
    scheduler.clean_redisKeys()

    # build resource database
    scheduler.create_resources()

    ## find host from docker service info
    # scheduler.service_to_host_mapping()

    user_id = "shengting.cui"
    cpus = 10
    mem = 5000000000
    scheduler.job_allocation_and_setup(user_id, cpus, mem)

if __name__ == "__main__":
    keynamehelper.set_prefix("stack0")
    # while True:     # Using this while loop causes a name nwm_mpi-worker_tmp0 exists error when looping through 2nd time
    test_scheduler()  # to run test_scheduler(). The while loop does work as expected.
    # while True:
    #     pass
