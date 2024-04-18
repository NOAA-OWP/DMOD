#!/usr/bin/env python3
import logging
from typing import Iterable, Optional, Union, List
from abc import ABC, abstractmethod
from dmod.core.execution import AllocationAssetGrouping
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

    # TODO: (later) consider encapsulating the notion of an AllocationRequest or something like that, especially if more
    #  things like AllocationAssetGrouping are added (e.g., for required ratio - or not - of memory to CPU)
    def allocate_single_node(self, cpus: int, memory: int,
                             asset_grouping: AllocationAssetGrouping = AllocationAssetGrouping.BUNDLE) -> List[
        Optional[ResourceAllocation]]:
        """
        Generate and return allocations as needed on a single node, according to the ``SINGLE_NODE`` paradigm.

        When there is some available :class:`Resource` node that has sufficient assets, return one or more
        :class:`ResourceAllocation` objects associated with that node such that the requested amounts of assets are
        fulfilled.

        For a ``BUNDLED`` :class:`AllocationAssetGrouping`, a single allocation is returned containing all the assets.
        For ``SILO``, several allocations are returned, each with a single CPU and an even share of the total requested
        memory.

        Parameters
        ----------
            cpus: Total number of CPUs requested
            memory: Amount of memory required in bytes
            asset_grouping: The way compute assets from a single node are grouped into allocations.

        Returns
        -------
        [ResourceAlloction]
            List of ResourceAllocation if allocation successful; otherwise, [None]
        """
        #Fit the entire allocation on a single resource
        self.validate_allocation_parameters(cpus, memory)

        node = None
        for resource_node in self.get_useable_resources():
            if resource_node.cpu_count >= cpus and resource_node.memory >= memory:
                node = resource_node
                break
        if node is None:
            return [None]

        if asset_grouping == AllocationAssetGrouping.BUNDLE:
            return [self.allocate_resource(resource_id=node.resource_id, requested_cpus=cpus, requested_memory=memory)]

        allocations = []
        mem = int(memory / cpus)
        for i in range(cpus):
            alloc = self.allocate_resource(resource_id=node.resource_id, requested_cpus=1, requested_memory=mem)
            # If any individual allocation failed because assets ran out ...
            if alloc is None:
                # ... release anything that was allocated, and then bail
                self.release_resources(allocations)
                return [None]
            else:
                allocations.append(alloc)
        return allocations

    def allocate_fill_nodes(self, cpus: int, memory: int,
                            asset_grouping: AllocationAssetGrouping = AllocationAssetGrouping.BUNDLE) -> List[
        Optional[ResourceAllocation]]:
        """
        Generate allocations of the requested assets on one or more nodes, using all of a nodes before moving to next.

        Generate allocations on one or more nodes to fulfill the requested assets.  For the current node, claim all
        available, compute assets before, up to the remaining amount requested, before beginning to get resources
        from the next node.

        For a ``BUNDLED`` :class:`AllocationAssetGrouping`, a single allocation is returned per :class:`Resource` node
        containing all the assets allocated from that node. For ``SILO``, several per-node allocations are returned,
        each with a single CPU and a roughly even share of the total requested memory.

        Parameters
        ----------
            cpus: Total number of CPUs requested
            memory: Amount of memory required in bytes
            asset_grouping: The way compute assets from a single node are grouped into allocations

        Returns
        -------
        [ResourceAllocation]
            List of one or more :class:`ResourceAllocation` if allocation successful, otherwise, [None]
        """
        self.validate_allocation_parameters(cpus, memory)
        # TODO: (later) consider another exec config enum that encapsulates the relationship between memory and cpu;
        #  e.g., sometimes memory should be the same amount per CPU, but other times maybe we want more memory on a box
        allocations = []

        def request_alloc(node_resource_id):
            requested_cpus = cpus if asset_grouping == AllocationAssetGrouping.BUNDLE else 1
            requested_memory = memory if asset_grouping == AllocationAssetGrouping.BUNDLE else int(memory / cpus)
            return self.allocate_resource(node_resource_id, requested_cpus, requested_memory, partial=True)

        # TODO: (later) this doesn't do a good job of accounting for the ratio of CPU to memory, though we'd also have
        #  to assume what the user wanted
        for res in self.get_useable_resources(): #i in range(len(resources)):
            # Greedily allocate a (potentially) partial allocation on this resource
            alloc = request_alloc(node_resource_id=res.resource_id)
            # Whenever the allocation was (partially) successful
            while isinstance(alloc, ResourceAllocation) and cpus - alloc.cpu_count > 0:
                # Disregard and release a partial allocation that provides below a min threshold, then move to next node
                if alloc.cpu_count == 0 or alloc.memory == 0:
                    self.release_resources([alloc])
                    alloc = None
                # Otherwise, append this allocation, update our outstanding quantities, and then allocate again
                else:
                    allocations.append(alloc)
                    cpus -= alloc.cpu_count
                    memory -= alloc.memory
                    alloc = request_alloc(node_resource_id=res.resource_id)
            # Here (back in outer loop), if we have all needed allocations, return (otherwise continue to next resource)
            # TODO: (later) account for whether we actually got enough memory better here
            if cpus == 0:
                return allocations

        # If there weren't enough resources and assets, roll back and release the acquired allocations
        # TODO: (later) similarly, account for whether we actually got enough memory better here
        self.release_resources(allocations)
        return [None]

    def allocate_round_robin(self, cpus: int, memory: int,
                             asset_grouping: AllocationAssetGrouping = AllocationAssetGrouping.BUNDLE) -> List[
        Optional[ResourceAllocation]]:
        """
            Generate allocations of the requested assets evenly across all active, ready resource nodes.

            Generate even, balanced allocations of the requested assets across all nodes that are active and ready.
            Importantly, this is slightly different not just those within

            This is a balanced round robin algorithm, assuming an even distribution is possible across all resources,
            with up to num_node-1 remainders to fill in.
            Note that this is not the most generic "round robin" in which we allocate
            cpus one after the other across all available resources and don't try to balance.
            i.e. a request for 10 cpus with an available resource view of [4, 2, 4] would fail to allocate with this
            algorithm, because it assumes an availability of [4, 3, 3]

            For a ``BUNDLED`` :class:`AllocationAssetGrouping`, a single allocation is returned per :class:`Resource`
            node containing all the assets allocated from that node. For ``SILO``, several per-node allocations are
            returned, each with a single CPU and a roughly even share of the total requested memory.

            Parameters
            ----------
                cpus: Total number of CPUs requested
                memory: Amount of memory required in bytes
                asset_grouping: The way compute assets from a single node are grouped into allocations

            Returns
            -------
            [ResourceAlloction]
                List of one or more ResourceAllocation if allocation successful, otherwise, [None]
        """
        #TODO consider scaling memory per cpu
        self.validate_allocation_parameters(cpus, memory)
        # Get all active and ready nodes, regardless of whether they are "allocateable" (i.e., not full)
        resource_nodes = {r.resource_id: r for r in self.get_resources() if r.is_active() and r.is_ready()}

        # Calculate in advance the exact amounts of CPUs and memory per node for the necessary balance
        # This is slightly different from simply an even share due to discrete amounts and remainders
        cpus_per_node, memory_per_node = dict(), dict()
        num_nodes = len(resource_nodes)
        cpu_share, mem_share = int(cpus / num_nodes), int(memory / num_nodes)
        cpu_remainder, mem_remainder = cpus - cpu_share, memory - mem_share

        for node_id, node in resource_nodes.items():
            # We must plan to request at least the per-node amounts on each node
            if node.cpu_count < cpu_share or node.memory < memory:
                return [None]
            cpus_per_node[node_id] = cpu_share
            memory_per_node[node_id] = mem_share
            # But we also need to try to pick up a share of the remainders if we can
            if node.cpu_count > cpu_share and cpu_remainder > 0:
                cpus_per_node[node_id] += 1
                cpu_remainder -= 1
            if node.memory > mem_share and mem_remainder > 0:
                memory_per_node[node_id] += 1
                mem_remainder -= 1

        # We must also make sure that all of each remainder was picked up
        if cpu_remainder > 0 or mem_remainder > 0:
            return [None]

        allocations = []
        for node_id in resource_nodes:
            alloc_count = 1 if asset_grouping == AllocationAssetGrouping.BUNDLE else cpus_per_node[node_id]
            for i in range(alloc_count):
                alloc = self.allocate_resource(resource_id=node_id,
                                               requested_cpus=int(cpus_per_node[node_id] / alloc_count),
                                               requested_memory=int(memory_per_node[node_id] / alloc_count))
                if not isinstance(alloc, ResourceAllocation):
                    self.release_resources(allocations)
                    return [None]
        return allocations
