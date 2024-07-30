from __future__ import annotations

from typing import Optional, TypeVar

from .enum import PydanticEnum

_E = TypeVar('_E')


def _get_from_name(enum_type: _E, name: Optional[str], strict: bool = False) -> Optional[_E]:
    """
    Get the value of the given enum type for the given name string, potentially falling back to a default.

    Get the appropriate value corresponding to the given string value name (trimming whitespace), falling back to
    the default from :method:`get_default_selection` if an unrecognized or ``None`` value is received.

    Parameters
    ----------
    enum_type: _E
        The enum type, expected to only be one of the types defined in the same module as the function.
    name: Optional[str]
        The expected string name corresponding to the desired value.
    strict: bool
        Whether strict parsing should be done, in which case unrecognized or invalid ``name`` parameter values will
        return ``None`` instead of the default type.

    Returns
    -------
    Optional[_E]
        The associated enum value, when the ``name`` arg matches; otherwise, either the default value when
        ``strict`` is ``False``, or ``None`` when ``strict`` is ``True``.
    """
    if not isinstance(name, str) or not name:
        return None if strict else enum_type.get_default_selection()

    # Adjust literal name string param value to generalize a little better
    adjusted_name = name.strip().replace('-', '_').upper()

    for enum_val in enum_type:
        # Do similar generalizing for enum name values
        if enum_val.name.replace('-', '_').upper() == adjusted_name:
            return enum_val

    return None if strict else enum_type.get_default_selection()


class AllocationParadigm(PydanticEnum):
    """
    The general strategies used when finding and obtaining compute assets from different resources for allocations.

    The values are as follows:
        FILL_NODES  - obtain allocations of assets by proceeding through resources in some order, getting either the max
                      possible allocation from the current resource or an allocation that fulfills the outstanding need,
                      until the sum of assets among all received allocations is sufficient
        ROUND_ROBIN - obtain allocations of assets from available resource nodes in a round-robin manner
        SINGLE_NODE - require all allocation of assets to be from a single resource/host
    """

    FILL_NODES = 0
    ROUND_ROBIN = 1
    SINGLE_NODE = 2

    @classmethod
    def get_default_selection(cls) -> AllocationParadigm:
        """
        Get the default fallback value select to use in various situation, which is ``ROUND_ROBIN``.

        Returns
        -------
        AllocationParadigm
            The ``ROUND_ROBIN`` value.
        """
        # Must hard code something, since get_from_name potentially has a nested call back to this
        #return cls.SINGLE_NODE
        return cls.ROUND_ROBIN

    @classmethod
    def get_from_name(cls, name: Optional[str], strict: bool = False) -> Optional[AllocationParadigm]:
        """
        Get the value for the given name string, potentially falling back to the default if the arg doesn't match.

        Get the appropriate value corresponding to the given string value name (trimming whitespace), falling back to
        the default from :method:`get_default_selection` if an unrecognized or ``None`` value is received.

        Parameters
        ----------
        name: Optional[str]
            The expected string name corresponding to the desired value.

        strict: bool
            Whether strict parsing should be done, in which case unrecognized or invalid ``name`` parameter values will
            return ``None`` instead of the default type.

        Returns
        -------
        Optional[AllocationParadigm]
            The associated enum value, when the ``name`` arg matches; otherwise, either the default value when
            ``strict`` is ``False``, or ``None`` when ``strict`` is ``True``.
        """
        return _get_from_name(enum_type=cls, name=name, strict=strict)


class AllocationAssetGrouping(PydanticEnum):
    """
    Strategy for how compute assets are grouped together when allocating from a resource.

    Resource allocation conforms to one of several :class:`AllocationParadigm` values that indicate the way in which
    assets are gathered from resource nodes:  e.g., ``SINGLE_NODE``.  However, the paradigm values do not necessarily
    encapsulate well the manner in which the assets should be grouped together into the allocations themselves.  This
    type serves that purpose.

    For example, consider a job that request 5 CPUs.  One might want a single allocation, which would lead to one job
    worker with access to all 5 CPUs, potentially allowing the worker to spawn subprocesses.  This would be indicated
    with the ``BUNDLE`` value.

    Alternatively, one might instead want 5 individual allocations and workers, with each worker only having a single
    CPU and single process running in isolation; this would be indicated with the ``SILO`` value.
    """

    BUNDLE = 0
    """ Bundle all compute assets from any single node into a single allocation. """
    SILO = 1
    """ Evenly divide the compute assets taking from any single resource node among many allocations. """

    @classmethod
    def get_default_selection(cls) -> AllocationAssetGrouping:
        """
        Get the default fallback value select to use in various situation, which is ``BUNDLE``.

        Returns
        -------
        AllocationAssetGrouping
            The ``BUNDLE`` value.
        """
        return cls.BUNDLE

    @classmethod
    def get_from_name(cls, name: Optional[str], strict: bool = False) -> Optional[AllocationAssetGrouping]:
        """
        Get the value for the given name string, potentially falling back to the default if the arg doesn't match.

        Get the appropriate value corresponding to the given string value name (trimming whitespace), falling back to
        the default from :method:`get_default_selection` if an unrecognized or ``None`` value is received.

        Parameters
        ----------
        name: Optional[str]
            The expected string name corresponding to the desired value.

        strict: bool
            Whether strict parsing should be done, in which case unrecognized or invalid ``name`` parameter values will
            return ``None`` instead of the default type.

        Returns
        -------
        Optional[AllocationAssetGrouping]
            The associated enum value, when the ``name`` arg matches; otherwise, either the default value when
            ``strict`` is ``False``, or ``None`` when ``strict`` is ``True``.
        """
        return _get_from_name(enum_type=cls, name=name, strict=strict)
