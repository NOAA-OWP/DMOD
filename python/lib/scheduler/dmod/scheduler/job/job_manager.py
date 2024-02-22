import uuid
from abc import ABC, abstractmethod
from asyncio import sleep
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4 as random_uuid
from dmod.core.execution import AllocationParadigm
from dmod.core.serializable import BasicResultIndicator
from dmod.communication.maas_request.dmod_job_request import DmodJobRequest
from .job import Job, JobExecPhase, JobExecStep, JobStatus, RequestedJob
from .job_util import JobUtil, RedisBackedJobUtil
from ..resources.resource_allocation import ResourceAllocation
from ..resources.resource_manager import ResourceManager
from ..scheduler import Launcher

from dmod.communication import SchedulerRequestMessage

import datetime
import heapq

import logging


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


class JobManager(JobUtil, ABC):
    """
    Abstract utility class for complete management of job objects, including allocations and scheduling.

    Another abstract utility class, extending from ::class:`JobUtil` to also provide an interface for creating and
    deleting jobs, job resource allocation, and job execution management and scheduling.
    """

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
    def create_job(self, request: DmodJobRequest, *args, **kwargs) -> Job:
        """
        Create and return a new job object.

        Implementations will vary, but they should all directly or indirectly (i.e., nested as attributes of some other
        object) provide the following parameters within keyword args.

            ``cpu_count`` - A count of CPUs for the job (``int``).
            ``memory_size`` - A size of memory needed for the job (``int``).
            ``parameters`` - A dictionary of job config parameters (``dict``).

        Parameters
        ----------
        request : DmodJobRequest
            The originating request for the job.
        args
            Other optional positional arguments
        kwargs
            Other optional keyword arguments.

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
    async def manage_job_processing(self):
        """
        Monitor for created jobs and perform steps for job queueing, allocation of resources, and hand-off to scheduler.
        """
        pass

    @abstractmethod
    def release_allocations(self, job_ref: Union[str, Job]) -> BasicResultIndicator:
        """
        Release any resource allocations held by the referenced job back to the resource manager.

        Not all jobs are eligible to release resources.  This is a property of the job itself and is accessible via
        ::method:`Job.should_release_resources`.

        Assuming a job is eligible, release will be considered successful even if there are no allocations (i.e., so
        long as the job is eligible and has no resources when the method returns).

        Parameters
        ----------
        job_ref: Union[str, Job]
            A direct or indirect reference to the job from which to release resources.

        Returns
        ----------
        BasicResultIndicator
            An indicator and details of whether resources were released.
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

    # TODO: (later) once pausing is supported, expand this to paused jobs
    @abstractmethod
    def request_restart(self, job_id: str) -> BasicResultIndicator:
        """
        Request a stopped job be restarted by the scheduler.

        Parameters
        ----------
        job_id : str
            The identifier of the job in question.

        Returns
        -------
        BasicResultIndicator
            Indicator and details of whether job was previously in ``STOPPED`` status step and is now in
            ``AWAITING_SCHEDULING`` step.
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

    # TODO: (later) consider stopping/pausing from states other than RUNNING (probably requires tracking state history)
    @abstractmethod
    def request_stop(self, job_id: str) -> BasicResultIndicator:
        """
        Request a running job be stopped by the scheduler.

        Parameters
        ----------
        job_id : str
            The identifier of the job in question.

        Returns
        -------
        BasicResultIndicator
            Indicator and details of whether the job was previously running and is now stopped.
        """
        pass


# TODO: properly account upstream for allocations for finished jobs (or any jobs being deleted) getting cleaned up,
#   since this type isn't responsible for that.
class RedisBackedJobManager(JobManager, RedisBackedJobUtil):
    """
    Implementation of ::class:`JobManager` with a Redis backend.

    An implementation of ::class:`JobManager` that extends ::class:`RedisBackedJobUtil`, thus having a Redis backend.
    The type works with ::class:`RequestedJob` job objects and acquires ::class:`ResourceAllocation` objects for
    processing jobs from some ::class:`ResourceManager`.  It also has a ::class:`Launcher` attribute to enable job
    scheduling and execution.
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

    def __init__(self, resource_manager : ResourceManager, launcher: Launcher, redis_host: Optional[str] = None,
                 redis_port: Optional[int] = None, redis_pass: Optional[str] = None, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
        resource_manager : ResourceManager
            The resource manager from which ::class:`ResourceAllocations` for managed jobs can be obtained.
        launcher : Launcher
            The launcher used for job execution.
        redis_host : Optional[str]
            Optional explicit string init param for the Redis connection host value.
        redis_port : Optional[str]
            Optional explicit string init param for the Redis connection port value.
        redis_pass : Optional[str]
            Optional explicit string init param for the Redis connection password value.
        kwargs
            Keyword args, passed through to the ::class:`RedisBackedJobUtil` superclass init function.
        """
        super().__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass, **kwargs)
        self._resource_manager = resource_manager
        self._launcher = launcher

    def _organize_active_jobs(self, active_jobs: List[RequestedJob]) -> List[List[RequestedJob]]:
        """
        Organize active jobs into collections ready to prepare for certain next-steps in processing.

        Organize the given list of active jobs into collections ready for certain specific next-steps in their
        processing, potentially with some housekeeping performed (i.e. side effects).

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
            # Transition newly created to their first appropriate phase and step
            if job.status_phase == JobExecPhase.INIT:
                # TODO: revisit this for JobCategory (remember right now this is the only way AWAITING_DATA_CHECK is entered, via default step)
                job.status = JobStatus(phase=JobExecPhase.MODEL_EXEC)
                self.save_job(job)
            # Skip jobs awaiting data check handled by the data service, or partitioning handled by partitioning service
            if job.status_step == JobExecStep.AWAITING_DATA_CHECK or job.status_step == JobExecStep.AWAITING_PARTITIONING:
                continue

            # TODO: figure out for STOPPED and FAILED if there are implications that require maintaining the same allocation
            # TODO: figure out for FAILED if restart should be automatic or should require manual request to restart
            # Note that this code should be safe as is as long as the job itself still has the previous allocation saved
            # in situations when it needs to use the same allocation as before
            if job.status_step == JobExecStep.STOPPED:
                job.status_step = JobExecStep.AWAITING_ALLOCATION
                # TODO: calculate impact on priority
                self.save_job(job)

            # TODO: figure out for FAILED if restart should be automatic or should require manual request to restart
            # For now, assume failure requires manual re-transition
            #if job.status_step == JobExecStep.FAILED

            if job.status_step == JobExecStep.AWAITING_ALLOCATION:
                # Add to collection, though make sure it doesn't already have an allocation
                if job.allocations is None or len(job.allocations) == 0:
                    jobs_eligible_for_allocate.append(job)
                # If it does have an allocation, update its status
                else:
                    # TODO: confirm the allocation is still valid (saving it without checking will make it so, which
                    #  could lead to inconsistencies)
                    job.status_step = JobExecStep.AWAITING_DATA
                    self.save_job(job)

            if job.should_release_resources:
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

    def create_job(self, request: SchedulerRequestMessage, *args, **kwargs) -> RequestedJob:
        """
        Create and return a new job object that has been saved to the backend store.

        Since this class works with ::class:`RequestedJob` objects, a new object must receive a
        ::class:`SchedulerRequestMessage` as a parameter.  This is in the ``request`` keyword arg.

        Parameters
        ------------
        request : SchedulerRequestMessage
            The originating request for the job.
        args
            Other optional positional arguments
        kwargs
            Other optional keyword arguments.

        Other Parameters
        ------------
        job_id : Union[str, UUID]
            Optional value to try use for the job's id, falling back to random if not present, invalid, or already used.

        Returns
        -------
        RequestedJob
            The newly created job object.
        """
        job_obj = RequestedJob.factory_init_from_request(job_request=request)
        # TODO: do some processing here or in the object init to build restrictions and constraints that make sense globally;
        #  i.e., make sure the requirements for forcings satisfy the necessary hydrofabric if the config doesn't include a specific subset explicitly
        uuid_param = kwargs.get('job_id', random_uuid())
        try:
            job_uuid = uuid_param if isinstance(uuid_param, UUID) else UUID(str(uuid_param))
        except:
            job_uuid = random_uuid()

        while self._does_redis_key_exist(self._get_job_key_for_id(job_uuid)):
            job_uuid = random_uuid()

        job_obj.set_job_id(job_uuid)
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
        logging.debug("Deleting job {}".format(job_id))
        # Retrieve the job and ensure any allocations are release
        job_key = self._get_job_key_for_id(job_id)
        job_obj = self.retrieve_job_by_redis_key(job_key)

        # Ensure allocations are released
        self.release_allocations(job_id)

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

    # TODO: (later) once pausing is supported, expand this to paused jobs
    def request_restart(self, job_id: str) -> BasicResultIndicator:
        """
        Request a stopped job be restarted by the scheduler.

        Note that this is a "safe" operation with respect to system-wide conflicts on job state changes.  I.e., only a
        ``STOPPED`` job will be updated, and a ``STOPPED`` job is not of interest to any other services, so no
        inconsistent simultaneous save operations are possible across the deployment.

        Parameters
        ----------
        job_id : str
            The identifier of the job in question.

        Returns
        -------
        BasicResultIndicator
            Indicator and details of whether job was previously in the ``STOPPED`` status step and is now in the `
            `AWAITING_SCHEDULING`` step.
        """
        job = self.retrieve_job(job_id)
        if job.status_step != JobExecStep.STOPPED:
            return BasicResultIndicator(success=False, reason="Invalid Status Step For Restart",
                                        message=f"{JobExecStep.STOPPED!s} required, but job was {job.status_step!s}.")
        else:
            job.set_status_step(JobExecStep.AWAITING_SCHEDULING)
            self.save_job(job)
            return BasicResultIndicator(success=True, reason="Job Restarted")

    def request_scheduling(self, job: RequestedJob) -> Tuple[bool, tuple]:
        """
            TODO rename this function, by the time we get here, we are already scheduled, just need to run
        """
        # TODO: make sure there aren't other cases
        if job.status_step == JobExecStep.AWAITING_SCHEDULING:
            try: #If we don't catch excpetions from the launcher, they get handled "somewhere" that causes the
                 #connection to close, but no useful information is provided, so handle them here.
                return self._launcher.start_job(job)
            except Exception as e:
                logging.error("launcher failed to start job")
                logging.exception(e)
                return False, (e,)
        logging.debug("Failed to start job")
        return False, ()

    def request_stop(self, job_id: str) -> BasicResultIndicator:
        """
        Request a running job be stopped by the scheduler.

        Note that this is a "safe" operation with respect to system-wide conflicts on job state changes.  I.e., only a
        ``RUNNING`` job will be updated, and a ``RUNNING`` job is not of interest to any other services, so no
        inconsistent simultaneous save operations are possible across the deployment.

        Parameters
        ----------
        job_id : str
            The identifier of the job in question.

        Returns
        -------
        BasicResultIndicator
            Indicator and details of whether the job was previously running and is now ``STOPPING`` (but not necessarily
            ``STOPPED``).
        """
        job = self.retrieve_job(job_id)
        if job.status_step != JobExecStep.RUNNING:
            return BasicResultIndicator(success=False, reason="Invalid Status Step For Stop",
                                        message=f"{JobExecStep.RUNNING!s} required, but job was {job.status_step!s}.")
        else:
            job.set_status_step(JobExecStep.STOPPING)
            self.save_job(job)
            return BasicResultIndicator(success=True, reason="Job Stopping")

    async def manage_job_processing(self):
        """
        Monitor for created jobs and perform steps for job queueing, allocation of resources, and hand-off to scheduler.
        """
        logging.debug("Starting job management async task")
        while True:
            logging.info("Starting next iteration of job manager async task")

            # TODO: do this better
            lock_id = str(uuid.uuid4())
            while not self.lock_active_jobs(lock_id):
                await sleep(2)

            # Get collection of "active" jobs
            active_jobs: List[RequestedJob] = self.get_all_active_jobs()

            # Prioritize stopping and handle separately for clarity
            for job in [j for j in active_jobs if j.status_step == JobExecStep.STOPPING]:
                try:
                    # Should be the case that this blocks until stopping is done
                    self._launcher.stop_job(job=job)
                    job.set_status_step(JobExecStep.STOPPED)
                except Exception as e:
                    logging.error(f"Service failed to stop job {job.job_id} due to {e.__class__.__name__} ({e!s}).")
                    job.set_status_step(JobExecStep.FAILED)
                self.save_job(job)

            for j in active_jobs:
                if j.status_step.is_error:
                    logging.error("Requested job {} has failed due to {}".format(j.job_id, j.status_step.name))
                if j.status_step.completes_phase:
                    active_jobs.remove(j)
                    self.save_job(j)

            # TODO: something must transition MODEL_EXEC_RUNNING Jobs to MODEL_EXEC_COMPLETED (probably Monitor class)
            # TODO: something must transition OUTPUT_EXEC_RUNNING Jobs to OUTPUT_EXEC_COMPLETED (probably Monitor class)

            # Process the jobs into various organized collections
            organized_lists = self._organize_active_jobs(active_jobs)
            jobs_eligible_for_allocate = organized_lists[0]
            jobs_to_release_resources = organized_lists[1]
            jobs_completed_phase = organized_lists[2]

            for job_with_allocations_to_release in jobs_to_release_resources:
                result = self.release_allocations(job_with_allocations_to_release.job_id)
                if not result.success:
                    logging.error(f"Failure deallocating {job_with_allocations_to_release.job_id} due to "
                                  f"'{result.reason}' (message was: `{result.message}`)")

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

            # TODO: have data management service handle the AWAITING_DATA step so it can transition to the AWAITING_SCHEDULING step

            # For each Job that is at the AWAITING_SCHEDULING, save updated state and pass to scheduler
            for job in [j for j in active_jobs if j.status_step == JobExecStep.AWAITING_SCHEDULING]:
                scheduling_result: Tuple[bool, tuple] = self.request_scheduling(job)
                if scheduling_result[0]:
                    job.status_step = JobExecStep.SCHEDULED
                else:
                    job.status_step = JobExecStep.FAILED
                    # TODO: probably log something about this, or raise exception
                self.save_job(job)

            self.unlock_active_jobs(lock_id)
            await sleep(5)

    def release_allocations(self, job_ref: Union[str, Job]) -> BasicResultIndicator:
        """
        If permitted, release any resource allocations held by the referenced job back to the resource manager.

        If the referenced job is eligible, release any resource allocations it holds back to the resource manager and
        update the job to unset the allocations.  When such release is performed, the backing state maintained by the
        job manager is updated, as is the value of the `job_ref` parameter if it is a :class:`Job` object.

        Not all jobs are eligible to release resources.  This is a property of the job itself and is accessible via the
        :class:`Job`'s ``should_release_resources`` function.

        Assuming a job is eligible, release will be considered successful even if there are no allocations (i.e., so
        long as the job is eligible and has no resources when the method returns).

        Parameters
        ----------
        job_ref: Union[str, Job]
            A direct or indirect reference to the job from which to release resources.

        Returns
        ----------
        BasicResultIndicator
            An indicator and details of whether resources were released.
        """
        job = job_ref if isinstance(job_ref, Job) else self.retrieve_job(job_id=job_ref)

        if not job.should_release_resources:
            return BasicResultIndicator(success=False, reason="Not Eligible",
                                        message=f"Can't release resources for job with status {job.status!s}.")
        elif job.allocations is not None and len(job.allocations) > 0:
            self._resource_manager.release_resources(job.allocations)
        job.allocations = None
        self.save_job(job)
        return BasicResultIndicator(success=True, reason="Release Successful")

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
        if job.allocation_paradigm == AllocationParadigm.SINGLE_NODE:
            alloc = self._resource_manager.allocate_single_node(job.cpu_count, job.memory_size)
        elif job.allocation_paradigm == AllocationParadigm.FILL_NODES:
            alloc = self._resource_manager.allocate_fill_nodes(job.cpu_count, job.memory_size)
        elif job.allocation_paradigm == AllocationParadigm.ROUND_ROBIN:
            alloc = self._resource_manager.allocate_round_robin(job.cpu_count, job.memory_size)
        else:
            alloc = [None]
        if isinstance(alloc, list) and len(alloc) > 0 and isinstance(alloc[0], ResourceAllocation):
            job.allocations = alloc
            job.status_step = JobExecStep.AWAITING_DATA
            return True
        else:
            return False
