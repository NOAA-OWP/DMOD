#!/usr/bin/env python3
import logging
from typing import Iterable, Optional, Union, List
from abc import ABC, abstractmethod
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
    def get_resources(self) -> Iterable[Resource]:
        """
        Get an iterable collection of the ::class:`Resource` objects for known resources.

        Returns
        -------
        Iterable[Resource]
            An iterable collection of the ::class:`Resource` objects for known resources.
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
            integer number of cpus to attempt to allocate

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
    def get_available_cpu_count(self) -> int:
        """
            Returns a count of all available CPU's summed across all resources
            at the time of calling.  Not guaranteed avaialable until allocated.

            Returns
            -------
            total available CPUs
        """
        pass

    def get_useable_resources(self) -> Iterable[Resource]:
        """
            Generator yielding allocatable resources

            Returns
            -------
            resources marked as 'allocatable'
        """
        # Filter only ready and usable resources
        for resource in self.get_resources():
            # Only allocatable resources are usable
            if resource.is_allocatable():
                yield resource

    def validate_allocation_parameters(self, cpus: int, memory: int):
        """
            Validate the allocation parameters

            Parameters
            ----------
                cpus: requested number of cpus
                memory: requested amount of memory (in bytes)

            Raises
            ------
                ValueError if cpus is or memory is not an integer > 0
        """
        if not (isinstance(cpus, int) and cpus > 0):
            raise(ValueError("cpus must be an integer > 0"))
        if not (isinstance(memory, int) and memory > 0):
            raise(ValueError("memory must be an integer > 0"))

    def allocate_single_node(self, cpus: int, memory: int) -> List[ResourceAllocation]:
        """
        Check available resources to allocate job request to a single node to optimize
        computation efficiency

        Parameters
        ----------
            cpus: Total number of CPUs requested
            memory: Amount of memory required in bytes

        Returns
        -------
        [ResourceAlloction]
            Single element List of ResourceAllocation if allocation successful, otherwise, [None]
        """
        #Fit the entire allocation on a single resource
        self.validate_allocation_parameters(cpus, memory)

        for res in self.get_useable_resources():
            #if res.cpu_count >= cpus and res.memory >= memory:
            allocation = self.allocate_resource(resource_id=res.resource_id, requested_cpus=cpus,
                                                requested_memory=memory)
            if allocation:
                return [allocation]
        return [None]

    def allocate_fill_nodes(self, cpus: int, memory: int) -> List[ResourceAllocation]:
        """
        Check available resources to allocate job request to one or more nodes, claiming all required
        resources from each node until the request is satisfied.

        Parameters
        ----------
            cpus: Total number of CPUs requested
            memory: Amount of memory required in bytes

        Returns
        -------
        [ResourceAlloction]
            List of one or more ResourceAllocation if allocation successful, otherwise, [None]
        """
        self.validate_allocation_parameters(cpus, memory)
        #TODO fill_nodes really should allocate on a MEM per CPU basis???
        allocation = []

        for res in self.get_useable_resources(): #i in range(len(resources)):
            #Greedily allocate a (potentially) partial allocation on this resource
            alloc = self.allocate_resource(resource_id=res.resource_id, requested_cpus=cpus,
                                                requested_memory=memory, partial=True)
            if alloc:
                #The allocation was (partially) successful
                allocation.append(alloc)
                cpus -= alloc.cpu_count
                #TODO what about memory?  If mem_per_node, don't change it
            else:
                #TODO think about mem per process type allocation
                #For now, this resource cannot provide anything to the allocation
                #So we skip to the next one
                continue
            if cpus < 1:
                break

        #If enough resources found, return the allocations
        #otherwise we have to roll back the greedily aquired resources
        if cpus > 0:
            self.release_resources(allocation)
            allocation = [None]

        return allocation

    def allocate_round_robin(self, cpus: int, memory: int) -> List[ResourceAllocation]:
        """
            Check available resources on host nodes and allocate in round robin manner even the request
            can fit in a single node.

            TODO this is a balanced round robin algorithm, assuming an even distribution is possible across all resources,
            with up to num_node-1 remainders to fill in.  This is not the most generic "round robin" in which we allocate
            cpus one after the other across all available resources and don't try to balance.
            i.e. a request for 10 cpus with an available resource view of [4, 2, 4] would fail to allocate with this
            algorithm, because it assumes an availablity of [4, 3, 3]

            Parameters
            ----------
                cpus: Total number of CPUs requested
                memory: Amount of memory required in bytes

            Returns
            -------
            [ResourceAlloction]
                List of one or more ResourceAllocation if allocation successful, otherwise, [None]
        """
        #TODO consider scaling memory per cpu
        #Find the number of cpus to allocate to each node
        self.validate_allocation_parameters(cpus, memory)
        resources = list(self.get_useable_resources())

        num_node = len(resources)
        if num_node == 0:
            return [None]

        int_cpus = int(cpus / num_node)
        remaining_cpus = cpus % num_node
        cpu_per_resource = [int_cpus]*num_node #The minimun number of cpus on each resource
        for i in range(remaining_cpus):
            cpu_per_resource[i] += 1    #Add remainder if needed

        allocation = []

        for i in range(num_node):
            #Greedily allocate a full allocation on this resource
            alloc = self.allocate_resource(resource_id=resources[i].resource_id, requested_cpus=cpu_per_resource[i],
                                                requested_memory=memory)
            if alloc:
                #This resource can satisfy the allocation so far
                allocation.append(alloc)
                cpus -= alloc.cpu_count
            else:
                #TODO think about mem per process type allocation
                #For now, this resource cannot provide anything to the allocation
                #If alloc wasn't successful, don't need to try any more, release any we are holding and return
                self.release_resources(allocation)
                return [None]

        return allocation
