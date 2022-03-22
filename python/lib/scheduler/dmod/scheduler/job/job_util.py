import json

from .job import Job, RequestedJob
from abc import ABC, abstractmethod
from dmod.redis import KeyNameHelper, RedisBacked
from typing import List, Optional


class DefaultJobUtilFactory:
    """
    A basic, default concrete implementation of a factory for obtaining ::class:`JobUtil` instances.

    The intent is for this to be exposed, along with interface class, but have implementations of ::class:`JobUtil`
    be essentially obscured.  To support externally created implementations, this factory class can itself be extended.

    This default implementation is only aware of one particular concrete type that uses a Redis backend, so it will
    always return an instance of that type.  The supported keyword args are documented in the method.
    """

    @classmethod
    def factory_create(cls, **kwargs):
        """
        Create and return a new instance of a ::class:`JobUtil` object.

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
            A newly created ::class:`JobUtil` object.
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
        return RedisBackedJobUtil(redis_host=host, redis_port=port, redis_pass=pword)


class JobUtil(ABC):
    """
    Abstract utility class for performing basic operations on jobs.

    An abstract utility class that provides an interface for both mutating and non-mutating operations on existing jobs.
    The interface does not include operations for creating or deleting jobs, nor does it deal with scheduling or
    resource allocations.
    """

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
        Get a list of every job known to this object that is considered active based on each job's status.

        Returns
        -------
        List[Job]
            A list of every job known to this util object that is considered active based on each job's status.
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
        Add or update the given job object in the backend data store of job record data.

        Parameters
        ----------
        job
            The job to be updated or added.
        """
        pass


class RedisBackedJobUtil(JobUtil, RedisBacked):
    """
    Implementation of ::class:`JobUtil` with a Redis backend.

    An implementation of both ::class:`JobUtil` and ::class:`RedisBacked`, thereby being a job util type with a Redis
    backend for job record storage.
    """

    # TODO: look at either deprecating this or applying it appropriately to all managed objects
    @classmethod
    def get_key_prefix(cls, environment_type: str = 'prod'):
        parsed_type = environment_type.strip().lower()
        if parsed_type == 'test' or parsed_type == 'dev' or parsed_type == 'local':
            return parsed_type + '_job_mgr'
        else:
            return 'job_mgr'

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
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
        if 'type' in kwargs:
            key_prefix = self.get_key_prefix(environment_type=kwargs['type'])
        else:
            key_prefix = self.get_key_prefix()
        self._active_jobs_set_key = self.keynamehelper.create_key_name(key_prefix, 'active_jobs')

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
        Get the appropriate Redis key for accessing the util's record of the job with the given id.

        Parameters
        ----------
        job_id
            The id of the job of interest.

        Returns
        -------
        str
            The appropriate Redis key for accessing the util's record of the job with the given id.
        """
        return self.create_key_name('job', str(job_id))

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
        Get a list of every job known to this util object that is considered active based on each job's status.

        Returns
        -------
        List[RequestedJob]
            A list of every job known to this util object that is considered active based on each job's status.
        """
        active_jobs = []
        for active_job_redis_key in self.redis.smembers(self._active_jobs_set_key):
            active_jobs.append(self.retrieve_job_by_redis_key(active_job_redis_key))
        return active_jobs

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
        Add or update the given job object's Redis record, also maintaining a Redis set of the ids of 'active' jobs.

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
