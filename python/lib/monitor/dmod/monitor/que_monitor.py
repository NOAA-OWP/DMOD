#!/usr/bin/env python3
from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Dict, List, Optional, Set, Tuple
import json
import docker
from docker.models.services import Service
from dmod.redis import RedisBacked
from dmod.scheduler.job import Job, JobStatus, JobExecStep
from dmod.scheduler.job.job_manager import RedisBackedJobManager

MAX_JOBS = 210
Max_Redis_Init = 5
T_INTERVAL = 20

logging.basicConfig(
    filename='que_monitor.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")


class Monitor(ABC):
    """
    Abstract interface class for ::class:`Job` monitor type.

    Abstraction type for monitoring jobs for status changes.  Type declares abstract methods for obtaining the
    collection of jobs to be monitored (i.e., ::method:`get_jobs_to_monitor`) and for monitoring whether a specific job
    has undergone a status change (i.e., ::method:`monitor_job`).

    Type also provides a ::method:`monitor_jobs` method containing the routine for monitoring all applicable jobs and
    returning data on changes.
    """

    @abstractmethod
    def get_jobs_to_monitor(self) -> List[Job]:
        """
        Get a list of the jobs currently needing monitoring.

        This will likely be something akin to "active" jobs, but the particular conditions should be documented for each
        implementation.

        Returns
        -------
        List[Job]
            A list of the job objects corresponding to executing jobs within the runtime that need to be monitored.
        """
        pass

    @abstractmethod
    def monitor_job(self, job: Job) -> Optional[Tuple[JobStatus, JobStatus]]:
        """
        Monitor a given job for changed status.

        Check whether the job modeled by the given object has changed in status, relative to an expected previous
        status.  When there is a change, return the previous and updated status values respectively.

        Implementations should document the means by which the previous status is determined.  They should also document
        what the state of the job object will be at the end of this function's execution (i.e., will the object have the
        original or updated ::attribute:`Job.status` value).

        Parameters
        ----------
        job: Job
            The job to check.

        Returns
        -------
        Optional[Tuple[JobStatus, JobStatus]]
            ``None`` when the job has not changed status, or a tuple of its previous and updated status when different.
        """
        pass

    def monitor_jobs(self) -> Tuple[Dict[str, Job], Dict[str, JobStatus], Dict[str, JobStatus]]:
        """
        Monitor jobs and return data on those that have changed.

        Monitor jobs according to ::method:`get_jobs_to_monitor` and ::method:`monitor_job`, returning details of
        observed changes as a tuple of three dictionaries.  These are all keyed by job id and contain the mapped job
        objects, original statuses, and new statuses respectively.

        Returns
        -------
        Tuple[Dict[str, Job], Dict[str, JobStatus], Dict[str, JobStatus]]
            A tuple of three dictionaries for jobs with status changes, having values of job object, original status,
            and updated status respectively, and all keyed by job id.
        """
        # job_id to job object
        jobs_with_changed_state = dict()
        # job_id to status (for jobs that are different/updated)
        original_job_statuses = dict()
        updated_job_statuses = dict()

        for job in self.get_jobs_to_monitor():
            monitor_result = self.monitor_job(job)
            if monitor_result:
                jobs_with_changed_state[job.job_id] = job
                original_job_statuses[job.job_id] = monitor_result[0]
                updated_job_statuses[job.job_id] = monitor_result[1]

        return jobs_with_changed_state, original_job_statuses, updated_job_statuses


class DockerSwarmMonitor(Monitor, ABC):
    """
    Abstract subtype of ::class:`Monitor` for monitoring Docker-Swarm-based jobs.

    Abstract subtype of ::class:`Monitor` for monitoring jobs running in containers in Docker Swarm.  Type implements
    ::method:`monitor_job` from superclass and provides methods for checking the Docker runtime and determining a job's
    true status.

    Type does not provide implementation of ::method:`get_jobs_to_monitor`.
    """
    _EXEC_STEP_DOCKER_STATUS_MAP: Dict[JobExecStep, Set[str]] = {
        JobExecStep.SCHEDULED: {'new', 'pending', 'assigned', 'accepted', 'preparing', 'starting'},
        JobExecStep.RUNNING: {'running'},
        JobExecStep.COMPLETED: {'complete'},
        JobExecStep.STOPPED: {'shutdown'},
        JobExecStep.FAILED: {'failed', 'rejected', 'orphaned', 'remove'}
    }
    """ Map of job exec steps and the set of string forms of Docker Service Tasks ``state`` values that correspond. """

    @classmethod
    def _get_task_state_and_exec_step_counts(cls, service: Service) -> Tuple[Dict[str, int], Dict[JobExecStep, int]]:
        """
        For a given service, examine the state of its tasks, returning a dictionary of state values to number of times
        occurring and a dictionary of converted ::class:`JobExecStep` for the state values to number of times occurring.

        Parameters
        ----------
        service : Service
            The Docker service in question.

        Returns
        -------
        Tuple[Dict[str, int], Dict[JobExecStep, int]]
            Dictionary of task state values to number of occurrences, and dictionary of equivalent ::class:`JobExecStep`
            values for observed task states to summed total occurrences.
        """
        # First get the statuses from all tasks for this service
        task_states = dict()
        for task in service.tasks():
            ts = task['Status']['State']
            if ts in task_states:
                task_states[ts] += 1
            else:
                task_states[ts] = 1
        # Then also get these as exec steps
        task_exec_steps = dict()
        for state in task_states:
            exec_step = cls.get_exec_step_for_job_docker_task_state(state)
            if exec_step in task_exec_steps:
                task_exec_steps[exec_step] += task_states[state]
            else:
                task_exec_steps[exec_step] = task_states[state]
        return task_states, task_exec_steps

    @classmethod
    def _process_service_exec_step(cls, task_exec_steps: Dict[JobExecStep, int], replica_count: int) -> JobExecStep:
        """
        Process and return the correct ::class:`JobExecStep` for some service given details about the service's tasks.

        Parameters
        ----------
        task_exec_steps : Dict[JobExecStep, int]
            A dict of the mapped ::class:`JobExecStep` values for the service's tasks's states and the counts of each.
        replica_count : int
            The number of task replicas desired per the configuration of the service.

        Returns
        -------
        JobExecStep
            The
        """
        # Now apply some rules to determine an exec step value for the service
        #
        # If there was only a single exec step encountered in tasks, then that's the service's step
        if len(task_exec_steps) == 1:
            # This syntax unpacks dict key(s) to tuple (mind the comma), then gets the 1st (and here, only) element
            return (*task_exec_steps,)[0]

        # If any task is running, consider the entire service in the running step
        # TODO: may want to rethink whether any STOPPED instances effect this
        # TODO: may want to rethink whether a certain number of FAILED instances effect this
        elif JobExecStep.RUNNING in task_exec_steps:
            return JobExecStep.RUNNING

        # If there are tasks SCHEDULED (and by implication, there are tasks COMPLETED, STOPPED, or FAILED, if we got
        # here), consider the service RUNNING (something happened and we don't really want to go backward in steps)
        elif JobExecStep.SCHEDULED in task_exec_steps:
            return JobExecStep.RUNNING

        # If task steps include STOPPED and either COMPLETED or FAILED, this is tricky, but for now treat service
        # as STOPPED
        # TODO: may need to rethink this
        elif JobExecStep.STOPPED in task_exec_steps:
            return JobExecStep.STOPPED

        # Implies there are > 1 steps types seen, but no RUNNING, SCHEDULED, or STOPPED (i.e., COMPLETED and FAILED)
        # If there are completed and failed tasks, look at how many completed compared to expected container count,
        # and assume that if there are more completed than replicas,
        else:
            # If we've had enough completed to cover the desired replicas, infer that no more are pending restart
            if task_exec_steps[JobExecStep.COMPLETED] >= replica_count:
                return JobExecStep.COMPLETED
            # Otherwise, assume still running
            else:
                # TODO: this almost certainly is wrong by itself, and needs some additional check to make sure it hasn't
                #  settled into failure; e.g., how long the service's states have been as they currently are
                return JobExecStep.RUNNING

    @classmethod
    def filter_services_for_job(cls, job: Job, services: List[Service]) -> List[Service]:
        """
        Filter a provided list of Docker services to those specifically associated with a given job, based on the
        standard format of service names.

        Parameters
        ----------
        job : Job
            A particular job of interest.
        services : List[Service]
            A list of Docker services to be filtered.

        Returns
        -------
        List[Service]
            The sub-collection of services from the provided list that are associated with the given job.
        """
        associated_services = []
        job_service_name_set = set(job.allocation_service_names)
        if len(job_service_name_set) > 0:
            for service in services:
                if service.name in job_service_name_set:
                    associated_services.append(service)
        return associated_services

    @classmethod
    def get_exec_step_for_job_docker_task_state(cls, task_state: str):
        """
        Get the primary associated ::class:`JobExecStep` for the given Docker service task state value.

        Keep in mind that the associate between jobs and Docker tasks is not 1-to-1, so this by itself is not
        necessarily an indication of the exec step of a job that has a task with the given task value.

        The task state is within a nested dictionary for a Docker ::class:`docker.models.services.Service` object.  The
        list of tasks is available via ::method:`docker.models.services.Service.tasks`.  From there, each dictionary has
        a ``Status`` key mapped to another dictionary, which itself has a ``State`` key for the state value.  This is
        what should be passed as an argument to this method.

        Parameters
        ----------
        task_state: str
            The string representation value for one of the enumeration values for Docker service tasks.

        Returns
        -------
        JobExecStep
            The corresponding ::class:`JobExecStep` value.
        """
        for exec_step in cls._EXEC_STEP_DOCKER_STATUS_MAP:
            if task_state in cls._EXEC_STEP_DOCKER_STATUS_MAP[exec_step]:
                return task_state
        # Fall back to fail
        return JobExecStep.FAILED

    def __init__(self, docker_client: Optional[docker.DockerClient] = None,
                 api_client: Optional[docker.APIClient] = None):
        if docker_client:
            self._docker_client = docker_client
            # TODO: should we account/allow for the api_client param to be None in this case?
            self._api_client = api_client
        else:
            self.check_docker()
            self._docker_client = docker.from_env()
            self._api_client = docker.APIClient()
        self._last_checked: Optional[datetime] = None
        self._service_state_map = {}

    @property
    def api_client(self) -> docker.APIClient:
        return self._api_client

    def check_docker(self):
        """
        Test that docker is up running
        """
        try:
            # Check docker client state
            self._docker_client.ping()
        except:
            raise ConnectionError("Please check that the Docker Daemon is installed and running.")

    def check_implied_job_exec_step(self, job: Job) -> JobExecStep:
        """
        Infer the appropriate ::class:`JobExecStep` value for a job based on the real-time states of the services
        created for its allocations.

        Parameters
        ----------
        job : Job
            The job in question.

        Returns
        -------
        JobExecStep
            The appropriate ::class:`JobExecStep` value for the given job.
        """
        # Start by getting the services for a given job.
        job_alloc_services = self.filter_services_for_job(job=job, services=self.docker_client.services.list())

        # Then, process the exec step for each service, based on the states of each service's task(s)
        service_states = []
        for service in job_alloc_services:
            # Get counts for task states and counts for task mapped exec_steps
            task_states, task_exec_steps = self._get_task_state_and_exec_step_counts(service=service)
            # TODO: this will need to be tested
            desired_replica_count = service.attrs['Spec']['Mode']['Replicated']['Replicas']
            # Now apply some rules to determine an exec step value for the service
            service_states.append(self._process_service_exec_step(task_exec_steps=task_exec_steps,
                                                                  replica_count=desired_replica_count))
        # Leave list also for now, but work with these below as a set
        service_states_set = set(service_states)

        # Now, process the appropriate exec step of the job, given the values for its services
        #
        # First, if there is only a single step type seen, then clearly that should be returned
        if len(service_states_set) == 1:
            return service_states[0]

        # If any service is FAILED, treat the job as FAILED
        elif JobExecStep.FAILED in service_states_set:
            # TODO: consider whether something additional is needed here or elsewhere to ensure any services other than
            #  the failed service have been stopped
            return JobExecStep.FAILED

        # Likewise, if (nothing is FAILED but) any service is STOPPED, treat the job as STOPPED
        elif JobExecStep.STOPPED in service_states_set:
            # TODO: consider whether something additional is needed here or elsewhere to ensure any services other than
            #  the stopped service have been or will be stopped
            return JobExecStep.STOPPED

        # Otherwise, there is some combo of SCHEDULED, RUNNING, and COMPLETED, with there being at least two of these.
        # This implies there must always be at least one service that previously began running (even if it isn't now)
        # and at least one service that is not complete (even if it isn't running yet), so the job is RUNNING.
        else:
            return JobExecStep.RUNNING

    @property
    def docker_client(self) -> docker.DockerClient:
        return self._docker_client

    def monitor_job(self, job: Job) -> Optional[Tuple[JobStatus, JobStatus]]:
        """
        Monitor whether a given job has changed status.

        Examine whether the status of an actual job in the backing Docker Swarm corresponds to the previously observed
        and persisted status for it.  Previous status is read directly from the parameter job object, and current is
        inferred from getting the exec step via ::method:`check_implied_job_exec_step`.

        For a job that does have an updated status, the method will adjust the state of the param object to set its
        ::attribute:`status` equal to the updated value.

        Parameters
        ----------
        job: Job
            The job to check.

        Returns
        -------
        Optional[Tuple[JobStatus, JobStatus]]
            ``None`` when the job has not changed status, or a tuple of its previous and updated status when different.
        """
        # TODO: verify that it is not necessary to examine status directory (i.e., check job phase) due to some
        #  guarantee on never jumping to the same step of a different phase between monitoring calls
        new_exec_step = self.check_implied_job_exec_step(job)
        if job.status_step == new_exec_step:
            return None
        previous_status = job.status
        job.status_step = new_exec_step
        updated_job_status = job.status
        return previous_status, updated_job_status


class RedisBackedMonitor(Monitor, RedisBacked, ABC):
    """
    Subtype of ::class:`Monitor` and ::class:`RedisBacked` that determines jobs to monitor from Redis.
    """
    def __init__(self, resource_pool: str,
                 redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
        RedisBacked.__init__(self=self, resource_pool=resource_pool, redis_host=redis_host,
                             redis_port=redis_port, redis_pass=redis_pass, **kwargs)
        if 'type' in kwargs:
            key_prefix = RedisBackedJobManager.get_key_prefix(environment_type=kwargs['type'])
        else:
            key_prefix = RedisBackedJobManager.get_key_prefix()
        self._active_jobs_set_key = self.keynamehelper.create_key_name(key_prefix, 'active_jobs')

    def get_jobs_to_monitor(self) -> List[Job]:
        """
        Get a list of the jobs currently needing monitoring.

        This will likely be something akin to "active" jobs, but the particular conditions should be documented for each
        implementation.

        Returns
        -------
        List[Job]
            A list of the job objects corresponding to executing jobs within the runtime that need to be monitored.
        """
        active_jobs = []
        for active_job_redis_key in self.redis.smembers(self._active_jobs_set_key):
            # If key exists
            if self.redis.exists(active_job_redis_key) == 1:
                serialized_job = json.loads(self.redis.get(active_job_redis_key))
                job = Job.factory_init_from_deserialized_json(serialized_job)
                if isinstance(job, Job):
                    active_jobs.append(job)
        return active_jobs


class RedisDockerSwarmMonitor(DockerSwarmMonitor, RedisBackedMonitor):
    """
    Concrete subtype of both ::class:`DockerSwarmMonitor` and ::class:`RedisBackedMonitor`.

    Concrete ::class:`Monitor` implementation inheriting from ::class:`DockerSwarmMonitor` (for runtime interaction and
    monitoring logic) and ::class:`RedisBackedMonitor` (for job monitoring eligibility/filtering logic).
    """

    def __init__(
        self,
        resource_pool: str,
        docker_client: Optional[docker.DockerClient] = None,
        api_client: Optional[docker.APIClient] = None,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_pass: Optional[str] = None,
        **kwargs
    ):
        DockerSwarmMonitor.__init__(self, docker_client, api_client)
        RedisBackedMonitor.__init__(
            self,
            resource_pool=resource_pool,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_pass=redis_pass,
            **kwargs
        )
