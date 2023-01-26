from abc import ABC, abstractmethod
from hypy import Catchment, Nexus
from typing import Collection, Optional, Set, Tuple
from pydantic import PrivateAttr
from ..hydrofabric import Hydrofabric
from .subset_definition import SubsetDefinition


class HydrofabricSubset(SubsetDefinition, ABC):
    """
    Abstract extension of ::class:`SubsetDefinition` that also contains a hydrofabric for at least its defined parts.

    An abstract extension of the base ::class:`SubsetDefinition` that must be initialized with a ``hydrofabric`` param
    as well, making it capable of also accessing to the actual catchment and nexus elements.

    Note that for equality, the tests of the super class type must be true.  Further, instances of this type must have
    a valid hydrofabric attribute according to ::method:`validate_hydrofabric` to be deemed equal to an otherwise-equal
    object.  The only exception is if two objects are of this type and are **both** invalid.  I.e., a base subset is not
    equal to an object of this type with the exact same catchments and nexuses IFF the object of this type does not
    possess a valid hydrofabric.

    The hash value is calculated in essentially the same fashion as the super class, except that a small adjustment is
    made in the case of invalid objects.  In such cases, the hash is equal to the super class hash output plus ``1``.
    """

    hydrofabric: Hydrofabric

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str], hydrofabric: Hydrofabric, **data):
        super().__init__(catchment_ids=catchment_ids, nexus_ids=nexus_ids, hydrofabric=hydrofabric, **data)
        if not self.validate_hydrofabric(hydrofabric):
            raise RuntimeError("Insufficient or wrongly formatted hydrofabric when trying to create {} object".format(
                self.__class__.__name__
            ))

    def __eq__(self, other: object):
        if isinstance(other, self.__class__):
            return self.validate_hydrofabric() == other.validate_hydrofabric() and super().__eq__(other)
        else:
            return self.validate_hydrofabric() and super().__eq__(other)

    def __hash__(self):
        if self.validate_hydrofabric():
            return super().__hash__()
        else:
            return super().__hash__() + 1

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
    def validate_hydrofabric(self, hydrofabric: Optional[Hydrofabric] = None) -> bool:
        """
        Determine whether hydrofabric is valid for this subset object.

        A hydrofabric is valid if it has sufficient data to retrieve or derive <i>appropriate</i> ::class:`Catchment`
        and ::class:`Nexus` objects to represent all the catchments and nexuses of this subset object.

        Implementations should be constructed to operate on the objects internal hydrofabric attribute if the provided
        parameter is ``None``, which should also be the default.

        Parameters
        ----------
        hydrofabric : Optional[Hydrofabric]
            A hydrofabric in which to determine validity, interpreted as the object's own hydrofabric if ``None``.

        Returns
        -------
        bool
            ``True`` if the hydrofabric has sufficient data, in format and content, for this subset, or ``False``
            otherwise.
        """
        pass


class SimpleHydrofabricSubset(HydrofabricSubset):
    """
    Simple ::class:`HydrofabricSubset` type.
    """

    _catchments: Set[Catchment] = PrivateAttr(default_factory=set)
    _nexuses: Set[Nexus] = PrivateAttr(default_factory=set)

    @classmethod
    def factory_create_from_base_and_hydrofabric(cls, subset_def: SubsetDefinition, hydrofabric: Hydrofabric,
                                                 *args, **kwargs) \
            -> 'SimpleHydrofabricSubset':
        """
        Convenience method for creating from a simpler subset def object and a hydrofabric.

        Parameters
        ----------
        subset_def : SubsetDefinition
            Subset definition object, encapsulating the required catchment and nexus ids.

        hydrofabric : Hydrofabric
            Hydrofabric parameter of an acceptable type.

        Other Parameters
        ----------------
        Other parameters utilized during initialization of the particular class/subclass implementation.

        Returns
        -------
        SimpleHydrofabricSubset
            A ::class:`SimpleHFSubsetDefinition` object for the same subset defined by ``subset_def``.
        """
        return cls(catchment_ids=subset_def.catchment_ids, nexus_ids=subset_def.nexus_ids, hydrofabric=hydrofabric,
                   *args, **kwargs)

    def __init__(self, catchment_ids: Collection[str], nexus_ids: Collection[str], hydrofabric: Hydrofabric, **data):
        super().__init__(catchment_ids=catchment_ids, nexus_ids=nexus_ids, hydrofabric=hydrofabric, **data)
        # Since super __init__ validates, and validate function make sure ids are recognized, these won't ever be None
        for cid in self.catchment_ids:
            self._catchments.add(hydrofabric.get_catchment_by_id(cid))
        for nid in self.nexus_ids:
            self._nexuses.add(hydrofabric.get_nexus_by_id(nid))

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

    def validate_hydrofabric(self, hydrofabric: Optional[Hydrofabric] = None) -> bool:
        """
        Determine whether hydrofabric is valid for this subset object.

        A hydrofabric is valid if it has sufficient data to retrieve or derive <i>appropriate</i> ::class:`Catchment`
        and ::class:`Nexus` objects to represent all the catchments and nexuses of this subset object.  As such, a valid
        hydrofabric will recognize all catchment and nexus ids making up this subset.

        Parameters
        ----------
        hydrofabric : Optional[Hydrofabric]
            A hydrofabric in which to determine validity, interpreted as the object's own hydrofabric if ``None``.

        Returns
        -------
        bool
            ``True`` if the hydrofabric has sufficient data, in format and content, for this subset, or ``False``
            otherwise.
        """
        if hydrofabric is None:
            hydrofabric = self.hydrofabric
        for cid in self.catchment_ids:
            if not hydrofabric.is_catchment_recognized(cid):
                return False
        for nid in self.nexus_ids:
            if not hydrofabric.is_nexus_recognized(nid):
                return False
        return True
