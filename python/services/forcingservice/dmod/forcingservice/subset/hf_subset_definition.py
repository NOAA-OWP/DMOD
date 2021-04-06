from abc import ABC, abstractmethod
from hypy import Catchment, Nexus
from queue import Queue
from typing import Collection, Sequence, Set, Tuple, Union
from .subset_definition import SubsetDefinition


class HFSubsetDefinition(ABC, SubsetDefinition):
    """
    Abstract extension of ::class:`SubsetDefinition` that also contains a hydrofabric for at least its defined parts.

    An abstract extension of the base ::class:`SubsetDefinition` that must be initialized with a ``hydrofabric`` param
    as well, making it capable of also accessing to the actual catchment and nexus elements.

    The type for the ``hydrofabric`` param (and utilizing ::attribute:`_hydrofabric` attribute) are not strictly
    specified.  However, it must be possible for objects implementing this abstraction to derive equivalent
    ::class:`Catchment` and ::class:`Nexus` objects from the catchments and nexuses are represented therein.  Depending
    on the particular implementation, these may be restricted to specific subtypes of ::class:`Catchment` and/or
    ::class:`Nexus`.  These are part of a "validity" constraint for the hydrofabric which is imposed by the
    ::method:`validate_hydrofabric` method.

    The requirements of the contained data of the ::attribute:`_hydrofabric` are also loose with respect to this base
    abstraction. I.e., ::attribute:`_hydrofabric` may contain any amount of data, so long as the it at minimum contains
    the necessary data for the subset represented by its parent object. As a consequences, ::attribute:`_hydrofabric` is
    not intended to be used directly externally and so does not effect things like hash value or equality.
    """

    __slots__ = ["_hydrofabric"]

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str], hydrofabric):
        super(HFSubsetDefinition, self).__init__(catchment_ids, nexus_ids)
        if not self.validate_hydrofabric(hydrofabric):
            raise RuntimeError("Insufficient or wrongly formatted hydrofabric when trying to create {} object".format(
                self.__class__.__name__
            ))
        self._hydrofabric = hydrofabric

    @property
    @abstractmethod
    def catchments(self) -> Tuple[Catchment]:
        """
        Get the associated catchments as ::class:`Catchment` objects.

        Returns
        -------
        Tuple[Catchment]
            The associated catchments as ::class:`Catchment` objects.
        """
        pass

    @property
    @abstractmethod
    def nexuses(self) -> Tuple[Nexus]:
        """
        Get the associated nexuses as ::class:`Nexus` objects.

        Returns
        -------
        Tuple[Catchment]
            The associated nexuses as ::class:`Nexus` objects.
        """
        pass

    @abstractmethod
    def validate_hydrofabric(self, hydrofabric) -> bool:
        """
        Determine whether the given hydrofabric is valid for this subset object.

        A hydrofabric is valid if it has sufficient data to retrieve or derive <i>appropriate</i> ::class:`Catchment`
        and ::class:`Nexus` objects to represent all the catchments and nexuses of this subset object.

        Note that ::class:`Catchment` and ::class:`Nexus` are listed for simplicity and generality, but implementations
        may require more specific subtypes of either when determining hydrofabric validity.

        Returns
        -------
        bool
            ``True`` if the hydrofabric's has sufficient data, in format and content, for this subset, or ``False``
            otherwise.
        """
        pass


