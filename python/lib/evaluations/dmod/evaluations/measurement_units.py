import typing
import numbers
import pint.registry

_T = typing.TypeVar("_T")


class UnitConverter:
    """
    A wrapper for a pint conversion registry containing common, yet abnormal units
    """
    def __init__(self, synonyms: typing.Dict[str, str] = None):
        self.__unsupported_to_supported_units = {
            "m3 s-1": "m^3/s",
            "ft3 s-1": "ft^3/s",
            "m3/s": "m^3/s",
            "ft3/s": "ft^3/s"
        }

        if synonyms:
            self.__unsupported_to_supported_units.update(synonyms)

        self.__registry = pint.registry.UnitRegistry()

        self.__registry.define("m3 = m^3")
        self.__registry.define("ft3 = ft^3")

        self.__registry.define("cfs = ft^3/s")
        self.__registry.define("CFS = ft^3/s")

        self.__registry.define("KCFS = 1000 * cfs")
        self.__registry.define("kcfs = 1000 * cfs")

        self.__registry.define("cms = m^3/s")
        self.__registry.define("CMS = m^3/s")

    def convert(self, value: _T, from_unit: str, to_unit: str) -> _T:
        """
        Converts the amount of the first unit to an amount of the second

        Args:
            value: The original amount of the original unit
            from_unit: The unit describing the original magnitude of the value
            to_unit: The unit to convert the original value into

        Returns:
            The converted amount
        """
        from_unit = self.__unsupported_to_supported_units.get(from_unit, from_unit)
        to_unit = self.__unsupported_to_supported_units.get(to_unit, to_unit)

        return self.__registry.convert(value, from_unit, to_unit)

    def get_quantity(self, value: _T, value_type: str) -> pint.Quantity:
        """
        Converts a value into a specified Quantity object

        >>> example = UnitConverter()
        >>> quantity = example.get_quantity(5.48, 'ft3 s-1')
        >>> similar_quantity = example.registry.Quantity(5.48, 'ft3/s')
        >>> similar_quantity.magnitude == quantity.magnitude
        True
        >>> similar_quantity.units == quantity.units
        True
        >>> similar_quantity == quantity
        True
        >>> dissimilar_quantity = example.registry.Quantity(5.48, 'm3 s-1')
        >>> dissimilar_quantity.magnitude == quantity.magnitude
        False
        >>> dissimilar_quantity.units == quantity.units
        False
        >>> dissimilar_quantity == quantity
        False

        NOTE: Quantity objects may be used just like regular values, but with additional logic and functions.

        Args:
            value: The amount in the Quantity
            value_type: The unit of the Quantity

        Returns:

        """
        value_type = self.__unsupported_to_supported_units.get(value_type, value_type)

        return self.__registry.Quantity(value, value_type)

    @property
    def unsupported_to_supported_units(self) -> typing.Dict[str, str]:
        """
        Creates a copy of the mapping from specialized unit descriptors `not` supported by pint to matching
        unit descriptors that ARE supported by pint

        The mapping just links unsupported synonyms, like "m3 s-1" => "m^3/s". "m3 s-1" may be considered an oddball,
        but it IS used by data sources that this library needs to support

        Returns:
            The mapping from specialized unit descriptors `not` supported by pint to matching unit descriptors
            that ARE supported by pint
        """
        return self.__unsupported_to_supported_units.copy()

    @property
    def registry(self) -> pint.registry.UnitRegistry:
        """
        Returns:
            The raw pint registry used by the converter
        """
        return self.__registry


_COMMON_CONVERTER = UnitConverter()


def convert(value: numbers.Number, from_unit: str, to_unit: str):
    """
    Converts a number from one unit into another

    Args:
        value: The value to convert
        from_unit: The current unit of measurement
        to_unit: The desired unit of measurement

    Returns:
        A new number reflecting a change of measurement unit
    """
    return _COMMON_CONVERTER.convert(value, from_unit, to_unit)
