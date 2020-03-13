#!/usr/bin/env python3
from typing import Iterable, List, Union, Optional
from redis import WatchError
import logging

## local imports
from .resource_manager import ResourceManager
from nwmaas.redis import RedisBacked
from .resources import Resource, ResourceAllocation

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
        super().__init__(resource_pool=resource_pool, redis_host=redis_host, redis_port=redis_port,
                         redis_pass=redis_pass, **kwargs)

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
            yield Resource.factory_init_from_dict(self.redis.hgetall(resource_id))

    def get_resource_ids(self) -> List[Union[str, int]]:
        """
            Get the identifiers for all managed resources

            Returns
            -------
            list of resource id's

        """
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
        with self.redis.pipeline() as pipeline:
            while True:
                try:
                    # Will get WatchError if the value changes between now and pipe.execute()
                    pipeline.watch(resource_key)
                    resource = Resource.factory_init_from_dict(self.redis.hgetall(resource_key))
                    cpus_allocated, mem_allocated, is_fully = resource.allocate(requested_cpus, requested_memory)

                    if is_fully or (partial and cpus_allocated > 0 and (mem_allocated > 0 or requested_memory == 0)):
                        pipeline.hmset(resource_key, resource.to_dict())
                        allocation = ResourceAllocation(resource_id, resource.hostname, cpus_allocated, mem_allocated)
                        allocation.unique_id_separator = self.keynamehelper.separator
                        pipeline.hmset(allocation.unique_id, allocation.to_dict())
                        pipeline.execute()
                    else:
                        resource.release(cpus_allocated, mem_allocated)
                except WatchError:
                    logging.debug("Write Conflict allocate_resource: {}. Retrying...".format(resource_key))
                    # Try the transaction again
                    continue
                break
        return allocation

    def release_resources(self, allocated_resources: Iterable[ResourceAllocation]):
        """
        Release any allocated resources to the manager.

        Parameters
        ----------
        allocated_resources : Iterable[ResourceAllocation]
            An iterable of resource allocation objects.
        """
        # A kind of local cache for retrieve and inflated Resource objects
        retrieved_resources = dict()

        # Also ...
        separator = self.keynamehelper.separator

        with self.redis.pipeline() as pipeline:
            for allocation in allocated_resources:
                allocation.unique_id_separator = separator

                # Obtain the source Resource object for the allocation
                source_resource_key = Resource.generate_unique_id(allocation.resource_id, separator)
                if source_resource_key in retrieved_resources:
                    source_resource = retrieved_resources[source_resource_key]
                elif not self.redis.exists(source_resource_key):
                    raise RuntimeError(
                        "RedisManager::release_resources -- No key {} exists to release resources to".format(
                            allocation.unique_id))
                else:
                    source_resource = Resource.factory_init_from_dict(pipeline.hmget(source_resource_key))
                    source_resource.unique_id_separator = separator
                    # Cache locally
                    retrieved_resources[source_resource_key] = source_resource

                # Release the allocated properties
                source_resource.release(allocation.cpu_count, allocation.memory)

                # Finally, delete the allocation redis record
                # TODO: need to address implications of this in job manager
                pipeline.delete(allocation.unique_id)

            # Once done with the allocation release loop, persisted any and all updated, locally cached Resources
            for resource_key in retrieved_resources:
                pipeline.hmset(resource_key, retrieved_resources[resource_key].to_dict())

            pipeline.execute()

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

        with self.redis.pipeline() as pipeline:
            while True:
                total_available = 0
                try:
                    for key in resource_keys:
                        pipeline.watch(key)
                        resource = Resource.factory_init_from_dict(pipeline.hgetall(key))
                        total_available += resource.cpu_count
                except WatchError as e:
                    logging.warning("Resource changed while counting available CPUs; will retry", e)
                    continue
                break
        return total_available