class SimpleHFSubsetDefImpl(HFSubsetDefinition):
    """
    Simple ::class:`HFSubsetDefinition` type hydrofabric being one or more catchment or nexus objects.
    """

    @classmethod
    def factory_create_from_base_and_hydrofabric(cls, subset_def: SubsetDefinition,
                                                 hydrofabric: Union[Sequence[Union[Catchment, Nexus]], Catchment, Nexus]) \
            -> 'SimpleHFSubsetDefImpl':
        """
        Convenience method for creating from a simpler subset def object and a hydrofabric.

        Parameters
        ----------
        subset_def : SubsetHandler
            Simple subset definition object, encapsulating the required catchment and nexus ids.

        hydrofabric : Union[Sequence[Catchment, Nexus], Catchment, Nexus]
            Hydrofabric parameter of an acceptable type.

        Returns
        -------
        SimpleHFSubsetDefImpl
            A ::class:`SimpleHFSubsetDefinition` object for the same subset defined by ``subset_def``.
        """
        return cls(catchment_ids=subset_def.catchment_ids, nexus_ids=subset_def.nexus_ids, hydrofabric=hydrofabric)

    __slots__ = ["_catchments", "_nexuses"]

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str],
                 hydrofabric: Union[Sequence[Union[Catchment, Nexus]], Catchment, Nexus]):
        self._catchments: Set[Catchment] = set()
        self._nexuses: Set[Nexus] = set()
        super(SimpleHFSubsetDefImpl, self).__init__(catchment_ids, nexus_ids, hydrofabric)

    @property
    def catchments(self) -> Tuple[Catchment]:
        """
        Get the associated catchments as ::class:`Catchment` objects.

        Returns
        -------
        Tuple[Catchment]
            The associated catchments as ::class:`Catchment` objects.
        """
        return tuple(self._catchments)

    @property
    def nexuses(self) -> Tuple[Nexus]:
        """
        Get the associated nexuses as ::class:`Nexus` objects.

        Returns
        -------
        Tuple[Catchment]
            The associated nexuses as ::class:`Nexus` objects.
        """
        return tuple(self._nexuses)

    def validate_hydrofabric(self, hydrofabric: Union[Sequence[Union[Catchment, Nexus]], Catchment, Nexus]) -> bool:
        """
        Determine whether the given hydrofabric is valid for this subset object.

        A hydrofabric is valid if it has sufficient data to retrieve or derive <i>appropriate</i> ::class:`Catchment`
        and ::class:`Nexus` objects to represent all the catchments and nexuses of this subset object.

        The given hydrofabric may either be a ::class:`Catchment` or ::class:`Nexus` object, or a sequences of
        such objects.

        This particular implementation also populates the ::attribute:`catchments` and ::attribute:`nexuses` properties
        when processing the hydrofabric for validity.

        Returns
        -------
        bool
            ``True`` if the hydrofabric's has sufficient data, in format and content, for this subset, or ``False``
            otherwise.
        """
        hf_graph = Queue()
        # We will deal with things as a queue of graph nodes to process.  Start by validating the param
        if isinstance(hydrofabric, Catchment) or isinstance(hydrofabric, Nexus):
            hf_graph.put(hydrofabric)
        elif isinstance(hydrofabric, Sequence):
            for item in hydrofabric:
                if isinstance(item, Catchment) or isinstance(item, Nexus):
                    hf_graph.put(item)
                else:
                    return False
        else:
            return False

        already_seen = set()
        required_item_ids = set(self._catchment_ids)
        required_item_ids.update(self._nexus_ids)
        found_items = 0

        while hf_graph.qsize() > 0:
            item = hf_graph.get()

            # Keep track of what we have seen, and don't repeat steps
            if item is None or item.id in already_seen:
                continue
            else:
                already_seen.add(item.id)

            # Whenever seeing something with a required id, update our tally, mark it found, and check if we are done
            if item.id in required_item_ids:
                found_items += 1

                # Add found required things to appropriate internal collection
                # To be in required_item_ids, must be in either set of catchment ids or set of nexus ids, so ...
                if item.id in self._catchment_ids:
                    self._catchments.add(item)
                else:
                    self._nexuses.add(item)

                # If this was the last thing, we can stop here
                if found_items == len(required_item_ids):
                    return True

            # Finally, traverse graph and add new next nodes to the hf_graph processing queue
            if isinstance(item, Catchment):
                hf_graph.put(item.inflow)
                hf_graph.put(item.outflow)
                # Don't think we should need to worry about containing or contained items; if they are needed,
                # additional catchments/nexuses that can reach them through same-scoped connections should be present
            if isinstance(item, Nexus):
                for c in item.contributing_catchments:
                    hf_graph.put(c)
                for c in item.receiving_catchments:
                    hf_graph.put(c)

        # If we get all the way out here, all nodes have been traversed, but we didn't find everything we needed, so ...
        return False
