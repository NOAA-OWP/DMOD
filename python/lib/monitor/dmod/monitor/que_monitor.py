#!/usr/bin/env python3
import logging

from dmod.redis import RedisBacked, KeyNameHelper
import dmod.scheduler.utils.parsing_nested as pn

from typing import Optional
#FIXME clean up imports
import sys
import os
from os.path import join, dirname, realpath
import time
import subprocess
import queue
import json, ast
import docker
from pprint import pprint as pp
#FIXME URGENT refactor all resource management usning redisManager
from redis import Redis, WatchError
import logging

## local imports
# from .scheduler import Scheduler
#from ..utils import self.keynamehelper as self.keynamehelper
#from ..utils import generate as generate
#from ..utils import parsing_nested as pn
#from ..utils.clean import clean_keys
#from ..lib import scheduler_request as sch_req
#from ..src.scheduler import DockerSrvParams

MAX_JOBS = 210
Max_Redis_Init = 5
T_INTERVAL = 20
Ncall_Max = 5

logging.basicConfig(
    filename='que_monitor.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")

class QueMonitor(RedisBacked):
    _jobQ = queue.deque()
    _jobQList = "redisQList"
    def __init__(self, resource_pool: str,
                 docker_client: docker.from_env() = None, api_client: docker.APIClient() = None,
                 redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
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
        super().__init__(resource_pool=resource_pool, redis_host=redis_host,
                         redis_port=redis_port, redis_pass=redis_pass, **kwargs)
        if docker_client:
            self.docker_client = docker_client
            self.api_client = api_client
        else:
            self.checkDocker()
            self.docker_client = docker.from_env()
            self.api_client = docker.APIClient()

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
        self.keyname_prefix = "nwm-monitor" #FIXME parameterize
        self.keynamehelper = KeyNameHelper(self.keyname_prefix, ':')
        #FIXME if resource is needed must load externally (file, redis, resourceManager)
        #self.create_resources()

    def checkDocker(self):
        """Test that docker is up running"""
        try:
            # Check docker client state
            docker.from_env().ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    #FIXME share queue with scheduler via redis
    def check_jobQ(self):
        """ Check jobs in the waiting queue """
        print("In que_monitor.check_jobQ, length of jobQ:", len(self._jobQ))
        que = self._jobQ
        # print("In check_jobQ, que = ", que)
        for job in que:
            print("In check_jobQ: user_id, cpus, mem: {} {} {}".format(job.user_id, job.cpus, job.mem))

    def check_runningJobs(self, ncall: int) -> tuple:
        """
        Check the running job queue
        Running job snapshot is needed for restart

        Parameters
        ----------
        ncall
            Number of times check_runningJobs() function is called

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

        # Initialize runningJobList the first time it is called
        #FIXME Remove an element from the set after appropriate action is performed on the job
        if (ncall == 0):
            runningJobList = []
        service_dict = {} #NJF  bugfix when no services runtime error
        for service in service_list:
            # iterate through entire service list
            service_id = service.id
            service_attrs = service.attrs
            flat_dict = pn.flatten(service_attrs)
            Name = list(pn.find('Name', service_attrs))[0]
            service_name = service.name
            if srv_basename in Name:
                print("\nIn check_runningJobs(): service_name = {}".format(service_name))
                (_, _, serv_name, req_id) = service_name.split('_')
                lens = len(serv_name)
                # FIXME the following line applies to case where nwm_mpi-worker_serv" is used as basename
                index = serv_name[4:lens]
                print("lens =", lens)
                print("index = {}".format(index))
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

                # Args need match with the scheduler.py code for every service created
                Args = pn.find('Args', service_attrs)
                *Args, = Args

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
                # need to be string type to store in Redis hash
                Image_redis = Image[0]
                Name_redis = Name[0]
                service_dict_redis = {"Image": Image_redis, "Name": Name_redis, "HostNode": HostNode, "cpus_alloc": cpus_alloc}
                runningJobList.append(service_dict)
                # Taking a snapshot of current running jobs and push it on to Redis
                s_key = self.keynamehelper.create_key_name("service", service_name)
                # TODO Convert the compound objects in service_dict_redis to byte, string or number before pushing to Redis
                self.redis.hmset(s_key, service_dict_redis)
                print("-" * 10)
        print("\nend of que_monitor.check_runningJobs")
        print("=" * 30)
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
        print("\n----In resubmit()-----")
        print("\nIn resubmit(): service_name = {}".format(service_name))
        (_, _, serv_name, req_id) = service_name.split('_')
        lens = len(serv_name)
        index = serv_name[4:lens]
        print("lens =", lens)
        print("index = {}".format(index))

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

        # Args need match with the scheduler.py code for every service created
        Args = (service_dict['Args'])[0]
        args = Args

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
        print("In function check_job_state():")
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
                    if (taskState == 'starting'):
                        pass
                    elif (taskState == 'running'):
                        #FIXME This option is for testing the codes involved in resubmitting
                        logging.info("Job {} is running: restart to test code".format(serviceName))
                        service.remove()
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
                    print("In check_job_state: service_state_list =")
                    pp(service_state_list)
                    print("-" * 15)
        print("=" * 30)
        return service_state_list

    def build_state_list_reqid_set(self, service_state_list: list) -> dict:
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
        print("\nIn build_state_list_reqid_set: service_state_list =")
        pp(service_state_list)
        print("\n")

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
        state_dict = {"failed_list": failed_list, "failed_set": failed_set,
                      "complete_list": complete_list, "complete_set": complete_set,
                      "rejected_list": rejected_list, "rejected_set": rejected_set,
                      "orphaned_list": orphaned_list, "orphaned_set": orphaned_set,
                      "shutdown_list": shutdown_list, "shutdown_set": shutdown_set,
                      "remove_list": remove_list, "remove_set": remove_set,
                      "running_list": running_list, "running_set": running_set}
        print("\nIn build_state_list_reqid_set: state_dict =")
        pp(state_dict)
        print("=" * 30)
        return state_dict

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
            print("\n\nIn servname_gen: req_id_state =", req_id_state)
            print("=" * 45)
            for service_name in state_list:
                (_, _, _, req_id) = service_name.split('_')
                print("-" * 20)
                print("In servname_gen: req_id =", req_id)
                if (req_id == req_id_state):
                    print("In servname_gen: service_name = {}".format(service_name))
                    print("=" * 20)
                    yield service_name

    def service_actions(self, runningJobList, state_dict):
        print("\n-----In service_actions-----")
        # print("\nIn service_actions: service_state_list =")
        # pp(state_dict)
        for jobState in state_dict:
            # task state failed
            # FIXME this is only used in test run
            if (jobState == "failed_list"):
                failed_list = state_dict[jobState]
                print("In service_actions: failed_list =", failed_list)
                failed_set = state_dict['failed_set']
                print("In service_actions: failed_set =", failed_set)
                print("In service_actions: flush the buffer", flush=True)
                if len(failed_list) > 0:
                    for servname in self.servname_gen(failed_set, failed_list):
                        service_name = servname
                        print("In service_actions: service_name = ", service_name)
                        for job in runningJobList:
                            Name = job['Name'][0]
                            print("In service_actions: Name = {}, servname = {}".format(Name, servname))
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                # avoid calling servname_gen() function simultaneously from different jobState
                                time.sleep(1)
                                print("In service_actions: service = ", service)
                print("-" * 39)

            # task state complete
            # FIXME this is only used in test run
            if (jobState == "complete_list"):
                complete_list = state_dict[jobState]
                print("In service_actions: complete_list =", complete_list)
                complete_set = state_dict['complete_set']
                print("In service_actions: complete_set =", complete_set)
                if len(complete_list) > 0:
                    for servname in self.servname_gen(complete_set, complete_list):
                        service_name = servname
                        print("In service_actions: service_name from servname_gen() = ", service_name)
                        for job in runningJobList:
                            Name = job['Name'][0]
                            print("In service_actions: Name = {}, service_name = {}".format(Name, servname))
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                # avoid calling servname_gen() function simultaneously from different jobState
                                time.sleep(1)
                                print("In service_actions: service = ", service)
                print("-" * 39)

            # task state running
            # FIXME this is only used in test run
            if (jobState == "running_list"):
                running_list = state_dict[jobState]
                # print("In service_actions: running_list =", running_list)
                running_set = state_dict['running_set']
                # print("In service_actions: running_set =", running_set)
                if len(running_list) > 0:
                    for servname in self.servname_gen(running_set, running_list):
                        print("In service_actions: servname = ", servname)
                        service_name = servname
                        print("In service_actions: service_name = ", service_name)
                        print("In service_actions: len = ", len(runningJobList))
                        for job in runningJobList:
                            Name = job['Name'][0]
                            print("In service_actions: Name = ", Name)
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                print("In service_actions: service = {}\n".format(service))

            # task state rejected
            if (jobState == "rejected_list"):
                rejected_list = state_dict[jobState]
                rejected_set = state_dict['rejected_set']
                if len(rejected_list) > 0:
                    for servname in self.servname_gen(rejected_set, rejected_list):
                        service_name = servname
                        for job in runningJobList:
                            Name = job['Name'][0]
                            if Name == service_name:
                                service_dict = job
                                service = self.resubmit(service_dict, service_name)

            # task state orphaned
            if (jobState == "orphaned_list"):
                orphaned_list = state_dict[jobState]
                orphaned_set = state_dict['orphaned_set']
                if len(orphaned_list) > 0:
                    for servname in self.servname_gen(orphaned_set, orphaned_list):
                        service_name = servname
                        for job in runningJobList:
                            Name = job['Name'][0]
                            if Name == service_name:
                                service_dict = job
                                service = self.resubmit(service_dict, service_name)

            # task state shutdown
            if (jobState == "shutdown_list"):
                shutdown_list = state_dict[jobState]
                shutdown_set = state_dict['shutdown_set']
                if len(shutdown_list) > 0:
                    for servname in self.servname_gen(shutdown_set, shutdown_list):
                        service_name = servname
                        for job in runningJobList:
                            Name = job['Name'][0]
                            if Name == service_name:
                                service_dict = job
                                service = self.resubmit(service_dict, service_name)

            # task state remove
            if (jobState == "remove_list"):
                remove_list = state_dict[jobState]
                remove_set = state_dict['remove_set']
                if len(remove_list) > 0:
                    for servname in self.servname_gen(remove_set, remove_list):
                        service_name = servname
                        for job in runningJobList:
                            Name = job['Name'][0]
                            if Name == service_name:
                                service_dict = job
                                service = self.resubmit(service_dict, service_name)

    #Since we are using a partitioning scheme with "resource_pool", should limit
    #this function to only care about the pool a given instance of monitor is
    #monitoring.
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
            n_key = self.keynamehelper.create_key_name("Node", Hostname)
            self.redis.hmset(n_key, node_dict)
            logging.info("In get_node_info: node_dict = {}".format(node_dict))
        logging.info("-" * 50)
        print("\nIn get_node_info:\nnodeList: ", *nodeList, sep = "\n")
        return nodeList

    #TODO A better function may be implemented for checking current available rerources
    #TODO REMOVE/LINK TO RESOURCE MANAGER
    def print_resource_details(self):
        """Print the details of remaining resources after allocating the request """
        print("Resources remaining:")
        #FIXME this is BROKEN. If resource definitions are needed, they must be externally linked.
        #I.e. read a resource file or read from redis or use resource manager
        for resource in resources:
            e_key = self.keynamehelper.create_key_name("resource", resource['node_id'])
            print("hgetall(e_key): {}".format(self.redis.hgetall(e_key)))
        print("-" * 20)
        print("\n")

    def store_running_jobs_attr_in_redis(self):
        """
        Store all jobs in running job queue to redis for the purpose restart in case of system down,
        network outage, or other unexpected system failure
        The operations involve iterating through the running job queue and push job related attributes to
        the redis database and/or a plain textfile for increased assurance

        Parameters
        ----------
        No input parameters

        Returns
        -------
        None
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # Create a list of all services in the running queue
        service_list = client.services.list()

        # service_list_key = self.keynamehelper.create_key_name("service_list")
        service_set_key = self.keynamehelper.create_key_name("service_set")

        # iterate through the service list
        for service in service_list:
            # service_id = service.id
            # serialize the service.attrs and store in redis
            service_attrs = service.attrs
            service_name = service.name
            if srv_basename in service_name:
                # store service_attrs in redis as string
                stringified_service_attrs = json.dumps(service_attrs)  # convert dict object to string
                service_attrs_hash_key = self.keynamehelper.create_key_name("service_attrs", service_name)
                self.redis.hmset(service_attrs_hash_key, stringified_service_attrs)
                self.redis.sadd(service_set_key, service_name)


    def retrieve_running_jobs_attr_from_redis(self) -> list:
        """
        Retrive services.attrs for all jobs in running job queue from redis,
        then use the services.attrs to build up the runningJobList

        Parameters
        ----------
            No input parameters

        Returns
        -------
        runningJobList
            A list of all running jobs last saved into redis
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # Initialize runningJobList the first time it is called
        runningJobList = list()

        # retrieve first element of the service set from redis
        service_set_key = self.keynamehelper.create_key_name("service_set")
        service_name = self.redis.spop(service_set_key)
        # iterate through the saved service set
        while service_name != None:
            service_attrs_hash_key = self.keynamehelper.create_key_name("service_attrs", service_name)
            stringified_service_attrs = self.redis.hgetall(service_attrs_hash_key)
            service_attrs = json.loads(stringified_service_attrs)  # convert string data to object(dict/JSON)

            #FIXME: remove all the print functions after testing
            # extract individual attribute to be used for creating service
            Image = pn.find('Image', service_attrs)
            *Image, = Image
            print("In retrieve_running_jobs_from_redis: Image = ", *Image)
            # Name = list(pn.find('Name', service_attrs))[0]
            # print("In retrieve_running_jobs_from_redis: Name = {}".format(Name))
            Name = pn.find('Name', service_attrs)
            *Name, = Name
            print("In retrieve_running_jobs_from_redis: Name = ", *Name)
            Constraints = pn.find('Constraints', service_attrs)
            *Constraints, = Constraints
            print("In retrieve_running_jobs_from_redis: Constraints = ", *Constraints)
            ContainerSpec = list(pn.find('ContainerSpec', service_attrs))
            pp(ContainerSpec)
            Mounts = pn.find('Mounts', service_attrs)
            *Mounts, = Mounts
            print("In retrieve_running_jobs_from_redis: Mounts = ", *Mounts)
            Args = pn.find('Args', service_attrs)
            *Args, = Args
            print("In retrieve_running_jobs_from_redis: Args = ", *Args)
            Command = pn.find('Command', service_attrs)
            *Command, = Command
            print("In retrieve_running_jobs_from_redis: Command = ", *Command)
            RestartPolicy = pn.find('RestartPolicy', service_attrs)
            *RestartPolicy, = RestartPolicy
            print("In retrieve_running_jobs_from_redis: RestartPolicy = ", *RestartPolicy)
            Healthcheck = pn.find('Healthcheck', service_attrs)
            *Healthcheck, = Healthcheck
            print("In retrieve_running_jobs_from_redis: Healthcheck = ", *Healthcheck)
            Labels = pn.find('Labels', service_attrs)
            *Labels, = Labels
            print("In retrieve_running_jobs_from_redis: Labels = ", *Labels)
            labels = list(pn.find('Labels', service_attrs))[0]
            HostNode = labels['Hostname']
            cpus_alloc = labels['cpus_alloc']

            service_dict = {"Image": Image, "Command": Command, "Args": Args, "Constraints": Constraints, "ContainerSpec": ContainerSpec,
                            "Labels": Labels, "Name": Name, "Mounts": Mounts, "Healthcheck": Healthcheck,
                            "RestartPolicy": RestartPolicy, "HostNode": HostNode, "cpus_alloc": cpus_alloc}
            runningJobList.append(service_dict)

            # retrieve service_name for next iteration
            service_name = self.redis.spop(service_set_key)

        print("\nend of que_monitor.retrieve_running_jobs_from_redis")
        print("=" * 30)
        return runningJobList


    def store_running_jobs_attr_items_in_redis(self):
        """
        Saving all jobs in running job queue for the purpose restart in case of system down, 
        network outage, or other unexpected system failure
        The operations involve iterating through the running job queue and push job related attributes to
        the redis database and/or a plain textfile for increased assurance

        Parameters
        ----------
        No input parameters

        Returns
        -------
        None
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # Create a list of all services in the running queue
        service_list = client.services.list()

        running_services_key = self.keynamehelper.create_key_name("running_service_list")
        s_set_key = self.keynamehelper.create_key_name("running_service_set")

        # iterate through the service list
        for service in service_list:
            # service_id = service.id
            # potentially, could serialize the service.attrs, store in redis, retrieve and extract individual attr
            service_attrs = service.attrs
            service_name = service.name
            Name = list(pn.find('Name', service_attrs))[0]
            if srv_basename in Name:
                # pp(service_attrs)
                ## Image = list(pn.find('Image', service_attrs))[0]
                ## print("In check_runningJobs: Image = {}".format(Image))
                # FIXME: remove all print() after testing
                Image = pn.find('Image', service_attrs)
                *Image, = Image
                print("In check_runningJobs: Image = ", *Image)
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
                # Healthcheck = pn.find('Healthcheck', service_attrs)
                # *Healthcheck, = Healthcheck
                Healthcheck = list(pn.find('Healthcheck', service_attrs))[0]

                print("In check_runningJobs: Healthcheck = ", *Healthcheck)
                Labels = pn.find('Labels', service_attrs)
                *Labels, = Labels
                print("In check_runningJobs: Labels = ", *Labels)

                labels = list(pn.find('Labels', service_attrs))[0]

                # Healthcheck is a nested dict containing key-value pairs and list
                # store Healcheck in redis as string
                healthcheck = Healthcheck
                stringified_healthcheck_obj = json.dumps(healthcheck)  # convert dict object to string
                healthcheck_hash_key = self.keynamehelper.create_key_name("healthcheck", service_name)
                self.redis.set(healthcheck_hash_key, stringified_healthcheck_obj)
                # self.redis.hmset(healthcheck_hash_key, stringified_healthcheck_obj)

                # in redis, list of strings can be pushed onto a named list_key
                # Args =  ['nwm_mpi-worker_serv2_NBFTGI-SPQRUZ:3', 'nwm_mpi-worker_serv1_NBFTGI-SPQRUZ:3', 'nwm_mpi-worker_serv0_NBFTGI-SPQRUZ:4']
                print("Args is an instance of list:", isinstance(Args,list))
                print("Args is an instance of str:", isinstance(Args,str))
                service_key = self.keynamehelper.create_key_name(service_name)
                print("In retrieve_running_jobs_attr_items_from_redis: service_key = {}".format(service_key))
                p = self.redis.pipeline()
                try:
                    self.redis.watch(service_key)
                    for string in Args:
                        p.rpush(service_key, string)
                except WatchError:
                    logging.debug("Write conflict in store_running_jobs_attr_items_in_redis: {}".format(service_key))
                finally:
                    p.reset()
                    logging.info("In store_running_jobs_attr_items_in_redis: complete writing Args!")

                # In redis, dict can be stored as hash
                # e.g.: Labels =  {'cpus_alloc': '3', 'com.docker.stack.image': '127.0.0.1:5000/nwm-2.0', \
                #                  'com.docker.stack.namespace': 'nwm', 'Hostname': 'nwcal-ucs2.nwc.nws.noaa.gov'}
                labels_key = self.keynamehelper.create_key_name("labels", service_name)
                # self.redis.hmset(labels_key, Labels)
                self.redis.hmset(labels_key, labels)

                # the services.create() defines Mounts as a list of strings, but docker service inspect outputs it as a list containing a single dict
                print("In store_running_jobs_attr_items_in_redis, Mounts =", Mounts)
                print("In store_running_jobs_attr_items_in_redis, Mounts is insatnce of list:", isinstance(Mounts,list))
                mounts_dict = Mounts[0][0]
                print("In store_running_jobs_attr_items_in_redis, Mounts is insatnce of list:", isinstance(mounts_dict,dict))
                source = mounts_dict['Source']
                target = mounts_dict['Target']
                options = 'rw'
                mounts_string = source + ':' + target + ':' + options
                #  mounts = [mts_string]
                print("In store_running_jobs_attr_items_in_redis: mounts = ", mounts_string)
                mounts_key = self.keynamehelper.create_key_name("mounts", service_name)
                self.redis.set(mounts_key, mounts_string)
                # self.redis.set(mounts_key, mounts_dict)

                # RestartPolicy = {'Condition': 'none', 'Delay': 0, 'MaxAttempts': 0, 'Window': 0} is a class object similar to Healthcheck
                # self.redis.hmset(restart_policy_key, RestartPolicy)
                stringified_restart_policy = json.dumps(RestartPolicy)  # convert dict object to string
                restart_policy_key = self.keynamehelper.create_key_name("restart_policy", service_name)
                self.redis.set(restart_policy_key, stringified_restart_policy)

                # create a dict of strings
                Image_redis = Image[0]    # str
                Name_redis = Name[0]      # str
                Command_redis = Command[0][0]    # list of str or str
                Hostname =  "{{.Service.Name}}"    # str constant
                Constraints_redis = Constraints[0][0]    # list of str
                service_dict_str = {"Image": Image_redis, "Name": Name_redis, "Command": Command_redis, "Hostname": Hostname,
                                    "Constraints": Constraints_redis}
                # store the dict in redis
                service_dict_key = self.keynamehelper.create_key_name("service_dict_str", service_name)
                self.redis.hmset(service_dict_key, service_dict_str)

                # taking a snapshot of current running jobs and push it on to redis
                # need to save service_name to redis so that service attributes can be retrieved from redis based on servcie_name
                # can use either the redis list or set data type
                # FIXME: choose one of the following
                # using list method
                # self.redis.rpush(running_services_key, service_name)
                # using set data type
                self.redis.sadd(s_set_key, service_name)
                print("-" * 10)
        print("\nend of que_monitor.check_runningJobs")
        print("=" * 30)
        return

    def retrieve_running_jobs_attr_items_from_redis(self) -> list:
        """
        Retrive services.attrs for all jobs in running job queue stored in redis, 
        then use the services.attrs to build up the runningJobList

        Parameters
        ----------
            No input parameters

        Returns
        -------
        runningJobList
            A list of all running jobs last saved into redis
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # test out some service functions
        service_list = client.services.list()

        # Initialize runningJobList the first time it is called
        runningJobList = list()

        # FIXME: choose one of the following
        # iterate through the saved service list
        ## running_services_key = self.keynamehelper.create_key_name("running_service_list")
        ## service_name = self.redis.lpop(running_services_key)
        ## while service_name != None:

        # iterate through the saved service set
        s_set_key = self.keynamehelper.create_key_name("running_service_set")
        service_name = self.redis.spop(s_set_key)
        while service_name != None:
            # retrieve Healthcheck from redis
            healthcheck_hash_key = self.keynamehelper.create_key_name("healthcheck", service_name)
            # stringified_healthcheck_obj = self.redis.hgetall(healthcheck_hash_key)
            stringified_healthcheck_obj = self.redis.get(healthcheck_hash_key)
            Healthcheck = json.loads(stringified_healthcheck_obj)  # convert string data to object(dict/JSON)

            # in redis, list of strings can be pushed onto a named list_key
            # Args =  ['nwm_mpi-worker_serv2_NBFTGI-SPQRUZ:3', 'nwm_mpi-worker_serv1_NBFTGI-SPQRUZ:3', 'nwm_mpi-worker_serv0_NBFTGI-SPQRUZ:4']

            # code for retrieving Args list of strings
            # this code block operates only on a single specific service with given service_name
            # the top outside loop iterates through all the running services
            service_key = self.keynamehelper.create_key_name(service_name)
            print("In retrieve_running_jobs_attr_items_from_redis: service_key = {}".format(service_key))
            p = self.redis.pipeline()
            args_list = list()
            try:
                self.redis.watch(service_key)
                # for str in Args:
                args = p.lpop(service_key)
                print("In retrieve_running_jobs_attr_items_from_redis: args = {}".format(args))
                while args != None:
                    args_list.append(args)
                    args = p.lpop(service_key)
                    print("In retrieve_running_jobs_attr_items_from_redis: args = {}".format(args))
            except WatchError:
                logging.debug("Read error in store_running_jobs_attr_items_in_redis: {}".format(service_key))
            finally:
                p.reset()
                logging.info("In store_running_jobs_attr_items_in_redis: complete writing Args!")

            # In redis, dict can be stored as hash
            # e.g.: Labels =  {'cpus_alloc': '3', 'com.docker.stack.image': '127.0.0.1:5000/nwm-2.0', \
            #                  'com.docker.stack.namespace': 'nwm', 'Hostname': 'nwcal-ucs2.nwc.nws.noaa.gov'}

            # code for retrieving the labels dict from redis
            # in principle, could combine the next three dicts for data efficiency, but more difficult to separate them
            labels_key = self.keynamehelper.create_key_name("labels", service_name)
            labels_dict = self.redis.hgetall(labels_key)

            # the services.create() defines Mounts as a list of strings, but docker service inspect outputs it as a list containing a single dict
            # code for retrieving mounts dict from redis
            mounts_key = self.keynamehelper.create_key_name("mounts", service_name)
            mounts_dict = self.redis.get(mounts_key)

            # RestartPolicy = {'Condition': 'none', 'Delay': 0, 'MaxAttempts': 0, 'Window': 0} is a class object similar to Healthcheck
            restart_policy_key = self.keynamehelper.create_key_name("restart_policy", service_name)
            # restart_policy = self.redis.hgetall(restart_policy_key)
            # retrieve restart_policy from redis
            stringified_restart_policy = self.redis.get(restart_policy_key)
            restart_policy = json.loads(stringified_restart_policy)  # convert string data to object(dict/JSON)

            # initlize a dictionary object
            service_dict_for_redis = dict()

            # retrieve from redis
            service_dict_key = self.keynamehelper.create_key_name("service_dict_str", service_name)
            service_dict_str = self.redis.hgetall(service_dict_key)

            service_dict_for_redis.update(service_dict_str)
            service_dict_for_redis.update(Healthcheck)
            service_dict_for_redis.update(args_list)
            service_dict_for_redis.update(labels_dict)
            service_dict_for_redis.update(mounts_dict)
            service_dict_for_redis.update(restart_policy)

            runningJobList.append(service_dict_for_redis)
            service_name = self.redis.spop(s_set_key)

        print("\nend of retrieve_running_jobs_attr_items_from_redis")
        print("=" * 30)
        return runningJobList


    def store_job_state_in_redis(self):
        """
        Store the job state of current service tasks

        Parameters
        No input parameters

        Returns
        -------
        None

        """
        print("In function store_job_state_in_redis():")
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # test out some service functions
        service_list = client.services.list()

        # initialize the service_state_list
        service_state_list = list()

        # create the redis key for service task id set
        task_set_key = self.keynamehelper.create_key_name("service_tasks")

        # iterate through entire service list
        for service in service_list:
            service_attrs = service.attrs
            service_name = service.name
            # print("service_name = ", service.name)
            if srv_basename in service_name:
                for task in service.tasks():
                    try:
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
                        (serviceName, taskState) = task_state.split(':')

                        service_state_dict = {"service_name": service_name, "taskState": taskState, "task_host": task_host,
                                              "task_container_id": task_container_id, "task_disired_state": task_disired_state}
                        task_key = self.keynamehelper.create_key_name("running_services", task_service_id)
                        self.redis.hmset(task_key, service_state_dict)

                        # save task_service_id to redis set as key for retrieving service_stat_dict later on
                        self.redis.sadd(task_set_key, task_service_id)
                    except:
                        raise RedisError("Error occurred in storing task states to redis")


    def retrieve_job_state_from_redis(self):
        """
        Retrieve the last saved task state of the running job queue from redis

        Parameters
        No input parameters

        Returns
        -------
        service_state_list
            A list of dicts containing task state and other relevant variables of the most recent running job queue
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client

        # initialize service_state_list
        service_state_list = list()

        # create t_set_key needed to find task_service_id, which has a one-to-one correpondence
        # with service_state_dict
        task_set_key = self.keynamehelper.create_key_name("service_tasks")
        task_service_id = self.redis.spop(task_set_key)
        while task_service_id != None:
            task_key = self.keynamehelper.create_key_name("running_services", task_service_id)
            service_state_dict = self.redis.hgetall(task_key)

            # form service_state_list needed for job resubmission
            service_state_list.append(service_state_dict)

            # extract individual item of the dictionary if necessary such as validation
            # otherwise comment out the next 4 lines of code
            service_name = service_state_dict['service_name']
            print("service_name = {}".format(service_name))
            taskState = service_state_dict['taskState']
            print("taskState = {}".format(taskState))
            # task_host = service_state_dict['task_host']
            # task_container_id = service_state_dict['task_container_id']
            # task_desired_state = service_state_dict['task_desired_state']

            # get next task_service_id from redis
            task_service_id = self.redis.spop(task_set_key)

        print("end of retrieve_job_state_from_redis()")
        return service_state_list

    def restart_running_jobQ(self):
        """
        In case of node failure, system shutdown, or any other types of system failure, restore the running job queue using saved job info.
        This cab done in two ways:
            (a) from saved plain text file
            (b) from Redis database
        Restart jobs from saved checkpoint will be more involved
        """
        # retrieve runningJobList and service_state_list from redis
        runningJobList = self.retrieve_running_jobs_attr_items_from_redis()
        service_state_list = self.retrieve_job_state_from_redis()
        for state_dict in service_state_list:
            self.service_actions(runningJobList, state_dict)


def main():
    #keynamehelper.set_prefix("nwm-monitor")
    #FIXME remove main at some point
    test_pass = os.environ.get('IT_REDIS_CONTAINER_PASS')
    test_port = os.environ.get('IT_REDIS_CONTAINER_HOST_PORT')

    q = QueMonitor("maas", redis_host='localhost',
    redis_port=test_port,
    redis_pass=test_pass)

    client = q.docker_client
    api_client = q.api_client

    # store running jobs attrs in redis database
    if store_running_jobs == True:
        q.store_running_jobs_attr_in_redis
        q.store_running_jobs_attr_items_in_redis()
        q.store_job_state_in_redis()

    # restart the entire previously saved running job queue
    if restart_running_job_queue == True:
        q.restart_running_jobQ()

    #FIXME check_job_state() should not be called before check_runningJobs() in operational run to save service info
    # before beibg removed from service list
    # service_state_list = q.check_job_state()
    print("flush the buffer", flush=True)
    print("-" * 16, flush=True)

    q.check_jobQ()

    #FIXME check_runningJobs() should be callled before each check_job_state() to save service info
    ncall = 0
    # while (ncall <= Ncall_Max):
    (runningJobList, service_dict) = q.check_runningJobs(ncall)
        # ncall += 1
        # time.sleep(30)

    # print("runningJobList: ", *runningJobList)
    print("\nIn main: runningJobList = ")
    ## pp(runningJobList)
    for job in runningJobList:
        print("Job name =", job['Name'])
    print("-" * 30, "\n")

    #time.sleep(60)
    service_state_list = q.check_job_state()

    state_dict = q.build_state_list_reqid_set(service_state_list)
    q.service_actions(runningJobList, state_dict)

    # if (jobState == 'complete') or (jobState == 'failed'):
    #     for service_name in service_list:
    #         service = q.resubmit(runningJobList, service_dict, service_name)

    nodeList = q.get_node_info()

    # (cpusList, user_key) = q.retrieve_job_metadata("shengting.cui")

    #TODO create a function that returns the current availble resources using Redis
    #q.print_resource_details()

    print("end of que_monitor")

if __name__ == "__main__":
    main()
