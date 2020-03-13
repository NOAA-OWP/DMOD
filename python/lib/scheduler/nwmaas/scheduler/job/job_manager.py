import os
import time
from abc import ABC, abstractmethod
from redis import Redis
from typing import Optional
from uuid import uuid4 as generate_uuid
from .job import Job
from ..rsa_key_pair import RsaKeyPair

from nwmaas.redis import RedisBacked


class JobManagerFactory:
    """
    A basic concrete implementation of a factory for obtaining ::class:`JobManager` instances.

    The intent is for this to be exposed, along with interface class, but have implementations of ::class:`JobManager`
    be essentially obscured.  To support externally created implementations, this factory class can itself be extended.

    This default implementation is only aware of one particular concrete type that uses a Redis backend, so it will
    always return an instance of that type.  The supported keyword args are documented in the method.
    """

    @classmethod
    def factory_create(cls, **kwargs):
        """
        Create and return a new instance of a ::class:`JobManager` object.

        In this default method implementation, only a single, Redis-backed type is available.  The method supports
        receiving keyword args to provide non-default values for the host, port, and password parameters for the Redis
        server connection.

        Keyword Args
        ----------
        host : str
            The Redis service host name.
        port : int
            The Redis service port.
        password : str
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
            if key == 'host':
                host = value
            elif key == 'port':
                port = int(value)
            elif key == 'password':
                pword = value
        return RedisBackedJobManager(redis_host=host, redis_port=port, redis_pass=pword)


class JobManager(ABC):

    @abstractmethod
    def create_job(self, cpu_count: int,  memory_size: int, parameters: dict, allocation: Optional[dict] = None,
                   key_pair: Optional[RsaKeyPair] = None, **kwargs) -> Job:
        """
        Create and return a new job object.

        Parameters
        ----------
        cpu_count : int
            A count of CPUs for the job.

        memory_size : int
            A size of memory needed for the job.

        parameters : dict
            A dictionary of job config parameters

        allocation : Optional[dict]
            An optional dictionary of the scheduled allocation for the job.

        key_pair : Optional[RsaKeyPair]
            An optional RSA key pair of use with SSH for create job service(s)

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


class RedisBackedJobManager(JobManager, RedisBacked):

    def __init__(self, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None):
        super(RedisBacked).__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass)


