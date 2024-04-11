from __future__ import annotations

from typing import Optional

from .enum import PydanticEnum


class AllocationParadigm(PydanticEnum):
    """
    The general strategies used when assembling and allocating compute assets from different resources.

    The values are as follows:
        FILL_NODES  - obtain allocations of assets by proceeding through resources in some order, getting either the max
                      possible allocation from the current resource or a allocation that fulfills the outstanding need,
                      until the sum of assets among all received allocations is sufficient; also, have allocations be
                      single cpu/process
        ROUND_ROBIN - obtain allocations of assets from available resource nodes in a round-robin manner; also, have
                      allocations be single cpu/process
        SINGLE_NODE - require all allocation of assets to be from a single resource/host; also, require allocations to
                      be single cpu/process
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
        if name is None or not isinstance(name, str):
            return None if strict else cls.get_default_selection()

        # Adjust literal name string param value to generalize a little better
        adjusted_name = name.strip().replace('-', '_').upper()

        for enum_val in cls:
            # Do similar generalizing for enum name values
            if enum_val.name.replace('-', '_').upper() == adjusted_name:
                return enum_val

        return None if strict else cls.get_default_selection()
