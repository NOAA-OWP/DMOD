#!/usr/bin/env python3

import logging
from typing import Optional
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
from pathlib import Path

## local imports
#from ..utils.clean import clean_keys

# from other dmod libs
from dmod.redis import RedisBacked, KeyNameHelper
from dmod.scheduler.job import RedisBackedJobManager, JobManagerFactory, JobManager
from dmod.scheduler.job import RequestedJob
from dmod.scheduler.resources import ResourceManager, RedisManager
from dmod.scheduler import RsaKeyPair
from dmod.scheduler.scheduler import Launcher
import dmod.scheduler.utils.parsing_nested as pn
import name_parser as name_parser

MAX_JOBS = 210
Max_Redis_Init = 5
T_INTERVAL = 20

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

    def check_waiting_job_que(self):
        """
        Check and output a list of jobs that are waiting to be executed, allocated, or request received
        """
        # get resource lsi file and Redis parameters
        args = name_parser._handle_args()
        resource_list = name_parser.read_resource_list(Path(args.resource_list_file))
        redis_host, redis_port, redis_pass = name_parser.redis_params(args)

        # use the same arg parameters as the RedisManager in redis_manager.py
        resource_manager = RedisManager("maas", redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass)

        # use the same arg parameters as the Launcher in scheduler.py
        launcher = Launcher(images_and_domains_yaml=args.images_and_domains_yaml, type="dev")

        # instantiate the job manager
        job_manager = JobManagerFactory.factory_create(resource_manager, launcher, host=redis_host, port=redis_port, redis_pass=redis_pass)

        rjmgr = job_manager
        active_jobs = rjmgr.get_all_active_jobs()

        # Process the jobs into various organized collections
        organized_lists = rjmgr._organize_active_jobs(active_jobs)    # the function call returns a list
        jobs_eligible_for_allocate = organized_lists[0]
        jobs_to_release_resources = organized_lists[1]
        jobs_completed_phase = organized_lists[2]

        # Build a fresh prioritized list/queue of allocation eligible Jobs on the spot
        priority_queues = rjmgr.build_prioritized_pending_allocation_queues(jobs_eligible_for_allocate)
        high_priority_queue = priority_queues['high']
        low_priority_queue = priority_queues['low']
        med_priority_queue = priority_queues['medium']

        # it appears that retrieve_job_by_redis_key() function does not remove elements from Redis
        # output job info in high priority queue
        print("--- High Priority Queue ---")
        print("{:^15} {:^15} {:^10} {:^15} {:^10}".format("job_id", "user_id", "cpus", "memory", "high"))     
        print("que_monitor: len(high_priority_queue) = {}".format(len(high_priority_queue)))
        while len(high_priority_queue) > 0:
            hp_job = heapq.heappop(high_priority_queue)
            job_id = hp_job.job_id
            job_req = hp_job._originating_request      # _originating_request = job_request: SchedulerRequestMessage
            user_id = job_req.user_id
            cpus = job_req.cpus
            memory = job_req.memory
            print("{:>15} {:>15} {:10d} {:15d} {:>10}".format(job_is, user_id, cpus, memory, "high"))

        # it appears that retrieve_job_by_redis_key() function does not remove elements from Redis
        # output job info in medium priority queue
        print("--- Medium Priority Queue ---")
        print("{:^15} {:^15} {:^10} {:^15} {:^10}".format("job_id", "user_id", "cpus", "memory", "medium"))     
        print("que_monitor: len(med_priority_queue) = {}".format(len(med_priority_queue)))
        while len(med_priority_queue) > 0:
            hp_job = heapq.heappop(med_priority_queue)
            job_id = hp_job.job_id
            job_req = hp_job._originating_request      # _originating_request = job_request: SchedulerRequestMessage
            user_id = job_req.user_id
            cpus = job_req.cpus
            memory = job_req.memory
            print("{:>15} {:>15} {:10d} {:15d} {:>10}".format(job_is, user_id, cpus, memory, "medium"))

        # it appears that retrieve_job_by_redis_key() function does not remove elements from Redis
        # output job info in low priority queue
        # TODO send output to front end
        print("--- Low Priority Queue ---")
        print("{:^15} {:^15} {:^10} {:^15} {:^10}".format("job_id", "user_id", "cpus", "memory", "medium"))     
        print("que_monitor: len(low_priority_queue) = {}".format(len(low_priority_queue)))
        while len(low_priority_queue) > 0:
            hp_job = heapq.heappop(low_priority_queue)
            job_id = hp_job.job_id
            job_req = hp_job._originating_request      # _originating_request = job_request: SchedulerRequestMessage
            user_id = job_req.user_id
            cpus = job_req.cpus
            memory = job_req.memory
            print("{:>15} {:>15} {:10d} {:15d} {:>10}".format(job_is, user_id, cpus, memory, "medium"))

        # output remaining waiting queue jobs info
        print("--- Waiting Job Queue ---")
        print("{:^15} {:^15} {:^10} {:^15}".format("job_id", "user_id", "cpus", "memory"))
        for job in active_jobs:
            if (job not in priority_queues):
                job_id = req_job.job_id()
                job_req = job._originating_request
                user_id = job_req.user_id
                cpus = job_req.cpus
                memory = job_req.memory
                print("{:>15} {:>15} {:10d} {:15d}".format(job_is, user_id, cpus, memory))
        #print("Ending check_waiting_job_que()")
        #print("=" * 30)

    def check_and_store_runningJobs(self) -> tuple:
        """
        Check the running job queue
        Running job snapshot is needed for restart

        Parameters
        ----------
        No input parameters

        Returns
        -------
        runningJobList
            A list of all current running jobs with key attributes packed into dict format, and a dict
        service_dict
            Service attributes packed into a dictionary
        """
        # docker api
        client = self.docker_client
        api_client = self.api_client
        srv_basename = self.name

        # test out some service functions
        service_list = client.services.list()

        # create a set key to store hash key names
        service_set_key = self.keynamehelper.create_key_name("service_set")

        # Initialize runningJobList the first time it is called
        runningJobList = []

        # iterate through entire service list
        for service in service_list:
            service_attrs = service.attrs
            service_name = service.name
            if srv_basename in service_name:
                logging.info("\nIn check_runningJobs(): service_name = {}".format(service_name))
                #print("\nIn check_runningJobs(): service_name = {}\n".format(service_name))
                # store service_attrs in Redis as string
                stringified_service_attrs = json.dumps(service_attrs)  # convert dict object to string
                service_attrs_hash_key = self.keynamehelper.create_key_name("service_attrs", service_name)
                self.redis.set(service_attrs_hash_key, stringified_service_attrs)
                # store the service_name to a set
                self.redis.sadd(service_set_key, service_name)

                (_, _, serv_name, req_id) = service_name.split('_')
                lens = len(serv_name)
                # FIXME the following line applies to case where nwm_mpi-worker_serv" is used as basename
                index = serv_name[4:lens]
                logging.info("lens = {}".format(lens))
                logging.info("index = {}".format(index))
                # pp(service_attrs)
                Image = pn.find('Image', service_attrs)
                *Image, = Image

                Name = pn.find('Name', service_attrs)
                *Name, = Name

                Constraints = pn.find('Constraints', service_attrs)
                *Constraints, = Constraints
                ContainerSpec = list(pn.find('ContainerSpec', service_attrs))
                # pp(ContainerSpec)
                Mounts = pn.find('Mounts', service_attrs)
                *Mounts, = Mounts

                Args = pn.find('Args', service_attrs)
                *Args, = Args

                Command = pn.find('Command', service_attrs)
                *Command, = Command

                RestartPolicy = pn.find('RestartPolicy', service_attrs)
                *RestartPolicy, = RestartPolicy

                Healthcheck = pn.find('Healthcheck', service_attrs)
                *Healthcheck, = Healthcheck

                Labels = pn.find('Labels', service_attrs)
                *Labels, = Labels

                labels = list(pn.find('Labels', service_attrs))[0]
                L_image =  labels['com.docker.stack.image']
                NameSpace = labels['com.docker.stack.namespace']
                HostNode = labels['Hostname']
                cpus_alloc = labels['cpus_alloc']

                service_dict = {"Image": Image, "Command": Command, "Args": Args, "Constraints": Constraints, "ContainerSpec": ContainerSpec,
                                "Labels": Labels, "Name": Name, "Mounts": Mounts, "Healthcheck": Healthcheck,
                                "RestartPolicy": RestartPolicy, "HostNode": HostNode, "cpus_alloc": cpus_alloc}
                runningJobList.append(service_dict)
        logging.info("end of que_monitor.check_runningJobs")
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
        client = self.docker_client
        #print("\nIn resubmit(): service_name = {}".format(service_name))
        (_, _, serv_name, req_id) = service_name.split('_')
        lens = len(serv_name)
        index = serv_name[4:lens]
        logging.info("lens = {}".format(lens))
        logging.info("index = {}".format(index))

        Image = (service_dict['Image'])[0]
        Name = (service_dict['Name'])[0]
        Constraints = (service_dict['Constraints'])[0]
        Hostname = ((service_dict['ContainerSpec'])[0])['Hostname']

        Mounts = ((service_dict['Mounts'])[0])[0]
        source = Mounts['Source']
        target = Mounts['Target']
        options = 'rw'
        mts_string = source + ':' + target + ':' + options
        mounts = [mts_string]

        Args = (service_dict['Args'])[0]
        args = Args

        Command = (service_dict['Command'])[0]
        command = Command

        Labels = (service_dict['Labels'])[0]
        #pp(Labels)
        #print("Labels isinstance of dict:", isinstance(Labels, dict))
        #print("Labels: Hostname = ", Labels['Hostname'])

        RestartPolicy = (service_dict['RestartPolicy'])[0]
        #pp(RestartPolicy)
        #print("RestartPolicy isinstance of dict:", isinstance(RestartPolicy, dict))
        # condition = RestartPolicy['Condition']
        # print("RestartPolicy: condition = ", condition)
        # restart = docker.types.RestartPolicy(condition = condition)
        restart = RestartPolicy
        restart = docker.types.RestartPolicy(condition='none')

        Healthcheck = (service_dict['Healthcheck'])[0]
        # pp(Healthcheck)

        networks = ["mpi-net"]

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

    def check_system_state(self):
        """
        The function returns logs of a service execution

        check_system_state can be called whenever a service stopped running or experiences a state change
        or called as a streaming process. This will provide a process for job debugging on par with a
        full fledged scheduler on a supercomputer

        Might use logging module to save the output

        Parameters
        ----------
        No input parameter

        Returns
        -------
            No return value from the function
        """
        client = self.docker_client
        srv_basename = self.name
        mpirun = "mpirun"
        failed = "failed"

        # logging some common linux exit status code and signal code
        service_list = client.services.list()
        for service in service_list:
            if srv_basename in service.name:
                for service_log in service.logs(details=True, stdout=True, stderr=True, timestamps=True):
                    # print(service_log)   # output in byte string format
                    service_log_str = str(service_log, 'utf-8')
                    # output regular strings
                    ## print(service_log_str)    # uncomment this line to output all logs in regular string format.
                    if failed in service_log_str:
                        logging.debug("failed info: {}".format(service_log_str))
                    if mpirun in service_log_str:
                        string = service_log_str
                        word = string.split()
                        #print("word is instance of list:", isinstance(word, list))
                        logging.debug("exitcode = {}".format(word[-1]))
                        exitcode = int(word[-1])
                        #print("int exitcode = ", exitcode)
                        if exitcode > 128 and exitcode < 256:
                            fatal_signal_code = exitcode - 128
                            logging.info("service name: {}, fatal signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 4:
                                logging.info("service name: {}, Illegal Instruction, signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 6:
                                logging.info("service name: {}, Abort Signal, signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 8:
                                logging.info("service name: {}, Floating Point Exception, signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 9:
                                logging.info("service name: {}, Kill Signal, signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 11:
                                logging.info("service name: {}, Invalid Memory Reference, signal code: {}".format(service.name, fatal_signal_code))
                            if fatal_signal_code == 13:
                                logging.info("service name: {}, Broken Pipe, signal code: {}".format(service.name, fatal_signal_code))
                        if exitcode == 0:
                            logging.info("service name: {}, exit code: {}, Successful Completion".format(service.name, exitcode))
                        if exitcode == 1:
                            logging.info("service name: {}, exit code: {}, Execution failed".format(service.name, exitcode))
                        if exitcode == 2:
                            logging.info("service name: {}, exit code: {}, Misuse of shell builtins".format(service.name, exitcode))
                        if exitcode == 126:
                            logging.info("service name: {}, exit code: {}, Command invoked cannot execute".format(service.name, exitcode))
                        if exitcode == 127:
                            logging.info("service name: {}, exit code: {}, Command not found".format(service.name, exitcode))
                        if exitcode == 130:
                            logging.info("service name: {}, exit code: {}, Script terminated by Control-C".format(service.name, exitcode))
                        if exitcode == 139:
                            logging.info("service name: {}, exit code: {}, Segmentation Fault".format(service.name, exitcode))

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

        # create the redis key for service task id set
        task_set_key = self.keynamehelper.create_key_name("service_tasks")

        # iterate through entire service list
        service_list = client.services.list()
        service_state_list = []
        for service in service_list:
            service_name = service.name
            if srv_basename in service_name:
                for task in service.tasks():
                    # logging task state
                    logging.info("\tState: {}".format(task['Status']['State']))
                    logging.info("\tTimestamp: {}".format(task['Status']['Timestamp']))
                    logging.info("\tContainerID: {}".format(task['Status']['ContainerStatus']['ContainerID']))
                    logging.info("\tDesiredState: {}".format(task['DesiredState']))
                    logging.info("\tServiceID: {}".format(task['ServiceID']))

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

                    logging.info("\n\tserviceName:taskState: {}".format(task_state))
                    (serviceName, taskState) = task_state.split(':')

                    logging.info("\tserviceName: {}".format(serviceName))
                    logging.info("\ttaskState: {}".format(taskState))
                    logging.info("\ttaskExitCode: {}".format(task_error))
                    logging.info("\ttaskExitCode: {}".format(task_error_num))
                    logging.info("\ttask_host: {}".format(task_host))
                    # pp(task)

                    try:
                        service_state_dict = {"service_name": service_name, "taskState": taskState, "task_host": task_host,
                                              "task_container_id": task_container_id, "task_disired_state": task_disired_state}
                        task_key = self.keynamehelper.create_key_name("running_services", task_service_id)
                        self.redis.hmset(task_key, service_state_dict)

                        # save task_service_id to redis set as key for retrieving service_stat_dict later on
                        self.redis.sadd(task_set_key, task_service_id)
                    except:
                        raise RedisError("Error occurred in storing task states to redis")

                    if (taskState == 'starting'):
                        pass
                    elif (taskState == 'running'):
                        #FIXME This option is for testing the codes involved in resubmitting
                        logging.info("Job {} is running: restart to test code".format(serviceName))
                        service.remove()
                    elif (taskState == 'complete'):
                        logging.info("Job {} successfully finished".format(serviceName))
                        service.remove()
                    elif (taskState == 'failed'):
                        logging.info("Job {} failed to complete".format(serviceName))
                        logging.info("Please examine the task logs for cause before removing the service")
                        # Check reasons and consider resubmit
                        service.remove()
                    elif (taskState == 'shutdown'):
                        # TODO consider resubmit
                        logging.info("Docker requested {} to shutdown".format(serviceName))
                        service.remove()
                    elif (taskState == 'rejected'):
                        # TODO check node state and resubmit
                        logging.info("The worker node rejected {}".format(serviceName))
                        service.remove()
                    elif (taskState == 'ophaned'):
                        # TODO check node state and possibly resubmit to a different node
                        logging.info("The node for {} down for too long".format(serviceName))
                        service.remove()
                    elif (taskState == 'remove'):
                        # TODO check node state and resubmit
                        logging.info("The node for {} down for too long".format(serviceName))
                        service.remove()
                    else:
                        pass
                    service_state = {"taskState": taskState, "service_name": service_name}
                    service_state_list.append(service_state)
                    #print("In check_job_state, service_state_list:")
                    #pp(service_state_list)
                    #print("-" * 30)
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
        #print("\nIn build_state_list_reqid_set: service_state_list =")
        #pp(service_state_list)

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
        #print("\nIn build_state_list_reqid_set: state_dict =")
        #pp(state_dict)
        #print("=" * 30)
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
            logging.info("\nIn servname_gen: req_id_state = {}".format(req_id_state))
            for service_name in state_list:
                (_, _, _, req_id) = service_name.split('_')
                logging.info("In servname_gen: req_id = {}".format(req_id))
                if (req_id == req_id_state):
                    logging.info("In servname_gen: service_name = {}".format(service_name))
                    #print("-" * 30)
                    yield service_name

    def service_actions(self, runningJobList, state_dict):
        """
        Take sevice action based on job state returned in state_dict

        Parameters
        ----------
        runningJobList
            List that contains the list of worker services with specific basename
        state_dict
            Dictionary that contains the service task states

        Returns
        -------
            None
        """
        #print("\n-----In service_actions-----")
        # pp(state_dict)
        for jobState in state_dict:
            # task state failed
            # FIXME this is only used in test run
            if (jobState == "failed_list"):
                failed_list = state_dict[jobState]
                logging.debug("In service_actions: failed_list = {}".format(failed_list))
                failed_set = state_dict['failed_set']
                logging.debug("In service_actions: failed_set = {}".format(failed_set))
                if len(failed_list) > 0:
                    for servname in self.servname_gen(failed_set, failed_list):
                        service_name = servname
                        logging.debug("In service_actions: service_name = {}".format(service_name))
                        for job in runningJobList:
                            #FIXME: Name in the original runningJobList is itself a list
                            Name = job['Name'][0]
                            logging.debug("In service_actions: Name = {}, servname = {}".format(Name, servname))
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                # service = self.resubmit_using_redis_items(service_dict, service_name)
                                # avoid calling servname_gen() function simultaneously from different jobState
                                time.sleep(1)
                                logging.info("In service_actions: service = {}".format(service))
                # print("-" * 30)

            # task state complete
            # FIXME this is only used in test run
            if (jobState == "complete_list"):
                complete_list = state_dict[jobState]
                logging.info("In service_actions: complete_list = {}".format(complete_list))
                complete_set = state_dict['complete_set']
                logging.info("In service_actions: complete_set = {}".format(complete_set))
                if len(complete_list) > 0:
                    for servname in self.servname_gen(complete_set, complete_list):
                        service_name = servname
                        logging.info("In service_actions: service_name from servname_gen() = {}".format(service_name))
                        for job in runningJobList:
                            Name = job['Name'][0]
                            logging.info("In service_actions: Name = {}, service_name = {}".format(Name, servname))
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                # service = self.resubmit_using_redis_items(service_dict, service_name)
                                # avoid calling servname_gen() function simultaneously from different jobState
                                time.sleep(1)
                                logging.info("In service_actions: service = {}".format(service))
                # print("-" * 30)

            # task state running
            # FIXME this is only used in test run
            if (jobState == "running_list"):
                running_list = state_dict[jobState]
                # print("In service_actions: running_list =", running_list)
                running_set = state_dict['running_set']
                # print("In service_actions: running_set =", running_set)
                if len(running_list) > 0:
                    for servname in self.servname_gen(running_set, running_list):
                        logging.info("In service_actions: servname = {}".format(servname))
                        service_name = servname
                        logging.info("In service_actions: service_name = {}".format(service_name))
                        logging.info("In service_actions: len = {}".format(len(runningJobList)))
                        for job in runningJobList:
                            Name = job['Name'][0]
                            logging.info("In service_actions: Name = {}".format(Name))
                            if Name == service_name:
                                service_dict = job
                                # print("service_dict", service_dict)
                                service = self.resubmit(service_dict, service_name)
                                # service = self.resubmit_using_redis_items(service_dict, service_name)
                                logging.info("In service_actions: service = {}\n".format(service))
                # print("-" * 30)

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
                                # service = self.resubmit_using_redis_items(service_dict, service_name)

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
                                # service = self.resubmit_using_redis_items(service_dict, service_name)

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
                                # service = self.resubmit_using_redis_items(service_dict, service_name)

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
                                # service = self.resubmit_using_redis_items(service_dict, service_name)


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
        #print("\nIn get_node_info:\nnodeList: ", *nodeList, sep = "\n")
        return nodeList

    #TODO A better function may be implemented for checking current available rerources
    #TODO REMOVE/LINK TO RESOURCE MANAGER
    def print_resource_details(self):
        """Print the details of remaining resources after allocating the request """
        #print("Resources remaining:")
        #FIXME this is BROKEN. If resource definitions are needed, they must be externally linked.
        #I.e. read a resource file or read from redis or use resource manager
        for resource in resources:
            e_key = self.keynamehelper.create_key_name("resource", resource['node_id'])
            logging.info("hgetall(e_key): {}".format(self.redis.hgetall(e_key)))

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
        srv_basename = self.name

        # Initialize runningJobList the first time it is called
        runningJobList = list()

        # retrieve first element of the service set from redis
        service_set_key = self.keynamehelper.create_key_name("service_set")
        service_name = self.redis.spop(service_set_key)
        # iterate through the saved service set
        while service_name != None:
            service_attrs_hash_key = self.keynamehelper.create_key_name("service_attrs", service_name)
            stringified_service_attrs = self.redis.get(service_attrs_hash_key)
            service_attrs = json.loads(stringified_service_attrs)  # convert string data to object(dict/JSON)

            # extract individual attribute to be used for creating service
            Image = pn.find('Image', service_attrs)
            *Image, = Image
            Name = pn.find('Name', service_attrs)
            *Name, = Name
            Constraints = pn.find('Constraints', service_attrs)
            *Constraints, = Constraints
            ContainerSpec = list(pn.find('ContainerSpec', service_attrs))
            pp(ContainerSpec)
            Mounts = pn.find('Mounts', service_attrs)
            *Mounts, = Mounts
            Args = pn.find('Args', service_attrs)
            *Args, = Args
            Command = pn.find('Command', service_attrs)
            *Command, = Command
            RestartPolicy = pn.find('RestartPolicy', service_attrs)
            *RestartPolicy, = RestartPolicy
            Healthcheck = pn.find('Healthcheck', service_attrs)
            *Healthcheck, = Healthcheck
            Labels = pn.find('Labels', service_attrs)
            *Labels, = Labels
            labels = list(pn.find('Labels', service_attrs))[0]
            HostNode = labels['Hostname']
            cpus_alloc = labels['cpus_alloc']

            service_dict = {"Image": Image, "Command": Command, "Args": Args, "Constraints": Constraints, "ContainerSpec": ContainerSpec,
                            "Labels": Labels, "Name": Name, "Mounts": Mounts, "Healthcheck": Healthcheck,
                            "RestartPolicy": RestartPolicy, "HostNode": HostNode, "cpus_alloc": cpus_alloc}
            runningJobList.append(service_dict)

            # retrieve service_name for next iteration
            service_name = self.redis.spop(service_set_key)

        #print("\nend of que_monitor.retrieve_running_jobs_from_redis")
        #print("=" * 30)
        return runningJobList

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
            #print("service_name = {}".format(service_name))
            taskState = service_state_dict['taskState']
            #print("taskState = {}".format(taskState))
            # task_host = service_state_dict['task_host']
            # task_container_id = service_state_dict['task_container_id']
            # task_desired_state = service_state_dict['task_desired_state']

            # get next task_service_id from redis
            task_service_id = self.redis.spop(task_set_key)

        #print("end of retrieve_job_state_from_redis()")
        return service_state_list

    def restart_running_jobQ(self):
        """
        In case of node failure, system shutdown, or any other types of system failure, restore the running job queue using saved job info.
        This cab done in two ways:
            (a) from saved plain text file
            (b) from Redis database
        Do we need to keep the original order? We may to fit all the jobs into the nodes. Otherwise, it may not be able to.
        Restart jobs from saved checkpoint will be more involved
        """
        #FIXME: check the ser_prefix() function in RedisBacked

        service_state_list = self.check_job_state()
        ## self.check_job_state()
        #FIXME: use the next line for alternative approach storing/retriving redis data
        runningJobList = self.retrieve_running_jobs_attr_from_redis()
        # runningJobList = self.retrieve_running_jobs_attr_items_from_redis()
        service_state_list = self.retrieve_job_state_from_redis()
        state_dict = self.build_state_list_reqid_set(service_state_list)
        self.service_actions(runningJobList, state_dict)
        #print("end of restart_running_jobQ")

def main():
    #self.keynamehelper.set_prefix("nwm-monitor")
    #FIXME remove main at some point
    test_pass = os.environ.get('IT_REDIS_CONTAINER_PASS')
    test_port = os.environ.get('IT_REDIS_CONTAINER_HOST_PORT')

    q = QueMonitor("maas", redis_host='localhost',
    redis_port=test_port,
    redis_pass=test_pass)

    # get info for all jobs that have been submitted
    q.check_waiting_job_que()

    # get runningJobList
    (runningJobList, service_dict) = q.check_and_store_runningJobs()

    # obtain job task state
    service_state_list = q.check_job_state()

    # check the return message from the system when a job stopped or state changed
    q.check_system_state()

    #FIXME use resource manager
    q.print_resource_details()

    # let the jobs run to finish
    time.sleep(30)

    # runningQ_restart = False
    runningQ_restart = True

    if runningQ_restart == True:
        q.restart_running_jobQ()

    else:
        # TODO double check the interaction between this function call and q.check_job_state()
        state_dict = q.build_state_list_reqid_set(service_state_list)
        q.service_actions(runningJobList, state_dict)

    nodeList = q.get_node_info()

    while True:
        time.sleep(30)
        q.check_system_state()

    print("end of que_monitor")

if __name__ == "__main__":
    main()
