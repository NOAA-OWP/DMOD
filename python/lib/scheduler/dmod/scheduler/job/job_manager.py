from abc import ABC, abstractmethod
from asyncio import sleep
from typing import Dict, Iterable, List, Optional, Tuple, Union
from uuid import UUID, uuid4 as random_uuid
from .job import Job, JobAllocationParadigm, JobExecStep, JobStatus, RequestedJob
from ..resources.resource_allocation import ResourceAllocation
from ..resources.resource_manager import ResourceManager
from ..rsa_key_pair import RsaKeyPair
from ..scheduler import Launcher

from dmod.communication import MaaSRequest, NWMRequest, SchedulerRequestMessage
from dmod.redis import KeyNameHelper, RedisBacked

import datetime
import heapq
import json


class JobManagerFactory:
    """
    A basic concrete implementation of a factory for obtaining ::class:`JobManager` instances.

    The intent is for this to be exposed, along with interface class, but have implementations of ::class:`JobManager`
    be essentially obscured.  To support externally created implementations, this factory class can itself be extended.

    This default implementation is only aware of one particular concrete type that uses a Redis backend, so it will
    always return an instance of that type.  The supported keyword args are documented in the method.
    """

    @classmethod
    def factory_create(cls, resource_manager: ResourceManager, launcher: Launcher, **kwargs):
        """
        Create and return a new instance of a ::class:`JobManager` object.

        In this default method implementation, only a single, Redis-backed type is available.  The method supports
        receiving keyword args to provide non-default values for the host, port, and password parameters for the Redis
        server connection.

        Keyword Args
        ----------
        redis_host : str
            The Redis service host name.
        redis_port : int
            The Redis service port.
        redis_pass : str
            The Redis service auth password.

        Returns
        -------
        JobManager
            A newly created ::class:`JobManager` object.
        """
        host = None
        port = None
        pword = None
        for key, value in kwargs.items():
            if key == 'redis_host':
                host = value
            elif key == 'redis_port':
                port = int(value)
            elif key == 'redis_pass':
                pword = value
        return RedisBackedJobManager(resource_manager=resource_manager, launcher=launcher, redis_host=host, redis_port=port,
                                     redis_pass=pword)


