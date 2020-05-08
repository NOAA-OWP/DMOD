#!/usr/bin/env python3
import logging
from typing import Iterable, Optional, Union
from abc import ABC, abstractmethod
from ..job import Job
from .resource import Resource
from .resource_allocation import ResourceAllocation

# As a pure ABC probably don't need logging
logging.basicConfig(
    filename='ResourceManager.log',
    level=logging.DEBUG,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S")


class ResourceManager(ABC):
    """
        Abstract class for defining the API for Resource Managing
    """

    @abstractmethod
    def set_resources(self, resources: Iterable[Resource]):
        """
            Set the provided resources into the manager's resource tracker.

            Parameters
            ----------
            resources
                An iterable of maps defining each resource to set.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

            Returns
            -------
            None


        """
        pass

    @abstractmethod
    def get_resources(self) -> Union[Iterable[str], Iterable[Resource]]:
        """
            Get metadata of all managed resoures.

            Returns
            -------
            resources
                An iterable of maps defining each managed resource.
                One map per resource with the following metadata.
                 { 'node_id': "Node-0001",
                   'Hostname': "my-host",
                   'Availability': "active",
                   'State': "ready",
                   'CPUs': 18,
                   'MemoryBytes': 33548128256
                  }

        """
        pass

    @abstractmethod
    def get_resource_ids(self) -> Iterable[Union[str, int]]:
        """
            Get the identifiers for all managed resources

            Returns
            -------
            list of resource id's

        """
        pass

    @abstractmethod
    def allocate_resource(self, resource_id: str, requested_cpus: int,
                          requested_memory: int = 0, partial: bool = False) -> Optional[ResourceAllocation]:
        """
        Attempt to allocate the requested resources.

        Parameters
        ----------
        resource_id
            Unique ID string of the resource referenceable by the manager

        requested_cpus
            integer numbre of cpus to attempt to allocate

        requested_memory
            integer number of bytes to allocate.  currently optional

        partial
            whether to partially fulfill the requested allocation and return
            an allocation map with less than the requested allocation

        Returns
        -------
        Optional[ResourceAllocation]
            A resource allocation object, or ``None`` if there were insufficient allocation properties in the designated
            ::class:`Resource` and ``partial`` was set to ``False``
        """
        pass

    @abstractmethod
    def release_resources(self, allocated_resources: Iterable[ResourceAllocation]):
        """
        Release allocated resources to the manager.

        Parameters
        ----------
        allocated_resources : Iterable[ResourceAllocation]
            An iterable of resource allocation objects.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_available_cpu_count(self) -> int:
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        pass
