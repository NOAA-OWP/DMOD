import json
import unittest
from .validator import JsonRequestValidator
from pathlib import Path


class TestJsonRequestValidator(unittest.TestCase):
    """
    Test case for the :class:`JsonRequestValidator` class.

    Attributes
    ----------
    invalid_request_data : object
        Deserialized JSON object created from the invalid serialized request example file.
    valid_request_data : object
        Deserialized JSON object created from the valid serialized request example file.
    validator : :class:`JsonRequestValidator`
        JsonRequestValidator instance to test

    """

    def setUp(self):
        current_dir = Path(__file__).resolve().parent
        json_schemas_dir = current_dir.joinpath('schemas')
        valid_request_json_file = json_schemas_dir.joinpath('request.json')
        invalid_request_json_file = json_schemas_dir.joinpath('request_bad.json')

        with valid_request_json_file.open(mode='r') as valid_test_file:
            self.valid_request_data = json.load(valid_test_file)

        with invalid_request_json_file.open(mode='r') as invalid_test_file:
            self.invalid_request_data = json.load(invalid_test_file)

        self.validator = JsonRequestValidator()

    def test_validate_request_1(self):
        """
        Test that the base :attr:`valid_request_json_file` is valid.
        """
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_1a(self):
        """
        Test that the base :attr:`valid_request_json_file` is valid even after removing the 'client_id' property if
        it is present.
        """
        if 'client_id' in self.valid_request_data:
            self.valid_request_data.pop('client_id')
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_1b(self):
        """
        Test that the base :attr:`valid_request_json_file` is invalid after setting an invalid 'client_id' value.
        """
        self.valid_request_data['client_id'] = 'purple'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_2(self):
        """
        Test that :attr:`valid_request_json_file` is valid after setting a valid 'client_id' value.
        """
        self.valid_request_data['client_id'] = 1
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_3(self):
        """
        Test that the base :attr:`invalid_request_json_file` is invalid.
        """
        self.assertFalse(self.validator.validate_request(self.invalid_request_data)[0])

    def test_validate_request_4(self):
        """
        Test that :attr:`invalid_request_json_file` is invalid, even after setting a valid 'client_id' value.
        """
        self.invalid_request_data['client_id'] = 1
        self.assertFalse(self.validator.validate_request(self.invalid_request_data)[0])

    def test_validate_request_5(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after removing the 'model' property.
        """
        self.valid_request_data.pop('model')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_6(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'model' property has its 'NWM' sub-property
        renamed/re-keyed with an invalid name.
        """
        self.valid_request_data['model']['not_NWM'] = self.valid_request_data['model'].pop('NWM')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_7(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'model' property has its 'NWM' sub-property
        removed.
        """
        self.valid_request_data['model'].pop('NWM')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_8(self):
        """
        Test that :attr:`valid_request_json_file` is valid even if the 'domain' property is removed.
        """
        self.valid_request_data.pop('domain')
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_9(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'domain' property is set to an invalid value of
        one space character.
        """
        self.valid_request_data['domain'] = ' '
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_9a(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'domain' property is set to an invalid value of
        an empty string.
        """
        self.valid_request_data['domain'] = ''
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_9b(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'domain' property is set to an invalid value of
        some non-empty, non-whitespace string.
        """
        self.valid_request_data['domain'] = 'blah'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_9c(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'domain' property is set to an invalid value of
        the valid string plus a whitespace character.
        """
        self.valid_request_data['domain'] = self.valid_request_data['domain'] + ' '
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_9d(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after the 'domain' property is set to an invalid value of
        the valid string plus an arbitrary, non-empty suffix string.
        """
        self.valid_request_data['domain'] = self.valid_request_data['domain'] + 'blah'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_11(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after adding an invalid property.
        """
        self.valid_request_data['unknown'] = 'purple'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_12(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after removing the 'version' sub-property from 'model.NWM'.
        """
        self.valid_request_data['model']['NWM'].pop('version')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_12a(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'version' sub-property from 'model.NWM'
        to an empty string.
        """
        self.valid_request_data['model']['NWM']['version'] = ''
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_12b(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'version' sub-property from 'model.NWM'
        to None.
        """
        self.valid_request_data['model']['NWM']['version'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_12c(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'version' sub-property from 'model.NWM'
        to an analogous representation of a valid value but of an invalid type (i.e., string instead of number).
        """
        self.valid_request_data['model']['NWM']['version'] = '2.0'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_12d(self):
        """
        Test that :attr:`valid_request_json_file` is valid after setting the 'version' sub-property from 'model.NWM'
        to a valid value.
        """
        self.valid_request_data['model']['NWM']['version'] = 2.1
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_13(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after removing the 'output' sub-property from 'model.NWM'.
        """
        self.valid_request_data['model']['NWM'].pop('output')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_13a(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'output' sub-property from 'model.NWM'
        to an empty string.
        """
        self.valid_request_data['model']['NWM']['output'] = ''
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_13b(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'output' sub-property from 'model.NWM'
        to None.
        """
        self.valid_request_data['model']['NWM']['output'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_13c(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after setting the 'output' sub-property from 'model.NWM'
        to an invalid value.
        """
        self.valid_request_data['model']['NWM']['output'] = self.valid_request_data['model']['NWM']['output'] + 'blah'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_13d(self):
        """
        Test that :attr:`valid_request_json_file` is valid after setting the 'output' sub-property from 'model.NWM'
        to a valid value.
        """
        self.valid_request_data['model']['NWM']['output'] = 'streamflow'
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_14(self):
        """
        Test that :attr:`valid_request_json_file` is invalid after removing the 'parameters' sub-property from
        'model.NWM'.
        """
        self.valid_request_data['model']['NWM'].pop('parameters')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_14a(self):
        """
        Test :attr:`valid_request_json_file` is valid after removing any sub-properties from 'model.NWM.parameters'.
        """
        self.valid_request_data['model']['NWM']['parameters'].clear()
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_14b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if some unrecognized sub-property is added to
        'model.NWM.parameters'.
        """
        params_property = self.valid_request_data['model']['NWM']['parameters']
        params_property['invalid'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_15(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'hydraulic_conductivity' sub-property from
        'model.NWM.parameters' is renamed to some invalid property name.
        """
        params_property = self.valid_request_data['model']['NWM']['parameters']
        params_property['invalid'] = params_property.pop('hydraulic_conductivity')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_15a(self):
        """
        Test :attr:`valid_request_json_file` is invalid if some unrecognized sub-property is added to
        'model.NWM.parameters.hydraulic_conductivity'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property['unknown'] = 'blah'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_15b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if all sub-properties are removed from
        'model.NWM.parameters.hydraulic_conductivity'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.clear()
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    # TODO: revisit why this doesn't hold true (likely due to something related to the nested definition for
    #  'distribution' in the nwm.model.parameter.schema.json file)
    # def test_validate_request_16(self):
    #     """
    #     Test :attr:`valid_request_json_file` is invalid if some unrecognized sub-property is added to
    #     'model.NWM.parameters.hydraulic_conductivity.distribution'.
    #     """
    #     req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
    #     req_property['something'] = 'blah'
    #     result = self.validator.validate_request(self.valid_request_data)
    #     self.assertFalse(result[0])

    def test_validate_request_16a(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'min' sub-property is removed from
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('min')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if None is set for the value of the 'min' sub-property of
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16c(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value below the valid range is set for the value of the
        'min' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = -1
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16d(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value above the valid range is set for the value of the
        'min' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 11
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16e(self):
        """
        Test :attr:`valid_request_json_file` is valid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 5
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16f(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a float).
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 5.1
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_16g(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a string).
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = '5.0'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17a(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'max' sub-property is removed from
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('max')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if None is set for the value of the 'max' sub-property of
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17c(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value below the valid range is set for the value of the
        'max' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = -1
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17d(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value above the valid range is set for the value of the
        'max' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 11
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17e(self):
        """
        Test :attr:`valid_request_json_file` is valid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 5
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17f(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a float).
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 5.1
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_17g(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a string).
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = '5.0'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_18a(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'type' sub-property is removed from
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('type')
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_18b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if None is set for the value of the 'type' sub-property of
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = None
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_18c(self):
        """
        Test :attr:`valid_request_json_file` is invalid if an invalid value is set for the value of the 'type'
        sub-property of 'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'invalid'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_18d(self):
        """
        Test :attr:`valid_request_json_file` is valid if 'normal' is set for the value of the 'type' sub-property of
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'normal'
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_18e(self):
        """
        Test :attr:`valid_request_json_file` is valid if 'lognormal' is set for the value of the 'type' sub-property of
        'model.NWM.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'lognormal'
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19(self):
        """
        Test :attr:`valid_request_json_file` is valid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' is replaced with a valid 'scalar' sub-property.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = 5
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19a(self):
        """
        Test :attr:`valid_request_json_file` is invalid if a valid 'scalar' sub-property is added to
        'model.NWM.parameters.hydraulic_conductivity' with the 'distribution' sub-property still present.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property['scalar'] = 5
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19b(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property having a value below the
        allowed range.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = -1
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19c(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property having a value above the
        allowed range.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = -11
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19d(self):
        """
        Test :attr:`valid_request_json_file` is valid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property in the valid range, even
        if the value is a non-integer number.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = 5.1
        self.assertTrue(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_19e(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property that is not of a number
        type (e.g., a string that represents a number in the valid range)
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = '5'
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

    def test_validate_request_20(self):
        """
        Test :attr:`valid_request_json_file` is invalid if the 'distribution' sub-property of
        'model.NWM.parameters.hydraulic_conductivity' conforms to the schema appropriate for the 'scalar' sub-property.
        """
        req_property = self.valid_request_data['model']['NWM']['parameters']['hydraulic_conductivity']
        req_property['distribution'] = 5
        self.assertFalse(self.validator.validate_request(self.valid_request_data)[0])