class JobManager(ABC):

    @classmethod
    @abstractmethod
    def build_prioritized_pending_allocation_queues(cls, jobs_eligible_for_allocate: List[RequestedJob]) -> Union[
            List[Tuple[int, RequestedJob]], Dict[str, List[Tuple[int, RequestedJob]]]]:
        """
        Construct one or more priority queues for the given jobs eligible to receive allocations, based on the jobs'
        ::attribute:`Job.allocation_priority` values, returning either the single priority queue or a keyed dictionary
        of queues.

        Implementations can decided whether a single or multiple queues should be produced, but they should clearly
        document which is the case.  Also, if multiple queues are returned, the distinction between the queues and how
        they are keyed should be clearly documented.

        Implementations must return Python Lib/heapq.py type priority queues. Note that because this implementation is a
        "min heap" (i.e. return smallest item first), jobs must first be wrapped inside a tuple before being added to
        a queue.  The first value in one of these tuples should be the additive inverse of the job's
        ::attribute:`Job.allocation_priority` value, with the job object itself being the second value.

        In cases multiple queues within a dictionary are returned, implemenations must ensure that each job within the
        parameter list is included in exactly one queue.  I.e., the sum of the length of all returned queues must be
        equal to the length of the provided argument list.

        Parameters
        ----------
        jobs_eligible_for_allocate : List[RequestedJob]
            A list of ::class:`RequestedJob` object, where each is eligible for allocation.

        Returns
        -------
        Dict[str, List[Tuple[int, RequestedJob]]]
            A mapping of high, medium, and low priority queues filled with tuples having the additive inverse of a job's
            priority and the respective job object.
        """
        pass

    @abstractmethod
    def create_job(self, **kwargs) -> Job:
        """
        Create and return a new job object.

        Implementations will vary, but they should all directly or indirectly (i.e., nested as attributes of some other
        object) provide the following parameters within keyword args.

            ``cpu_count`` - A count of CPUs for the job (``int``).
            ``memory_size`` - A size of memory needed for the job (``int``).
            ``parameters`` - A dictionary of job config parameters (``dict``).

        Parameters
        ----------
        kwargs
            Other appropriate, implementation-specific keyed parameters supported for creating the job object.

        Returns
        -------
        Job
            The newly created job object.
        """
        pass

    @abstractmethod
    def delete_job(self, job_id) -> bool:
        """
        Delete the job record for the job with the given id value.

        Parameters
        ----------
        job_id
            The unique id for a job of interest to delete.

        Returns
        -------
        bool
            ``True`` if a record was successfully deleted, otherwise ``False``.
        """
        pass

    @abstractmethod
    def does_job_exist(self, job_id) -> bool:
        """
        Test whether a job with the given job id exists.

        Parameters
        ----------
        job_id
            The job id of interest.

        Returns
        -------
        bool
            ``True`` if a job exists with the provided job id, or ``False`` otherwise.
        """
        pass

    @abstractmethod
    def get_all_active_jobs(self) -> List[Job]:
        """
        Get a list of every job known to this manager object that is considered active based on each job's status.

        Returns
        -------
        List[Job]
            A list of every job known to this manager object that is considered active based on each job's status.
        """
        pass

    @abstractmethod
    async def manage_job_processing(self):
        """
        Monitor for created jobs and perform steps for job queueing, allocation of resources, and hand-off to scheduler.
        """
        pass

    @abstractmethod
    def release_allocations(self, job: Job):
        """
        Release any resource allocations held by the given job back to the resource manager.

        Parameters
        ----------
        job : Job
            The job for which any held allocations should be released.
        """
        pass

    @abstractmethod
    def request_allocations(self, job: Job, require_awaiting_status: bool = True) -> bool:
        """
        Request required resource allocation(s) from resource manager, if sufficient resources are currently available,
        assigning successfully obtained allocations to the given job.

        By default, the job must be in the appropriate status indicating it is awaiting allocation in order to have
        an attempt made to get resources, although this can be overridden.  The method will return ``False`` otherwise
        if the job does not have an appropriate status.

        However, this function does not alter the status property of the job.

        Parameters
        ----------
        job : Job
            The job requiring resource allocation(s).
        require_awaiting_status : bool
            Whether a job must have a valid job status (i.e., with execution step ``AWAITING_ALLOCATION``) to have
            allocations requested, which is ``True`` by default.

        Returns
        -------
        bool
            Whether an allocation was successfully requested, received, and assigned to the job object.
        """
        pass

    @abstractmethod
    def request_scheduling(self, job: Job) -> bool:
        """
        Request a job be passed sent to the scheduler and scheduled for execution.

        Parameters
        ----------
        job : Job
            The job in question.

        Returns
        -------
        bool
            Whether the job was scheduled.
        """
        pass

    @abstractmethod
    def retrieve_job(self, job_id) -> Job:
        """
        Get the particular job with the given unique id.

        Method will raise a ::class:`ValueError` if called using a job id that does not correspond to an existing job.
        Users of the method should either catch this error or test job ids for existence first with the
        ::method:`does_job_exist` method.

        Parameters
        ----------
        job_id
            The unique id of the desired job.

        Returns
        -------
        Job
            The particular job with the given unique id.

        Raises
        -------
        ValueError
            If no job exists with given job id.
        """
        pass

    @abstractmethod
    def save_job(self, job: Job):
        """
        Add or update the given job object in this manager's backend data store of job record data.

        Parameters
        ----------
        job
            The job to be updated or added.
        """
        pass


