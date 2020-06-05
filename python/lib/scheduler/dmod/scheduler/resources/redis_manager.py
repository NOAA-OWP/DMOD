#!/usr/bin/env python3
from typing import Iterable, List, Union, Optional
from redis import WatchError
import logging

from dmod.redis import RedisBacked
## local imports
from .resource_manager import ResourceManager
from .resource import Resource, ResourceAvailability, ResourceState
from .resource_allocation import ResourceAllocation
from ..job import Job, JobAllocationParadigm

Max_Redis_Init = 5

logging.basicConfig(
    filename='scheduler.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")


class RedisManager(ResourceManager, RedisBacked):
    """
    Implementation of a Redis-backed ::class:`ResourceManager` that works internally with modeled objects representing
    the involved data entities (e.g., ::class:`Resource` objects), as opposed to some other raw serial data structures
    like dictionaries.
    """

    def __init__(self, resource_pool: str, redis_host: Optional[str] = None, redis_port: Optional[int] = None,
                 redis_pass: Optional[str] = None, **kwargs):
        super().__init__(redis_host=redis_host, redis_port=redis_port, redis_pass=redis_pass, **kwargs)
        self.resource_pool = resource_pool
        self.resource_pool_key = self.keynamehelper.create_key_name("resource_pool", self.resource_pool)

    def add_resource(self, resource: Resource, resource_pool_key: Optional[str] = None):
        """
        Add a single resource to this managers pool.

        Parameters
        ----------
        resource : Resource
            A resource object.

        resource_pool_key : Optional[str]
            An optional string identifying the resource list to associate this resource with, if not the default of
            ::attribute:`resource_pool_key`.
        """
        if resource_pool_key is None:
            resource_pool_key = self.resource_pool_key
        resource.unique_id_separator = self.keynamehelper.separator
        if self.redis.exists(resource.unique_id) == 0:
            # Add main record
            self.redis.hmset(resource.unique_id, resource.to_dict())
            # And add reference to record in pool
            self.redis.sadd(resource_pool_key, resource.unique_id)

    def set_resources(self, resources: Iterable[Resource]):
        """
        Set the provided resources into the manager's resource tracker.

        Parameters
        ----------
        resources : Iterable[Resource]
            An iterable of resource objects.
        """
        for resource in resources:
            self.add_resource(resource)

    def get_resources(self) -> List[Resource]:
        """
        Get all managed resource objects.

        Returns
        -------
        List[Resource]
            A list of all managed resource objects.
        """
        for resource_id in self.get_resource_ids():
            yield Resource.factory_init_from_dict(
                self.redis.hgetall(Resource.generate_unique_id(resource_id, self.keynamehelper.separator)))

    def get_resource_ids(self) -> List[Union[str, int]]:
        """
            Get the identifiers for all managed resources

            Returns
            -------
            list of resource id's

        """
        resource_ids = list()
        for uid in self.get_resource_unique_ids():
            resource_ids.append(uid.split(':')[1])
        return resource_ids

    def get_resource_unique_ids(self):
        return self.redis.smembers(self.resource_pool_key)

    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory: int = 0, partial: bool = False) -> Optional[ResourceAllocation]:
        """
        Attempt to allocate the requested resource.

        Parameters
        ----------
        resource_id : str
            Unique ID string of the ::class:`Resource` from which the allocation will be sourced.

        requested_cpus : int
            Integer number of cpus to attempt to allocate.

        requested_memory : int
            Optional integer number of bytes of memory to allocate, defaulting to ``0``.

        partial : bool
            Whether to partially fulfill the requested allocation if the resource does not have the requested amounts of
            allocation properties available, which by default is ``False``.

        Returns
        -------
        Optional[ResourceAllocation]
            A resource allocation object, or ``None`` if there were insufficient allocation properties in the designated
            ::class:`Resource` and ``partial`` was set to ``False``

        Raises
        ------
        ValueError
            If the allocation request is invalid due to either an unrecognized source resource or requested CPU count of
            less than 1.

        """
        if requested_cpus <= 0:
            raise ValueError("Invalid < 1 CPU allocation requested")

        resource_key = Resource.generate_unique_id(resource_id, separator=self.keynamehelper.separator)
        if not self.redis.exists(resource_key):
            raise ValueError("Invalid allocation request to unrecognized resource {}".format(resource_key))

        allocation = None

        # By using the context manager, we get connection cleanup for free (e.g., pipeline.reset(), etc.)

        while True:
            with self.redis.pipeline() as pipeline:
                try:
                    # Will get WatchError if the value changes between now and pipe.execute()
                    pipeline.watch(resource_key)
                    resource = Resource.factory_init_from_dict(pipeline.hgetall(resource_key))
                    pipeline.multi()
                    cpus_allocated, mem_allocated, is_fully = resource.allocate(requested_cpus, requested_memory)

                    if is_fully or (partial and cpus_allocated > 0 and (mem_allocated > 0 or requested_memory == 0)):
                        pipeline.hmset(resource_key, resource.to_dict())
                        allocation = ResourceAllocation(resource_id, resource.hostname, cpus_allocated, mem_allocated)
                        allocation.unique_id_separator = self.keynamehelper.separator
                        pipeline.hmset(allocation.unique_id, allocation.to_dict())
                    else:
                        resource.release(cpus_allocated, mem_allocated)
                except WatchError:
                    logging.debug("Write Conflict allocate_resource: {}. Retrying...".format(resource_key))
                    # Clear and try the transaction again
                    pipeline.reset()
                    continue
                pipeline.execute()
                break
        return allocation

    def release_resource(self, allocation: ResourceAllocation):
        """
        Release a resource allocated to the manager.

        Parameters
        ----------
        allocation : ResourceAllocation
            A resource allocation object.
        """
        allocation.unique_id_separator = self.keynamehelper.separator
        while True:
            with self.redis.pipeline() as pipeline:
                try:
                    # Obtain the source Resource object for the allocation
                    source_resource_key = Resource.generate_unique_id(allocation.resource_id,
                                                                      self.keynamehelper.separator)
                    pipeline.watch(source_resource_key)
                    if not pipeline.exists(source_resource_key):
                        raise RuntimeError(
                            "RedisManager::release_resources -- No key {} exists to release resources to".format(
                                allocation.unique_id))

                    # Should return directly after watch takes us of of buffered mode
                    serial_source_resource_hash = pipeline.hgetall(source_resource_key)
                    source_resource = Resource.factory_init_from_dict(serial_source_resource_hash)

                    # Once we have looked up the resource record and deserialized, return to buffered transaction mode
                    pipeline.multi()
                    source_resource.unique_id_separator = self.keynamehelper.separator

                    # Release the allocated properties and updated the Resource record
                    source_resource.release(allocation.cpu_count, allocation.memory)
                    pipeline.hmset(source_resource_key, source_resource.to_dict())

                    # Delete the allocation redis record
                    # TODO: need to address implications of this in job manager
                    pipeline.delete(allocation.unique_id)

                    # Finally, execute the transaction
                    pipeline.execute()
                    return

                except WatchError:
                    logging.debug("Write Conflict allocate_resource: {}. Retrying...".format(source_resource_key))

    def release_resources(self, allocated_resources: Iterable[ResourceAllocation]):
        """
        Release any allocated resources to the manager.

        Parameters
        ----------
        allocated_resources : Iterable[ResourceAllocation]
            An iterable of resource allocation objects.
        """
        for allocation in allocated_resources:
            self.release_resource(allocation)

    def _allocate_fill_nodes(self, cpus: int, memory: int, resources: List[Resource]) -> List[ResourceAllocation]:
        # Plan things out first, before actually executing allocations
        cpu_alloc_by_res_index = {}
        mem_alloc_by_res_index = {}


        for i in range(len(resources)):
            if resources[i].cpu_count >= cpus and resources[i].memory >= memory:
                cpu_alloc_by_res_index[i] = cpus
                mem_alloc_by_res_index[i] = memory
            else:
                # TODO:
                pass
            # Finally, account for what's been allocated, before moving on to next resource or breaking
            cpus -= cpu_alloc_by_res_index[i]
            memory -= mem_alloc_by_res_index[i]
            if cpus < 1 and memory < 1:
                break

        #TODO: finish

    def _allocate_round_robin(self, cpus: int, memory: int, resources: List[Resource]) -> List[ResourceAllocation]:
        # TODO
        pass


    def request_allocations(self, job: Job) -> Iterable[ResourceAllocation]:
        """
        Request resource allocations for the given ::class:`Job` object, according to its needs and permitted allocation
        paradigm(s).

        Parameters
        ----------
        job

        Returns
        -------
        Iterable[ResourceAllocation]
            An iterable collection of allocations to satisfy the given job, which will be empty if there are not
            sufficient assets available to construct such allocations.
        """
        # Filter only ready and usable resources
        usable_resources = []
        for resource in self.get_resources():
            # Only allocatable resources are usable
            if resource.is_allocatable():
                usable_resources.append(resource)

        # Return immediately if there are no usable resources
        if len(usable_resources) == 0:
            return []

        if job.allocation_paradigm == JobAllocationParadigm.SINGLE_NODE:
            return self._allocate_single_node(cpus=job.cpu_count, memory=job.memory_size, resources=usable_resources)
        elif job.allocation_paradigm == JobAllocationParadigm.FILL_NODES:
            return self._allocate_fill_nodes(cpus=job.cpu_count, memory=job.memory_size, resources=usable_resources)
        elif job.allocation_paradigm == JobAllocationParadigm.ROUND_ROBIN:
            return self._allocate_round_robin(cpus=job.cpu_count, memory=job.memory_size, resources=usable_resources)
        else:
            # TODO: handle this better
            raise RuntimeError("Unknown allocation paradigm {}".format(str(job.allocation_paradigm)))

    def get_available_cpu_count(self) -> int:
        """
        Returns a count of all available CPU's summed across all resources at the time of calling.

        Not guaranteed available until allocated.

        Returns
        -------
        int
            Total available CPUs.
        """
        resource_keys = list()
        for resource_id in self.get_resource_ids():
            resource_keys.append(Resource.generate_unique_id(resource_id, self.keynamehelper.separator))

        while True:
            with self.redis.pipeline() as pipeline:
                total_available = 0
                try:
                    pipeline.watch(*resource_keys)
                    for key in resource_keys:
                        total_available += int(pipeline.hget(key, Resource.get_cpu_hash_key()))
                except WatchError as e:
                    logging.warning("Resource changed while counting available CPUs; will retry", e)
                    continue
                break
        return total_available
