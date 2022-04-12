import typing
import numbers
import pint.registry


class UnitConverter:
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
        
    def convert(self, value, from_unit: str, to_unit: str):
        from_unit = self.__unsupported_to_supported_units.get(from_unit, from_unit)
        to_unit = self.__unsupported_to_supported_units.get(to_unit, to_unit)
        
        return self.__registry.convert(value, from_unit, to_unit)

    def get_quantity(self, value, value_type: str) -> pint.Quantity:
        value_type = self.__unsupported_to_supported_units.get(value_type, value_type)

        return self.__registry.Quantity(value, value_type)
    
    @property
    def unsupported_to_supported_units(self) -> typing.Dict[str, str]:
        return self.__unsupported_to_supported_units.copy()

    @property
    def registry(self) -> pint.registry.UnitRegistry:
        return self.__registry
    

converter = UnitConverter()


def convert(value: numbers.Number, from_unit: str, to_unit: str):
    return converter.convert(value, from_unit, to_unit)
