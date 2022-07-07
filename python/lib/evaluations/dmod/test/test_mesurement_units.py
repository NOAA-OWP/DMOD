import unittest
import random

from ..evaluations import measurement_units

DELTA = 0.0001


class ManualConversion:
    def __init__(
            self,
            from_unit: str,
            to_unit: str,
            factor: float = None,
            initial_addition: float = None,
            final_addition: float = None
    ):
        self.from_unit = from_unit
        self.to_unit = to_unit
        self.factor = factor if factor else 1
        self.initial_addition = initial_addition if initial_addition else 0
        self.final_addition = final_addition if final_addition else 0

    def __call__(self, value: float, *args, **kwargs):
        return ((value + self.initial_addition) * self.factor) + self.final_addition

    def __str__(self):
        return f"((x + {self.initial_addition}) * {self.factor}) + {self.final_addition}"


class TestMeasurementUnits(unittest.TestCase):

    def test_cms(self):
        unitless_quantity = random.uniform(15, 29)
        conversion_factor = 35.314666212661

        lower_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'cms')
        upper_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'CMS')

        caret_less_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'm3/s')
        divisionless_quantity = measurement_units._COMMON_CONVERTER.get_quantity(unitless_quantity, 'm3 s-1')

        self.assertEqual(lower_case_quantity.magnitude, upper_case_quantity.magnitude)
        self.assertEqual(caret_less_quantity.magnitude, upper_case_quantity.magnitude)
        self.assertEqual(divisionless_quantity, upper_case_quantity)

        self.assertEqual(lower_case_quantity.magnitude, unitless_quantity)
        self.assertEqual(upper_case_quantity.magnitude, unitless_quantity)
        self.assertEqual(caret_less_quantity.magnitude, unitless_quantity)
        self.assertEqual(divisionless_quantity.magnitude, unitless_quantity)

        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'cms', 'm^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'CMS', 'm^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'm3/s', 'm^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.convert(unitless_quantity, "m3 s-1", "m^3/s")
        )

        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'cms', 'm^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'CMS', 'm^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'm3/s', 'm^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'm3 s-1', 'm^3/s'))

        manual_conversion = unitless_quantity * conversion_factor
        converted_lower_case_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'cms', 'ft^3/s')
        converted_upper_case_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'CMS', 'ft^3/s')
        converted_caretless_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'm3/s', 'ft^3/s')
        converted_divisionless_quantity = measurement_units._COMMON_CONVERTER.convert(unitless_quantity, "m3 s-1", "ft^3/s")

        self.assertAlmostEqual(manual_conversion, converted_lower_case_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_upper_case_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_caretless_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_divisionless_quantity, delta=DELTA)

        self.assertEqual(converted_lower_case_quantity, converted_upper_case_quantity)
        self.assertEqual(converted_upper_case_quantity, converted_caretless_quantity)
        self.assertEqual(converted_divisionless_quantity, converted_upper_case_quantity)

    def test_cfs(self):
        unitless_quantity = random.uniform(8, 23)
        conversion_factor = 1 / 35.314666212661

        lower_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'cfs')
        upper_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'CFS')

        caret_less_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'ft3/s')
        divisionless_quantity = measurement_units._COMMON_CONVERTER.get_quantity(unitless_quantity, 'ft3 s-1')

        self.assertEqual(lower_case_quantity.magnitude, upper_case_quantity.magnitude)
        self.assertEqual(caret_less_quantity.magnitude, upper_case_quantity.magnitude)
        self.assertEqual(divisionless_quantity, upper_case_quantity)

        self.assertEqual(lower_case_quantity.magnitude, unitless_quantity)
        self.assertEqual(upper_case_quantity.magnitude, unitless_quantity)
        self.assertEqual(caret_less_quantity.magnitude, unitless_quantity)
        self.assertEqual(divisionless_quantity.magnitude, unitless_quantity)

        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'cfs', 'ft^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'CFS', 'ft^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'ft3/s', 'ft^3/s')
        )
        self.assertEqual(
                unitless_quantity,
                measurement_units._COMMON_CONVERTER.convert(unitless_quantity, "ft3 s-1", "ft^3/s")
        )

        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'cfs', 'ft^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'CFS', 'ft^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'ft3/s', 'ft^3/s'))
        self.assertEqual(unitless_quantity, measurement_units.convert(unitless_quantity, 'ft3 s-1', 'ft^3/s'))

        manual_conversion = unitless_quantity * conversion_factor
        converted_lower_case_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'cfs', 'm^3/s')
        converted_upper_case_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'CFS', 'm^3/s')
        converted_caretless_quantity = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'ft3/s', 'm^3/s')
        converted_divisionless_quantity = measurement_units._COMMON_CONVERTER.convert(unitless_quantity, "ft3 s-1", "m^3/s")

        self.assertAlmostEqual(manual_conversion, converted_lower_case_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_upper_case_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_caretless_quantity, delta=DELTA)
        self.assertAlmostEqual(manual_conversion, converted_divisionless_quantity, delta=DELTA)

        self.assertEqual(converted_lower_case_quantity, converted_upper_case_quantity)
        self.assertEqual(converted_upper_case_quantity, converted_caretless_quantity)
        self.assertEqual(converted_divisionless_quantity, converted_upper_case_quantity)

    def test_kcfs(self):
        unitless_quantity = 15
        cms_conversion_factor = 1000 / 35.314666212661
        cfs_conversion_factor = 1000.0

        expected_cms = 424.752705
        expected_cfs = 15000

        lower_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'kcfs')
        upper_case_quantity = measurement_units._COMMON_CONVERTER.registry.Quantity(unitless_quantity, 'KCFS')

        self.assertEqual(lower_case_quantity.magnitude, upper_case_quantity.magnitude)

        self.assertEqual(lower_case_quantity.magnitude, unitless_quantity)
        self.assertEqual(upper_case_quantity.magnitude, unitless_quantity)

        manual_cms_conversion = unitless_quantity * cms_conversion_factor
        manual_cfs_conversion = unitless_quantity * cfs_conversion_factor

        self.assertAlmostEqual(expected_cfs, manual_cfs_conversion)
        self.assertAlmostEqual(expected_cms, manual_cms_conversion)

        converted_cfs = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'kcfs', 'ft^3/s')
        converted_cms = measurement_units._COMMON_CONVERTER.registry.convert(unitless_quantity, 'KCFS', 'm^3/s')

        self.assertAlmostEqual(manual_cfs_conversion, converted_cfs, delta=DELTA)
        self.assertAlmostEqual(manual_cms_conversion, converted_cms, delta=DELTA)

    def test_cross_conversion(self):
        cross_conversions = [
            ManualConversion('ft', 'in', factor=12),
            ManualConversion('in', 'ft', factor=1/12),
            ManualConversion('m', 'in', factor=39.3700787402),
            ManualConversion('inch', 'meter', factor=1/39.3700787402),
            ManualConversion('kcfs', 'CFS', factor=1000),
            ManualConversion('m3 s-1', 'CMS', factor=1),
            ManualConversion('ft3 s-1', 'm3 s-1', factor=1/35.314666212661),
            ManualConversion('fahrenheit', 'celsius', factor=5/9, initial_addition=-32),
            ManualConversion('celsius', 'fahrenheit', factor=9/5, final_addition=32)
        ]

        for cross in cross_conversions:
            value = random.uniform(8.4, 29.1)

            manual_conversion = cross(value)
            library_conversion = measurement_units.convert(value, cross.from_unit, cross.to_unit)

            self.assertAlmostEqual(manual_conversion, library_conversion)


if __name__ == '__main__':
    unittest.main()
