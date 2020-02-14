#!/usr/bin/env python3

import sys
import os
from os.path import join, dirname, realpath
import time
import subprocess
import queue
import json, ast
import docker
from pprint import pprint as pp
from redis import Redis, WatchError
import logging

## local imports
# from .scheduler import Scheduler
from ..utils import keynamehelper as keynamehelper
from ..utils import generate as generate
from ..utils import parsing_nested as pn
from ..utils.clean import clean_keys
from ..lib import scheduler_request as sch_req
from ..src.scheduler import DockerSrvParams

MAX_JOBS = 210
Max_Redis_Init = 5
T_INTERVAL = 20

logging.basicConfig(
    filename='que_monitor.log',
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

class QueMonitor():
    _jobQ = queue.deque()
    _jobQList = "redisQList"
    def __init__(self, docker_client: docker.from_env() = None, \
                 api_client: docker.APIClient() = None, \
                 redis: Redis = None):
        """
        Parameters
        ----------
        docker_client
            Docker API client
        api_client
            Docker Low-level API client
        redis
            Redis API
        """
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
                 # self.redis = Redis(host=os.environ.get("REDIS_HOST", "localhost"),
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
        ## initialize variables for create_service()
        ## default image
        self.image = "127.0.0.1:5000/nwm-2.0:latest"
        ## self.image =  "127.0.0.1:5000/nwm-master:latest"

        self.constraints = []
        self.hostname = "{{.Service.Name}}"
        self.labels =  {"com.docker.stack.image": "127.0.0.1:5000/nwm-2.0",
                        "com.docker.stack.namespace": "nwm"
                       }
        self.name = "nwm_mpi-worker_serv"
        self.networks = ["mpi-net"]

        # self._jobQ = queue.deque()
        # _MAX_JOBS is set to currently available total number of CPUs
        self._MAX_JOBS = MAX_JOBS
        #TODO find a clearer way to set this...probably need to to do it on init of the module, and pull from
        #the env the stack the module is running in (or from the docker API???
        # self.keyname_prefix = "nwm-master" #FIXME parameterize
        self.keyname_prefix = "nwm-scheduler" #FIXME parameterize
        # self.keyname_prefix = keyname_prefix
        self.create_resources()
        self.set_prefix()

    def set_prefix(self):
        """
        Set the prefix for a set of Redis key names to start
        """
        keynamehelper.set_prefix(self.keyname_prefix)

    def create_resources(self):
        """ Create resource from the array of passed resource details"""
        e_set_key = keynamehelper.create_key_name("resources")
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            self.redis.hmset(e_key, resource)
            self.redis.sadd(e_set_key, resource['node_id'])

    def checkDocker(self):
        """Test that docker is up running"""
        try:
            # Check docker client state
            docker.from_env().ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    def check_jobQ(self):
        """ Check jobs in the waiting queue """
        print("In que_monitor.check_jobQ, length of jobQ:", len(self._jobQ))
        que = self._jobQ
        # print("In check_jobQ, que = ", que)
        for job in que:
            print("In check_jobQ: user_id, cpus, mem: {} {} {}".format(job.user_id, job.cpus, job.mem))

    def check_runningJobs(self) -> tuple:
        """
        Check the running job queue
        Running job snapshot is needed for restart

        Returns
        -------
        runningJobList
            A list of all current running jobs with key attributes packed into dict format, and a dict
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # test out some service functions
        service_list = client.services.list()
        runningJobList = []
        for service in service_list:
            # iterate through entire service list
            service_id = service.id
            service_attrs = service.attrs
            flat_dict = pn.flatten(service_attrs)
            Name = list(pn.find('Name', service_attrs))[0]
            service_name = service.name
            if srv_basename in Name:
                # pp(service_attrs)
                ## Image = list(pn.find('Image', service_attrs))[0]
                ## print("In check_runningJobs: Image = {}".format(Image))
                Image = pn.find('Image', service_attrs)
                *Image, = Image
                print("In check_runningJobs: Image = ", *Image)
                # Image = pn.find('Image', service_attrs)
                # print("In check_runningJobs: Image = ", *Image)
                # Name = list(pn.find('Name', service_attrs))[0]
                # print("In check_runningJobs: Name = {}".format(Name))
                Name = pn.find('Name', service_attrs)
                *Name, = Name
                print("In check_runningJobs: Name = ", *Name)
                print("In check_runningJobs: service_name = {}".format(service_name))
                Constraints = pn.find('Constraints', service_attrs)
                *Constraints, = Constraints
                print("In check_runningJobs: Constraints = ", *Constraints)
                ContainerSpec = list(pn.find('ContainerSpec', service_attrs))
                pp(ContainerSpec)
                Mounts = pn.find('Mounts', service_attrs)
                *Mounts, = Mounts
                print("In check_runningJobs: Mounts = ", *Mounts)
                Args = pn.find('Args', service_attrs)
                *Args, = Args
                print("In check_runningJobs: Args = ", *Args)
                Command = pn.find('Command', service_attrs)
                *Command, = Command
                print("In check_runningJobs: Command = ", *Command)
                RestartPolicy = pn.find('RestartPolicy', service_attrs)
                *RestartPolicy, = RestartPolicy
                print("In check_runningJobs: RestartPolicy = ", *RestartPolicy)
                Healthcheck = pn.find('Healthcheck', service_attrs)
                *Healthcheck, = Healthcheck
                print("In check_runningJobs: Healthcheck = ", *Healthcheck)
                Labels = pn.find('Labels', service_attrs)
                *Labels, = Labels
                print("In check_runningJobs: Labels = ", *Labels)

                labels = list(pn.find('Labels', service_attrs))[0]
                L_image =  labels['com.docker.stack.image']
                NameSpace = labels['com.docker.stack.namespace']
                HostNode = labels['Hostname']
                cpus_alloc = labels['cpus_alloc']

                service = client.services.get(service_id, insert_defaults=True)
                service_dict = {"Image": Image, "Command": Command, "Args": Args, "Constraints": Constraints, "ContainerSpec": ContainerSpec,
                                "Labels": Labels, "Name": Name, "Mounts": Mounts, "Healthcheck": Healthcheck,
                                "RestartPolicy": RestartPolicy, "HostNode": HostNode, "cpus_alloc": cpus_alloc}
                service_dict_rds = {"Image": Image, "Name": Name, "Constraints": Constraints, "Labels": Labels,
                                    "HostNode": HostNode, "Mounts": Mounts, "cpus_alloc": cpus_alloc}
                runningJobList.append(service_dict)
                # Taking a snapshot of current running jobs and push it on to Redis
                # s_key = keynamehelper.create_key_name("service", service_name)
                # TODO Convert the compound objects in service_dict_rds to byte, string or number before pushing to Redis
                # self.redis.hmset(s_key, service_dict_rds)
        print("\nend of que_monitor.check_runningJobs")
        print("-" * 30)
        return runningJobList, service_dict

    def resubmit(self, service_dict: dict, service_name: str) -> docker.from_env().services.create:
        """
        Resubmit a job that failed to start/run/complete successfully using the service attributes extracted from the initial service

        Parameters
        ----------
        service_dict
            Dictionary containing service attributes of the initial service
        service_name
            Name of the initial service       

        Returns
        -------
        service
            Service object created
        """
        Image = (service_dict['Image'])[0]
        print("service_dict: Image = ", Image)
        print("Image isinstance of str:", isinstance(Image, str))

        Name = (service_dict['Name'])[0]
        print("service_dict: Name = ", Name)
        print("Name isinstance of str:", isinstance(Name, str))

        Constraints = (service_dict['Constraints'])[0]
        print("service_dict: Constraints = ", Constraints)
        print("Constraints isinstance of list:", isinstance(Constraints, list))

        Hostname = ((service_dict['ContainerSpec'])[0])['Hostname']
        print("service_dict: Hostname = ", Hostname)
        print("Hostname isinstance of str:", isinstance(Hostname, str))

        HostNode = service_dict['HostNode']
        print("service_dict: HostNode = ", HostNode)
        print("HostNode isinstance of str:", isinstance(HostNode, str))

        # TODO change type: bind to options: rw
        Mounts = ((service_dict['Mounts'])[0])[0]
        print("service_dict: Mounts = ", Mounts)
        print("Mounts isinstance of dict:", isinstance(Mounts, dict))
        source = Mounts['Source']
        target = Mounts['Target']
        options = 'rw'
        mts_string = source + ':' + target + ':' + options
        mounts = [mts_string]
        print("mounts = ", mounts)

        Args = (service_dict['Args'])[0]
        args = Args
        print("service_dict: Args = ", Args)
        print("Args isinstance of list:", isinstance(Args, list))
        print("service_dict: args = ", args)

        Command = (service_dict['Command'])[0]
        command = Command
        print("service_dict: Command = ", Command)
        print("Command isinstance of list:", isinstance(Command, list))
        print("service_dict: command = ", command)

        Labels = (service_dict['Labels'])[0]
        print("Labels: ")
        pp(Labels)
        print("Labels isinstance of dict:", isinstance(Labels, dict))
        print("Labels: Hostname = ", Labels['Hostname'])

        RestartPolicy = (service_dict['RestartPolicy'])[0]
        # print("service_dict: RestartPolicy = ", RestartPolicy)
        print("RestartPolicy: ")
        pp(RestartPolicy)
        print("RestartPolicy isinstance of dict:", isinstance(RestartPolicy, dict))
        condition = RestartPolicy['Condition']
        print("RestartPolicy: condition = ", condition)
        # restart = docker.types.RestartPolicy(condition = condition)
        # restart = docker.types.RestartPolicy(condition='none')
        restart = RestartPolicy

        Healthcheck = (service_dict['Healthcheck'])[0]
        print("Healthcheck: ")
        pp(Healthcheck)

        networks = ["mpi-net"]

        # time.sleep(90)
        # service_state_list = self.check_job_state()
        # if (jobState == 'complete'):
        service = client.services.create(image = Image,
                                         command = command,
                                         args = args,
                                         constraints = Constraints,
                                         hostname = Hostname,
                                         labels = Labels,
                                         name = Name,
                                         mounts = mounts,
                                         networks = networks,
                                         healthcheck = Healthcheck,
                                         restart_policy = restart)
        return service

    def check_job_state(self) -> list:
        """
        Check the job state of current worker services

        Returns
        -------
        service_state_list
            A list of dict containing taskState and service_name of all current running jobs
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # test out some service functions
        service_list = client.services.list()
        service_state_list = []
        for service in service_list:
            # iterate through entire service list
            service_id = service.id
            service_attrs = service.attrs
            # Name = list(pn.find('Name', service_attrs))[0]
            service_name = service.name
            # print("service_name = ", service.name)
            # if srv_basename in Name:
            if srv_basename in service_name:
                for task in service.tasks():
                    # TODO logging monitor output
                    print('\n\tState: '+task['Status']['State'])
                    print('\tTimestamp: '+task['Status']['Timestamp'])
                    print('\tContainerID: '+task['Status']['ContainerStatus']['ContainerID'])
                    print('\tDesiredState: '+task['DesiredState'])
                    print('\tServiceID: '+task['ServiceID'])
                    task_state = service_name + ':' + task['Status']['State']
                    task_timestamp = service_name + ':' + task['Status']['Timestamp']
                    task_container_id = service_name + ':' + task['Status']['ContainerStatus']['ContainerID']
                    task_disired_state = service_name + ':' + task['DesiredState']
                    task_service_id = service_name + ':' + task['ServiceID']
                    task_error = service_name + ':' + str(task['Status']['ContainerStatus']['ExitCode'])
                    task_error_num = task['Status']['ContainerStatus']['ExitCode']
                    task_host = task['Spec']['Placement']['Constraints']
                    task_host = task_host[0]
                    (_, task_host) = task_host.split(' == ')
                    # task_host = service_name + ':' + task_host
                    print('\n\tserviceName:taskState: ', task_state)
                    (serviceName, taskState) = task_state.split(':')
                    print('\tserviceName: ', serviceName)
                    print('\ttaskState: ', taskState)
                    print('\ttaskExitCode: ', task_error)
                    print('\ttaskExitCode: ', task_error_num)
                    print('\ttask_host: ', task_host)
                    print("flush the buffer", flush=True)
                    # pp(task)
                    if (taskState == 'starting') or (taskState == 'running'):
                        pass
                    elif (taskState == 'complete'):
                        logging.info("Job {} successfully finished".format(serviceName))
                        service.remove()
                        # time.sleep(10)
                    elif (taskState == 'failed'):
                        logging.info("Job {} failed to complete".format(serviceName))
                        logging.info("Please examine the task logs for cause before removing the service")
                        # Check reasons and consider resubmit
                        service.remove()
                        # time.sleep(10)
                    elif (taskState == 'shutdown'):
                        # TODO consider resubmit
                        logging.info("Docker requested {} to shutdown".format(serviceName))
                        service.remove()
                    elif (taskState == 'rejected'):
                        # TODO consider resubmit
                        # TODO check node state and resubmit
                        logging.info("The worker node rejected {}".format(serviceName))
                        service.remove()
                    elif (taskState == 'ophaned'):
                        # TODO consider resubmit
                        # TODO check node state and possibly resubmit to a different node
                        logging.info("The node for {} down for too long".format(serviceName))
                        service.remove()
                    elif (taskState == 'remove'):
                        # TODO consider resubmit
                        # TODO check node state and resubmit
                        logging.info("The node for {} down for too long".format(serviceName))
                        service.remove()
                    else:
                        pass
                    print("In check_job_state: ", taskState)
                    service_state = {"taskState": taskState, "service_name": service_name}
                    service_state_list.append(service_state)
        return service_state_list

    def build_state_list_reqid_set(self, service_state_list: list) -> list:
        """
        Enumerate through all possible jobs in the service list and classfify them into possible
        Docker task state. Create a list for each and push associated request_id into a related set

        Parameters
        ----------

        service_state_list
            A list of task state for all jobs in Docker service

        Returns
        -------
            A nested list of dict containing task state list and associated request_id set
        """
        failed_list = []
        complete_list = []
        rejected_list = []
        orphaned_list = []
        shutdown_list = []
        remove_list = []
        running_list = []
        failed_set = set()
        complete_set = set()
        rejected_set = set()
        orphaned_set = set()
        shutdown_set = set()
        remove_set = set()
        running_set = set()
        for service_state in service_state_list:
            jobState = service_state['taskState']
            service_name = service_state['service_name']
            (_, _, _, req_id) = service_name.split('_')
            print("jobState =", jobState, "service_name =", service_name)
            if (jobState == 'failed'):
                failed_list.append(service_name)
                failed_set.add(req_id)
            elif (jobState == 'complete'):
                complete_list.append(service_name)
                complete_set.add(req_id)
            elif (jobState == 'rejected'):
                rejected_list.append(service_name)
                rejected_set.add(req_id)
            elif (jobState == 'orphaned'):
                orphaned_list.append(service_name)
                orphaned_set.add(req_id)
            elif (jobState == 'shutdown'):
                shutdown_list.append(service_name)
                shutdown_set.add(req_id)
            elif (jobState == 'remove'):
                remove_list.append(service_name)
                remove_set.add(req_id)
            elif (jobState == 'running'):
                running_list.append(service_name)
                running_set.add(req_id)
            else:
                pass
        state_list = [{"failed_list": failed_list, "failed_set": failed_set}, 
                      {"complete_list": complete_list, "complete_set": complete_set},
                      {"rejected_list": rejected_list, "rejected_set": rejected_set},
                      {"orphaned_list": orphaned_list, "orphaned_set": orphaned_set},
                      {"shutdown_list": shutdown_list, "shutdown_set": shutdown_set},
                      {"remove_list": remove_list, "remove_set": remove_set},
                      {"running_list": running_list, "running_set": running_set}]
        return state_list

    def servname_gen(self, state_set: set, state_list: list) -> list:
        """
        Generator function for identifying the service names belong to one single job

        Parameters
        ----------
        state_set
            Set that contains the request_id
        state_list
            List that contains the service task state

        Returns
        -------
        servname_list
            Service name in list format
        """
        while state_set:
            req_id_state = state_set.pop()
            print("\nreq_id_state =", req_id_state)
            servname_list = []
            for service_name in state_list:
                (_, _, serv_name, req_id) = service_name.split('_')
                print("req_id", req_id)
                if (req_id == req_id_state):
                    servname_list.append(service_name)
                    # print("serv_name =", serv_name)
                    lens = len(serv_name)
                    # print("lens =", lens)
                    index = serv_name[4:lens]
                    # print("index = {}".format(index))
                    # print("servname_list:", servname_list)
            yield servname_list

    def service_actions(self, runningJobList, state_list):
        for jobState in state_list:
            # task state failed
            # FIXME this is only used in test run
            failed_list = jobState['failed_list']
            failed_set = jobState['failed_set']
            if len(failed_list) > 0:
                for servname in self.servname_gen(failed_set, failed_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            #TODO add number of retries for resubmit?
                            service = self.resubmit(service_dict, service_name)
            # task state complete
            # FIXME this is only used in test run
            """
            complete_list = jobState['complete_list']
            complete_set = jobState['complete_set']
            if len(complete_list) > 0:
                for servname in self.servname_gen(complete_set, complete_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            service = self.resubmit(service_dict, service_name)
            """
            # task state rejected
            rejected_list = jobState['rejected_list']
            rejected_set = jobState['rejected_set']
            if len(rejected_list) > 0:
                for servname in self.servname_gen(rejected_set, rejected_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            service = self.resubmit(service_dict, service_name)
            # task state orphaned
            orphaned_list = jobState['orphaned_list']
            orphaned_set = jobState['orphaned_set']
            if len(orphaned_list) > 0:
                for servname in self.servname_gen(orphaned_set, orphaned_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            service = self.resubmit(service_dict, service_name)
            # task state shutdown
            shutdown_list = jobState['shutdown_list']
            shutdown_set = jobState['shutdown_set']
            if len(shutdown_list) > 0:
                for servname in self.servname_gen(shutdown_set, shutdown_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            service = self.resubmit(service_dict, service_name)
            # task state remove
            remove_list = jobState['remove_list']
            remove_set = jobState['remove_set']
            if len(remove_list) > 0:
                for servname in self.servname_gen(remove_set, remove_list):
                    service_name = servname[0]
                    for job in runningJobList:
                        Name = job['Name']
                        if Name == service_name:
                            service_dict = job
                            service = self.resubmit(service_dict, service_name)

    def get_node_info(self) -> docker.from_env().nodes.list:
        """
        Obtain service node info using Docker API

        Returns
        -------
        nodeList
            List of all node in the Docker Swarm
        """
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

    #FIXME Keep in place for the moment
    #FIXME Some form of variation of this function may be needed for communication with scheduler
    def retrieve_job_metadata(self, user_id: str) -> list:
        """
        Retrieve queued job info from the database using user_id as a key to the req_id list
        Using req_id to uniquely retrieve the job request dictionary: cpus_dict
        Build nested cpusList from cpus_dict
        The code only retrieve one job that make up cpusList. Complete job list is handled in check_jobQ
        For comprehensive info on all jobs by a user in the database, a loop can be used to call this method

        Parameter
        ---------
        user_id
            User Identification

        Returns
        -------
        cpusList
            List of allocated CPUs on each node
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
                print("In retrieve_job_metadata, user_key: ", user_key, "req_id = ", req_id)
        print("In retrieve_job_metadata: cpusList:", *cpusList, sep = "\n")
        print("End of retrieve_job_metadata")
        return cpusList, user_key

    #TODO A better function may be implemented for checking current available rerources
    def print_resource_details(self):
        """Print the details of remaining resources after allocating the request """
        logging.info("Resources remaining:")
        for resource in resources:
            e_key = keynamehelper.create_key_name("resource", resource['node_id'])
            logging.info("hgetall(e_key): {}".format(self.redis.hgetall(e_key)))
        logging.info("-" * 20)
        logging.info("\n")

if __name__ == "__main__":
    keynamehelper.set_prefix("nwm-monitor")
    q = QueMonitor()
    client = q.docker_client
    api_client = q.api_client

    time.sleep(5)
    #FIXME check_job_state() should not be called before check_runningJobs() in operational run to save service info
    # before beibg removed from service list
    # service_state_list = q.check_job_state()
    print("flush the buffer", flush=True)
    print("-" * 16, flush=True)

    q.check_jobQ()

    #FIXME check_runningJobs() should be callled before each check_job_state() to save service info
    (runningJobList, service_dict) = q.check_runningJobs()
    # print("runningJobList: ", *runningJobList)
    print("runningJobList:")
    pp(runningJobList)
    for job in runningJobList:
        print("Job name =", job['Name'])
    print("-" * 30, "\n")

    time.sleep(90)
    service_state_list = q.check_job_state()

    state_list = q.build_state_list_reqid_set(service_state_list)
    q.service_actions(runningJobList, state_list)

    # if (jobState == 'complete') or (jobState == 'failed'):
    #     for service_name in service_list:
    #         service = q.resubmit(runningJobList, service_dict, service_name)

    nodeList = q.get_node_info()

    # (cpusList, user_key) = q.retrieve_job_metadata("shengting.cui")

    #TODO create a function that returns the current availble resources using Redis
    q.print_resource_details()

    print("end of que_monitor")