# TODO: properly account upstream for allocations for finished jobs (or any jobs being deleted) getting cleaned up,
#   since this type isn't responsible for that.
class RedisBackedJobManager(JobManager, RedisBacked):
    """
    An implementation of ::class:`JobManager` that uses Redis as a backend, works with ::class:`RequestedJob` job
    objects, and acquires ::class:`ResourceAllocation` objects for processing jobs from some ::class:`ResourceManager`.
    """

    @classmethod
    def build_prioritized_pending_allocation_queues(cls, jobs_eligible_for_allocate: List[RequestedJob]) -> Dict[
            str, List[Tuple[int, RequestedJob]]]:
        """
        Construct priority queues for the given jobs eligible to receive allocations, based on the jobs'
        ::attribute:`Job.allocation_priority` values, and return a keyed dictionary of the resulting queues.

        In this implementation, three priority queues are returned within a dictionary, keyed as ``high``, ``medium``,
        and ``low``.

        The ``high`` queue consists of jobs with priority values over 100.

        The ``medium`` queue consists of jobs with priority values between 50 and 100 inclusive.

        The ``low`` queue consists of jobs with priorities under 50.

        Note that because the priority queue implementation is a "min heap" (i.e. return smallest item first), jobs are
        first wrapped inside a tuple before being added to the appropriate priority queue, with the first value being
        the additive inverse of the job's ::attribute:`Job.allocation_priority` value, and the second being the job
        object itself.

        Parameters
        ----------
        jobs_eligible_for_allocate : List[RequestedJob]
            A list of ::class:`RequestedJob` object, where each is eligible for allocation.

        Returns
        -------
        Dict[str, List[Tuple[int, RequestedJob]]]
            A mapping of high, medium, and low priority queues filled with tuples having the additive inverse of a job's
            priority and the respective job object.
        """
        # Build prioritized list/queue of allocation eligible Jobs
        low_priority_queue = []
        med_priority_queue = []
        high_priority_queue = []
        for eligible_job in jobs_eligible_for_allocate:
            # Bump by 10 if not updated for an hour
            if datetime.datetime.now() - eligible_job.last_updated >= datetime.timedelta(hours=1):
                eligible_job.allocation_priority = eligible_job.allocation_priority + 10
            # TODO: formalize this scale better
            # Over 100: high
            # 50 to 100: med
            # otherwise: low
            priority = eligible_job.allocation_priority
            # Also keep in mind that higher priority is first, which is reversed from priority queue (so negate)
            inverted_priority = priority * -1
            if priority > 100:
                heapq.heappush(high_priority_queue, (inverted_priority, eligible_job))
            elif priority > 49:
                heapq.heappush(med_priority_queue, (inverted_priority, eligible_job))
            else:
                heapq.heappush(low_priority_queue, (inverted_priority, eligible_job))
        return {'high': high_priority_queue, 'medium': med_priority_queue, 'low': low_priority_queue}

    # TODO: look at either deprecating this or applying it appropriately to all managed objects
    @classmethod
    def get_key_prefix(cls, environment_type: str = 'prod'):
        parsed_type = environment_type.strip().lower()
        if parsed_type == 'test' or parsed_type == 'dev' or parsed_type == 'local':
            return parsed_type + '_job_mgr'
        else:
            return 'job_mgr'

    def __init__(self, resource_manager : ResourceManager, launcher: Launcher, redis_host: Optional[str] = None,
                 redis_port: Optional[int] = None, redis_pass: Optional[str] = None, **kwargs):
        """

        Parameters
        ----------
        resource_manager : ResourceManager
            The resource manager from which ::class:`ResourceAllocations` for managed jobs can be obtained.
        redis_host : Optional[str]
            Optional explicit string init param for the Redis connection host value.
        redis_port : Optional[str]
            Optional explicit string init param for the Redis connection port value.
        redis_pass : Optional[str]
            Optional explicit string init param for the Redis connection password value.
        kwargs
            Keyword args, passed through to the ::class:`RedisBacked` superclass init function.
        """
        super().__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass, **kwargs)
        self._resource_manager = resource_manager
        if 'type' in kwargs:
            key_prefix = self.get_key_prefix(environment_type=kwargs['type'])
        else:
            key_prefix = self.get_key_prefix()
        self._active_jobs_set_key = self.keynamehelper.create_key_name(key_prefix, 'active_jobs')
        self._launcher = launcher

    def _dev_setup(self):
        self._clean_keys()
        self.keynamehelper = 'dev' + KeyNameHelper.get_default_separator() + self.get_key_prefix()

    def _does_redis_key_exist(self, redis_key: str) -> bool:
        """
        Test whether a record with the given Redis key exists.

        Works by making an ``EXISTS`` API call for the appropriate key, and seeing if the result of the call is ``1``,
        per the API spec.

        Parameters
        ----------
        redis_key
            The Redis key of interest.

        Returns
        -------
        bool
            ``True`` if a record exists with the provided key, or ``False`` otherwise.
        """
        return self.redis.exists(redis_key) == 1

    def _get_job_key_for_id(self, job_id) -> str:
        """
        Get the appropriate Redis key for accessing the manager's record of the job with the given id.

        Parameters
        ----------
        job_id
            The id of the job of interest.

        Returns
        -------
        str
            The appropriate Redis key for accessing the manager's record of the job with the given id.
        """
        return self.create_key_name('job', str(job_id))

    def _organize_active_jobs(self, active_jobs: List[RequestedJob]) -> List[List[RequestedJob]]:
        """
        Organize the given list of active jobs into collections ready for various next-steps in their processing,
        potentially with some housekeeping performed (i.e. side effects).

        In some cases, job status may be changed (e.g., ``CREATED`` to ``MODEL_EXEC_AWAITING_ALLOCATION``).  In those
        cases and a few other situations, the updated job object will have its state re-saved using ::method:`save_job`.

        Parameters
        ----------
        active_jobs : List[RequestedJob]
            A list of ::class:`RequestedJob` objects with active statuses.

        Returns
        -------
        List[List[RequestedJob]]
            A list of lists of jobs indexed as follows:
                * index ``0``: jobs eligible for allocation
                * index ``1``: jobs to have their resource allocations released
                * index ``2``: jobs that have completed their current phase
        """
        jobs_eligible_for_allocate = []
        jobs_to_release_resources = []
        jobs_completed_phase = []

        for job in active_jobs:
            # Transition CREATED to awaiting allocation as a first step for them
            if job.status == JobStatus.CREATED:
                job.status = JobStatus.MODEL_EXEC_AWAITING_ALLOCATION
                self.save_job(job)
            # TODO: figure out for STOPPED and FAILED if there are implications that require maintaining the same allocation
            # Note that this code should be safe as is as long as the job itself still has the previous allocation saved
            # in situations when it needs to use the same allocation as before
            if job.status_step == JobExecStep.STOPPED:
                job.status_step = JobExecStep.AWAITING_ALLOCATION
                # TODO: calculate impact on priority
                self.save_job(job)

            # TODO: figure out for FAILED if restart should be automatic or should require manual request to restart
            # For now, assume failure requires manual re-transition
            #if job.status_step == JobExecStep.FAILED

            if job.status_step.AWAITING_ALLOCATION:
                # Add to collection, though make sure it doesn't already have an allocation
                if job.allocations is None or len(job.allocations) == 0:
                    jobs_eligible_for_allocate.append(job)
                # If it does have an allocation, update its status
                else:
                    # TODO: confirm the allocation is still valid (saving it without checking will make it so, which
                    #  could lead to inconsistencies)
                    job.status_step = JobExecStep.ALLOCATED
                    self.save_job(job)

            if job.status.should_release_allocations:
                jobs_to_release_resources.append(job)

            if job.status_step == JobExecStep.COMPLETED:
                jobs_completed_phase.append(job)

        return [jobs_eligible_for_allocate, jobs_to_release_resources, jobs_completed_phase]

    def _request_allocations_for_queue(self, jobs_priority_queue: List[Tuple[int, RequestedJob]]) -> List[RequestedJob]:
        """
        Request allocations for all jobs in a provided priority queue, updating and saving in Redis any jobs that did
        get the requested allocation, and returning a list of those successfully allocated jobs.

        Parameters
        ----------
        jobs_priority_queue : List[Tuple[int, RequestedJob]]
            A priority queue (implemented as a list) of jobs for which allocation requests should be made, with items
            being tuples of priority value additive inverses and requested jobs.

        Returns
        -------
        List[RequestedJob]
            A list of the job objects that received their requested allocations.

        """
        allocated_successfully = []
        not_allocated = []
        priorities_to_bump = []
        while len(jobs_priority_queue) > 0:
            # Remember, the job object itself is the second item in the popped tuple, since this is a min heap
            job = heapq.heappop(jobs_priority_queue)[1]
            was_allocated = self.request_allocations(job)
            # If the allocation was successful
            if was_allocated:
                allocated_successfully.append(job)
                self.save_job(job)
                # Keep track of jobs that got skipped over by at least one lower priority job like this
                # Simplest thing is to clear an rebuild list with anything "not allocated" that came before this
                priorities_to_bump = []
                for j in not_allocated:
                    priorities_to_bump.append(j)
            else:
                not_allocated.append(job)
        # Then at the end, bump priorities for skipped
        for j in priorities_to_bump:
            j.allocation_priority = j.allocation_priority + 1
            self.save_job(j)
        return allocated_successfully

    def create_job(self, **kwargs) -> RequestedJob:
        """
        Create and return a new job object that has been saved to the backend store.

        Since this class works with ::class:`RequestedJob` objects, a new object must receive a
        ::class:`SchedulerRequestMessage` as a parameter.  This is in the ``request`` keyword arg.

        Parameters
        ----------
        kwargs
            Implementation-specific keyed parameters for creating appropriate job objects (see *Keyword Args* section).

        Keyword Args
        ------------
        request : SchedulerRequestMessage
            The originating request for the job.
        job_id : str, UUID, None
            Optional value to try use for the job's id, falling back to random if not present, invalid, or already used.

        Returns
        -------
        RequestedJob
            The newly created job object.
        """
        job_obj = RequestedJob(job_request=kwargs['request'])
        try:
            job_uuid = kwargs['job_id'] if isinstance(kwargs['job_id'], UUID) else UUID(str(kwargs['job_id']))
            if not self._does_redis_key_exist(self._get_job_key_for_id(job_uuid)):
                job_obj.job_id = job_uuid
            else:
                job_obj.job_id = random_uuid()
        except:
            job_obj.job_id = random_uuid()

        self.save_job(job_obj)
        return job_obj

    def delete_job(self, job_id) -> bool:
        """
        Delete the job record for the job with the given id value.

        Note that this deletes all the serialized records for the job in Redis, except for the resource allocations,
        which are handled separately by a resource manager.  This method assumes that gets handled appropriately on its
        own.

        Parameters
        ----------
        job_id
            The unique id for a job of interest to delete.

        Returns
        -------
        bool
            ``True`` if a record was successfully deleted, or ``False`` if the backing record could not be deleted after
            multiple attempts.

        Raises
        -------
        ValueError
            If no job exists with given job id.
        """
        # Retrieve the job and ensure any allocations are release
        job_key = self._get_job_key_for_id(job_id)
        job_obj = self.retrieve_job_by_redis_key(job_key)

        # Ensure allocations are released
        self.release_allocations(job_obj)

        i = 0
        while i < 5:
            i += 1
            with self.redis.pipeline() as pipeline:
                if job_obj.status.is_active:
                    # Make sure not in active set
                    pipeline.srem(self._active_jobs_set_key, job_key)
                pipeline.delete(job_key)
                pipeline.execute()
                # Try to do this, but don't fully fail just for this part
                try:
                    job_obj.rsa_key_pair.delete_key_files()
                except:
                    # TODO: look at at least logging something if this happens; for now ...
                    pass
                return True
        # If we get here, it means we failed the max allowed times, so bail
        return False

    def does_job_exist(self, job_id) -> bool:
        """
        Test whether a job with the given job id exists.

        Parameters
        ----------
        job_id
            The job id of interest.

        Returns
        -------
        bool
            ``True`` if a job exists with the provided job id, or ``False`` otherwise.
        """
        return self._does_redis_key_exist(self._get_job_key_for_id(job_id))

    def get_all_active_jobs(self) -> List[RequestedJob]:
        """
        Get a list of every job known to this manager object that is considered active based on each job's status.

        Returns
        -------
        List[RequestedJob]
            A list of every job known to this manager object that is considered active based on each job's status.
        """
        active_jobs = []
        for active_job_redis_key in self.redis.smembers(self._active_jobs_set_key):
            active_jobs.append(self.retrieve_job_by_redis_key(active_job_redis_key))
        return active_jobs

    def request_scheduling(self, job: RequestedJob):
        """
            TODO rename this function, by the time we get here, we are already scheduled, just need to run
        """
        # TODO: make sure there aren't other cases
        if job.status_step == JobExecStep.ALLOCATED:
            return self._launcher.start_job(job)

    async def manage_job_processing(self):
        """
        Monitor for created jobs and perform steps for job queueing, allocation of resources, and hand-off to scheduler.
        """
        while True:
            # Get collection of "active" jobs
            active_jobs: List[RequestedJob] = self.get_all_active_jobs()

            # TODO: something must transition MODEL_EXEC_RUNNING Jobs to MODEL_EXEC_COMPLETED (probably Monitor class)
            # TODO: something must transition OUTPUT_EXEC_RUNNING Jobs to OUTPUT_EXEC_COMPLETED (probably Monitor class)

            # Process the jobs into various organized collections
            organized_lists = self._organize_active_jobs(active_jobs)
            jobs_eligible_for_allocate = organized_lists[0]
            jobs_to_release_resources = organized_lists[1]
            jobs_completed_phase = organized_lists[2]

            for job_with_allocations_to_release in jobs_to_release_resources:
                self.release_allocations(job_with_allocations_to_release)
                self.save_job(job_with_allocations_to_release)

            for job_transitioning_phases in jobs_completed_phase:
                # TODO: figure out what to do here; e.g., start output service after model_exec is done
                pass

            # Build prioritized list/queue of allocation eligible Jobs
            priority_queues = self.build_prioritized_pending_allocation_queues(jobs_eligible_for_allocate)
            high_priority_queue = priority_queues['high']
            # Do this here to get size in case queue is altered below
            initial_high_priority_queue_size = len(high_priority_queue)
            low_priority_queue = priority_queues['low']
            med_priority_queue = priority_queues['medium']

            # Request allocations and get collection of jobs that were allocated, starting first with high priorities
            allocated_successfully = self._request_allocations_for_queue(high_priority_queue)
            # Only even process others if any and all high priority jobs get allocated
            if len(allocated_successfully) == initial_high_priority_queue_size:
                allocated_successfully.extend(self._request_allocations_for_queue(med_priority_queue))
                allocated_successfully.extend(self._request_allocations_for_queue(low_priority_queue))

            # For each Job that received an allocation, save updated state and pass to scheduler
            for job in allocated_successfully:
                if self.request_scheduling(job):
                    job.status_step = JobExecStep.SCHEDULED
                else:
                    job.status_step = JobExecStep.FAILED
                    # TODO: probably log something about this, or raise exception
                self.save_job(job)

            await sleep(60)

    def release_allocations(self, job: Job):
        """
        Release any resource allocations held by the given job back to the resource manager and unset the allocation
        assignment for the object.

        Parameters
        ----------
        job : Job
            The job for which any held allocations should be released.
        """
        if job.allocations is not None and len(job.allocations) > 0:
            self._resource_manager.release_resources(job.allocations)
        job.allocations = None

    def request_allocations(self, job: Job, require_awaiting_status: bool = True) -> bool:
        """
        Request required resource allocation(s) from resource manager, if sufficient resources are currently available,
        assigning successfully obtained allocations to the given job.

        By default, the job must be in the appropriate status indicating it is awaiting allocation in order to have
        an attempt made to get resources, although this can be overridden.  The method will return ``False`` otherwise
        if the job does not have an appropriate status.

        However, this function does not alter the status property of the job.

        Parameters
        ----------
        job : Job
            The job requiring resource allocation(s).
        require_awaiting_status : bool
            Whether a job must have a valid job status (i.e., with execution step ``AWAITING_ALLOCATION``) to have
            allocations requested, which is ``True`` by default.

        Returns
        -------
        bool
            Whether an allocation was successfully requested, received, and assigned to the job object.
        """
        if require_awaiting_status and job.status_step != JobExecStep.AWAITING_ALLOCATION:
            return False
        if job.allocation_paradigm == JobAllocationParadigm.SINGLE_NODE:
            alloc = self._resource_manager.allocate_single_node(job.cpu_count, job.memory_size)
        elif job.allocation_paradigm == JobAllocationParadigm.FILL_NODES:
            alloc = self._resource_manager.allocate_fill_nodes(job.cpu_count, job.memory_size)
        elif job.allocation_paradigm == JobAllocationParadigm.ROUND_ROBIN:
            alloc = self._resource_manager.allocate_round_robin(job.cpu_count, job.memory_size)
        else:
            alloc = [None]
        if isinstance(alloc, list) and len(alloc) > 0 and isinstance(alloc[0], ResourceAllocation):
            job.allocations = alloc
            job.status_step = JobExecStep.ALLOCATED
            return True
        else:
            return False

    def retrieve_job(self, job_id) -> RequestedJob:
        """
        Get the particular job with the given unique id.

        Method will raise a ::class:`ValueError` if called using a job id that does not correspond to an existing job.
        Users of the method should either catch this error or test job ids for existence first with the
        ::method:`does_job_exist` method.

        Parameters
        ----------
        job_id
            The unique id of the desired job.

        Returns
        -------
        RequestedJob
            The particular job with the given unique id.

        Raises
        -------
        ValueError
            If no job exists with given job id.
        """
        return self.retrieve_job_by_redis_key(job_redis_key=self._get_job_key_for_id(job_id))

    def retrieve_job_by_redis_key(self, job_redis_key: str) -> RequestedJob:
        """
        Get the particular job for the given Redis key, which will be based on the id of the job.

        Parameters
        ----------
        job_redis_key : str
            The Redis key for the job's saved record.

        Returns
        -------
        RequestedJob
            The particular job with the given Redis key.

        Raises
        -------
        ValueError
            If no job record exists with given key.
        """
        if self._does_redis_key_exist(job_redis_key):
            serialized_job = json.loads(self.redis.get(job_redis_key))
            return RequestedJob.factory_init_from_deserialized_json(json_obj=serialized_job)
        else:
            raise ValueError('No job record found for job with key {}'.format(job_redis_key))

    def save_job(self, job: RequestedJob):
        """
        Add or update the given job object in this manager's backend data store of job record data, also maintaining a
        Redis set of the ids of 'active' jobs.

        Parameters
        ----------
        job : RequestedJob
            The job to be updated or added.
        """
        job_key = self._get_job_key_for_id(job.job_id)
        serialized_job_str = job.to_json()

        pipeline = self.redis.pipeline()
        try:
            pipeline.set(job_key, serialized_job_str)
            if job.status.is_active:
                # Add to active set
                pipeline.sadd(self._active_jobs_set_key, job_key)
            else:
                # Make sure not in active set
                pipeline.srem(self._active_jobs_set_key, job_key)
            pipeline.execute()
        finally:
            pipeline.reset()
