import json
import unittest
from ..communication import NWMRequestJsonValidator, SessionInitMessageJsonValidator
from pathlib import Path


class TestJsonRequestValidator(unittest.TestCase):
    """
    Test case for the :class:`JsonRequestValidator` class.

    Attributes
    ----------
    invalid_job_request_data : object
        Deserialized JSON object created from the invalid serialized request example file.
    valid_job_request_data : object
        Deserialized JSON object created from the valid serialized request example file.
    jobs_validator : :class:`JsonRequestValidator`
        JsonRequestValidator instance to test

    """

    def setUp(self):
        script_dir = Path(__file__).resolve().parent
        json_schemas_dir = script_dir.parent.joinpath('communication').joinpath('schemas')
        valid_job_request_json_file = json_schemas_dir.joinpath('request.json')
        valid_auth_request_json_file = json_schemas_dir.joinpath('auth.json')
        invalid_job_request_json_file = json_schemas_dir.joinpath('request_bad.json')

        with valid_job_request_json_file.open(mode='r') as valid_test_file:
            self.valid_job_request_data = json.load(valid_test_file)

        with invalid_job_request_json_file.open(mode='r') as invalid_test_file:
            self.invalid_job_request_data = json.load(invalid_test_file)

        with valid_auth_request_json_file.open(mode='r') as valid_test_file:
            self.valid_auth_request_data = json.load(valid_test_file)

        self.auth_validator = SessionInitMessageJsonValidator()
        self.jobs_validator = NWMRequestJsonValidator()

    def test_validate_request_1a(self):
        """
        Test that the base :attr:`valid_request_json_file` is valid.
        """
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_1b(self):
        """
        Test that the base :attr:`valid_job_request_json_file` is valid even after removing the 'client_id' property if
        it is present.
        """
        if 'client_id' in self.valid_job_request_data:
            self.valid_job_request_data.pop('client_id')
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_1c(self):
        """
        Test that the base :attr:`valid_job_request_json_file` is invalid after setting an invalid 'client_id' value.
        """
        self.valid_job_request_data['client_id'] = 'purple'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_1d(self):
        """
        Test that :attr:`valid_job_request_json_file` is valid after setting a valid 'client_id' value.
        """
        self.valid_job_request_data['client_id'] = 1
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_2a(self):
        """
        Test that the base :attr:`invalid_job_request_json_file` is invalid.
        """
        self.assertFalse(self.jobs_validator.validate(self.invalid_job_request_data)[0])

    def test_validate_request_2b(self):
        """
        Test that :attr:`invalid_job_request_json_file` is invalid, even after setting a valid 'client_id' value.
        """
        self.invalid_job_request_data['client_id'] = 1
        self.assertFalse(self.jobs_validator.validate(self.invalid_job_request_data)[0])

    def test_validate_request_3a(self):
        """
        Test that the base :attr:`valid_auth_request_json_file` is valid.
        """
        self.assertTrue(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_3b(self):
        """
        Test that the base :attr:`valid_auth_request_json_file` is valid, even if changing the username to something
        else valid.
        """
        self.valid_auth_request_data['username'] = 'somethingelsevalid'
        self.assertTrue(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_4a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after removing the 'model' property.
        """
        self.valid_job_request_data.pop('model')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_4b(self):
        """
        Test that :attr:`valid_job_request_json_file` is valid after removing the 'domain' property.
        """
        self.valid_job_request_data.pop('domain')
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_4c(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after removing the 'session-secret' property.
        """
        self.valid_job_request_data.pop('session-secret')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_5a(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after removing the 'user_secret' property.
        """
        self.valid_auth_request_data.pop('user_secret')
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_5b(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after removing the 'username' property.
        """
        self.valid_auth_request_data.pop('username')
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_6a(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after modifying the 'username' property to be too
        short.
        """
        self.valid_auth_request_data['username'] = 'short'
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_6b(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after modifying the 'username' property to be invalid.
        """
        self.valid_auth_request_data['username'] = None
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_6c(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after modifying the 'user_secret' property to be too
        short.
        """
        self.valid_auth_request_data['user_secret'] = 'short'
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_6d(self):
        """
        Test that :attr:`valid_auth_request_json_file` is invalid after modifying the 'user_secret' property to be
        invalid.
        """
        self.valid_auth_request_data['user_secret'] = 1234567890
        self.assertFalse(self.auth_validator.validate(self.valid_auth_request_data)[0])

    def test_validate_request_7a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'model' property has its 'nwm' sub-property
        renamed/re-keyed with an invalid name.
        """
        self.valid_job_request_data['model']['not_nwm'] = self.valid_job_request_data['model'].pop('nwm')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_7b(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'model' property has its 'nwm' sub-property
        removed.
        """
        self.valid_job_request_data['model'].pop('nwm')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8a(self):
        """
        Test that :attr:`valid_job_request_json_file` is valid even if the 'domain' property is removed.
        """
        self.valid_job_request_data.pop('domain')
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8b(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'domain' property is set to an invalid value
        of one space character.
        """
        self.valid_job_request_data['domain'] = ' '
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8c(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'domain' property is set to an invalid value
        of an empty string.
        """
        self.valid_job_request_data['domain'] = ''
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8d(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'domain' property is set to an invalid value
        of some non-empty, non-whitespace string.
        """
        self.valid_job_request_data['domain'] = 'blah'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8e(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'domain' property is set to an invalid value
        of the valid string plus a whitespace character.
        """
        self.valid_job_request_data['domain'] = self.valid_job_request_data['domain'] + ' '
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_8f(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after the 'domain' property is set to an invalid value
        of the valid string plus an arbitrary, non-empty suffix string.
        """
        self.valid_job_request_data['domain'] = self.valid_job_request_data['domain'] + 'blah'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_9a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after adding an invalid property.
        """
        self.valid_job_request_data['unknown'] = 'purple'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_10a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after removing the 'version' sub-property from
        'model.nwm'.
        """
        self.valid_job_request_data['model']['nwm'].pop('version')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_10b(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting the 'version' sub-property from
        'model.nwm' to an empty string.
        """
        self.valid_job_request_data['model']['nwm']['version'] = ''
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_10c(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting the 'version' sub-property from
        'model.nwm' to None.
        """
        self.valid_job_request_data['model']['nwm']['version'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_10d(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting the 'version' sub-property from
        'model.nwm' to an analogous representation of a valid value but of an invalid type (i.e., string instead of
        number).
        """
        self.valid_job_request_data['model']['nwm']['version'] = '2.0'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_10e(self):
        """
        Test that :attr:`valid_job_request_json_file` is valid after setting the 'version' sub-property from 'model.nwm'
        to a valid value.
        """
        self.valid_job_request_data['model']['nwm']['version'] = 2.1
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_11a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after removing the 'output' sub-property from
        'model.nwm'.
        """
        self.valid_job_request_data['model']['nwm'].pop('output')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_11b(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting 'output' sub-property from 'model.nwm'
        to an empty string.
        """
        self.valid_job_request_data['model']['nwm']['output'] = ''
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_11c(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting 'output' sub-property from 'model.nwm'
        to None.
        """
        self.valid_job_request_data['model']['nwm']['output'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_11d(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after setting 'output' sub-property from 'model.nwm'
        to an invalid value.
        """
        self.valid_job_request_data['model']['nwm']['output'] += 'blah'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_11e(self):
        """
        Test that :attr:`valid_job_request_json_file` is valid after setting the 'output' sub-property from 'model.nwm'
        to a valid value.
        """
        self.valid_job_request_data['model']['nwm']['output'] = 'streamflow'
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_12a(self):
        """
        Test that :attr:`valid_job_request_json_file` is invalid after removing the 'parameters' sub-property from
        'model.nwm'.
        """
        self.valid_job_request_data['model']['nwm'].pop('parameters')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_12b(self):
        """
        Test :attr:`valid_job_request_json_file` is valid after removing any sub-properties from 'model.nwm.parameters'.
        """
        self.valid_job_request_data['model']['nwm']['parameters'].clear()
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_12c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if some unrecognized sub-property is added to
        'model.nwm.parameters'.
        """
        params_property = self.valid_job_request_data['model']['nwm']['parameters']
        params_property['invalid'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_13a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'hydraulic_conductivity' sub-property from
        'model.nwm.parameters' is renamed to some invalid property name.
        """
        params_property = self.valid_job_request_data['model']['nwm']['parameters']
        params_property['invalid'] = params_property.pop('hydraulic_conductivity')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_13b(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if some unrecognized sub-property is added to
        'model.nwm.parameters.hydraulic_conductivity'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property['unknown'] = 'blah'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_13c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if all sub-properties are removed from
        'model.nwm.parameters.hydraulic_conductivity'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.clear()
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    # TODO: revisit why this doesn't hold true (likely due to something related to the nested definition for
    #  'distribution' in the nwm.model.parameter.schema.json file)
    # def test_validate_request_14a(self):
    #     """
    #     Test :attr:`valid_job_request_json_file` is invalid if some unrecognized sub-property is added to
    #     'model.nwm.parameters.hydraulic_conductivity.distribution'.
    #     """
    #     req_property = self.valid_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
    #     req_property['something'] = 'blah'
    #     result = self.validator.validate_request(self.valid_request_data)
    #     self.assertFalse(result[0])

    def test_validate_request_15a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'min' sub-property is removed from
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('min')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15b(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if None is set for the value of the 'min' sub-property of
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value below the valid range is set for the value of the
        'min' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = -1
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15d(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value above the valid range is set for the value of the
        'min' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 11
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15e(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 5
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15f(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a float).
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = 5.1
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_15g(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value in the valid range is set for the value of the
        'min' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a string).
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['min'] = '5.0'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'max' sub-property is removed from
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('max')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16b(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if None is set for the value of the 'max' sub-property of
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value below the valid range is set for the value of the
        'max' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = -1
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16d(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value above the valid range is set for the value of the
        'max' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 11
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16e(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 5
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16f(self):
        """
        Test :attr:`valid_rjob_equest_json_file` is invalid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a float).
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = 5.1
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_16g(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a value in the valid range is set for the value of the
        'max' sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution', but it is of the wrong type
        (in this case, a string).
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['max'] = '5.0'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_17a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'type' sub-property is removed from
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property.pop('type')
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_17b(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if None is set for the value of the 'type' sub-property of
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = None
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_17c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if an invalid value is set for the value of the 'type'
        sub-property of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'invalid'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_17d(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if 'normal' is set for the value of the 'type' sub-property of
        'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'normal'
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_17e(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if 'lognormal' is set for the value of the 'type' sub-property
        of 'model.nwm.parameters.hydraulic_conductivity.distribution'.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']['distribution']
        req_property['type'] = 'lognormal'
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_18a(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' is replaced with a valid 'scalar' sub-property.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = 5
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_19a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if a valid 'scalar' sub-property is added to
        'model.nwm.parameters.hydraulic_conductivity' with the 'distribution' sub-property still present.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property['scalar'] = 5
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_19b(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property having a value below the
        allowed range.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = -1
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_19c(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property having a value above the
        allowed range.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = -11
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_19d(self):
        """
        Test :attr:`valid_job_request_json_file` is valid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property in the valid range, even
        if the value is a non-integer number.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = 5.1
        self.assertTrue(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_19e(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' is replaced with a 'scalar' sub-property that is not of a number
        type (e.g., a string that represents a number in the valid range)
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property.pop('distribution')
        req_property['scalar'] = '5'
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])

    def test_validate_request_20a(self):
        """
        Test :attr:`valid_job_request_json_file` is invalid if the 'distribution' sub-property of
        'model.nwm.parameters.hydraulic_conductivity' conforms to the schema appropriate for the 'scalar' sub-property.
        """
        req_property = self.valid_job_request_data['model']['nwm']['parameters']['hydraulic_conductivity']
        req_property['distribution'] = 5
        self.assertFalse(self.jobs_validator.validate(self.valid_job_request_data)[0])
