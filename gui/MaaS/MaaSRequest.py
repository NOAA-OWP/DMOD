"""
Lays out details describing how a request may be created and the different types of requests

@author: Chris Tubbs
"""

import json


def get_available_models() -> dict:
    """
    :return: The names of all models mapped to their class
    """
    available_models = dict()

    for subclass in MaaSRequest.__subclasses__():  # type: MaaSRequest
        available_models[subclass.model_name] = subclass

    return available_models


def get_available_outputs() -> set:
    """
    :return: A collection of all valid outputs across any model
    """
    all_outputs = set()

    for model in get_available_models().values():  # type: MaaSRequest
        all_outputs = all_outputs.union(set(model.get_output_variables()))

    return all_outputs


def get_distribution_types() -> set:
    """
    :return: The distribution types used across any model
    """
    all_types = set()

    for model in get_available_models().values():
        all_types = all_types.union(set(model.get_distribution_types()))

    return all_types


class Scalar(object):
    """
    Represents a parameter value that is bound to a single number
    """
    def __init__(self, scalar: int):
        """
        :param int scalar: The value for the parameter
        """
        self.scalar = scalar

    def to_dict(self):
        return {'scalar': self.scalar}

    def __str__(self):
        return self.scalar

    def __repr__(self):
        return self.__str__()


class Distribution(object):
    """
    Represents the definition of a distribution of numbers
    """
    def __init__(self, minimum: int = 0, maximum: int = 0, distribution_type: str = 'normal'):
        """
        :param int minimum: The lower bound for the distribution
        :param int maximum: The upper bound of the distribution
        :param str distribution_type: The type of the distribution
        """
        self.minimum = minimum
        self.maximum = maximum
        self.distribution_type = distribution_type

    def to_dict(self):
        return {'distribution': {'min': self.minimum, 'max': self.maximum, 'type': self.distribution_type}}

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()


class MaaSRequest(object):
    """
    The base class underlying all types of MaaS requests
    """

    model_name = None
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover'
    ]
    """(:class:`list`) The collection of parameters to use"""

    max_distribution = 0
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = 10
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 10
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'lognormal'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    output_variables = [
        'streamflow'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    def __init__(self, version: float, output: str, parameters: dict, session_secret: str):
        """
        :param float version: The version of the model to use
        :param str output: The name of the variable to generate numbers for
        :param dict parameters: A mapping between parameters to configure and their scalar or distribution configurations
        :param str session_secret: The session secret for the right session when communicating with the MaaS request handler
        """

        # If this model doesn't generate the output, we want to fail
        if output not in get_available_outputs():
            raise ValueError(
                "{} is not an allowable output; "
                "the only acceptable outputs are: {}".format(output, get_available_outputs())
            )

        # We want to check each parameter
        for parameter in parameters:
            # If the parameter isn't approved, we want to fail
            if parameter not in self.get_parameters():
                raise ValueError(
                    '{} is not a valid parameter; '
                    'the only acceptable parameters are: {}'.format(parameter, self.get_parameters())
                )

            # Validate the parameter based on scalar rules if it's a scalar
            if isinstance(parameters[parameter], Scalar):
                self.validate_scalar(parameter, parameters[parameter])
            elif isinstance(parameters[parameter], Distribution):
                # Validate the parameter based on distribution rules if it's a distribution
                self.validate_distribution(parameter, parameters[parameter])
            else:
                # Raise an exception since we only approve of Scalar or Distribution parameters
                raise ValueError(
                    "{} is not a scalar or distribution.".format(parameter)
                )

        self.version = version
        self.output = output
        self.parameters = parameters
        self.session_secret = session_secret

    @classmethod
    def get_distribution_types(cls) -> list:
        """
        :return: All distribution types that this model uses
        """
        return cls.distribution_types

    @classmethod
    def get_model_name(cls) -> str:
        """
        :return: The name of this model
        """
        return cls.model_name

    @classmethod
    def get_parameters(cls) -> list:
        """
        :return: The parameters for the model that may be configured
        """
        return cls.parameters

    @classmethod
    def get_output_variables(cls) -> list:
        """
        :return: The variables that the model is able to generate
        """
        return cls.output_variables

    @classmethod
    def validate_scalar(cls, parameter_name: str, scalar: Scalar):
        """
        Test the scalar value to see if it is compatible with the model

        A different way to approach this might be to make the parameter list a mapping between the
        parameters and their boundaries (i.e. shifting the min/max scalar value into the map). This will allow
        behavior that has different bounds between parameters. For instance, 'land_cover' could have a max scalar of
        8 while 'hydro_whatever' might have a max scalar of 72.

        :param str parameter_name: The name of the parameter with the scalar
        :param Scalar scalar: The value for the parameter
        :raises ValueError: Raised in the event that the scalar is incompatible with the model
        """
        if scalar.scalar < cls.min_scalar:
            raise ValueError(
                "{} is too low of a scalar value for {} for {} models. It must be greater than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
                    cls.model_name,
                    cls.min_scalar
                )
            )
        elif scalar.scalar > cls.max_scalar:
            raise ValueError(
                "{} is too high of a scalar value for {} for {} models. It must be less than or equal to {}.".format(
                    scalar.scalar,
                    parameter_name,
                    cls.model_name,
                    cls.max_scalar
                )
            )

    @classmethod
    def validate_distribution(cls, parameter_name: str, distribution: Distribution):
        """
        Test the distribution value to see if it is compatible with the model

        A different way to approach this might be to make the parameter list a mapping between the
        parameters and their boundaries (i.e. shifting the min/max scalar value into the map). This will allow
        behavior that has different bounds between parameters. For instance, 'land_cover' could have a max scalar of
        8 while 'hydro_whatever' might have a max scalar of 72.

        :param str parameter_name: The name of the parameter with the distribution
        :param Distribution distribution: The value for the parameter
        :raises ValueError: Raised in the event that the distribution is incompatible with the model
        """
        messages = list()

        if distribution.minimum < cls.min_distribution:
            messages.append(
                "{} is too low of a distribution value for {} for {} models. "
                "It must be greater than or equal to {}".format(
                    distribution.minimum,
                    parameter_name,
                    cls.model_name,
                    cls.min_distribution
                )
            )

        if distribution.minimum > cls.max_distribution:
            messages.append(
                "{} is too high of a distribution value for {} for {} models. "
                "It must be less than or equal to {}".format(
                    distribution.maximum,
                    parameter_name,
                    cls.model_name,
                    cls.max_distribution
                )
            )

        if distribution.minimum > distribution.maximum:
            messages.append(
                "The minimum value for the distribution ({}) is higher than the maximum ({}) "
                "for the {} parameter".format(distribution.minimum, distribution.maximum, parameter_name)
            )

        if distribution.distribution_type not in cls.distribution_types:
            messages.append(
                "The {} distribution type may not be used for the {} parameter".format(
                    distribution.distribution_type,
                    parameter_name
                )
            )

        if len(messages) > 0:
            raise ValueError(". ".join(messages))

    @classmethod
    def validate_output(cls, output: str):
        """
        :param str output: The type of output that we want the model to generate
        :raises ValueError if the model cannot generate the given output type
        """
        if output not in cls.output_variables:
            raise ValueError("{} is not supported by the {} model.".format(output, cls.model_name))

    def to_dict(self) -> dict:
        """
        Converts the request to a dictionary that may be passed to web requests

        Will look like:

        {
            'model': {
                'NWM': {
                    'version': 2.1,
                    'output': 'streamflow',
                    'parameters': [
                        {
                            'land_cover': {
                                'distribution': {
                                    'min': 0,
                                    'max': 10,
                                    'type': 'lognormal'
                                }
                            }
                        }
                    ]
                }
            }
        }

        :return: A dictionary containing all the data in such a way that it may be used by a web request
        """
        model = dict()
        model[self.get_model_name()] = dict()
        model[self.get_model_name()]['version'] = self.version
        model[self.get_model_name()]['output'] = self.output
        model[self.get_model_name()]['parameters'] = dict()
        model[self.get_model_name()]['session-secret'] = self.session_secret

        for parameter in self.parameters:
            model[self.get_model_name()]['parameters'].update({parameter: self.parameters[parameter].to_dict()})

        return {'model': model}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class NWMRequest(MaaSRequest):
    model_name = 'NWM'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'streamflow'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 10
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = 0
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 10
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'lognormal'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    def __init__(self, version: float = 0.0, output: str = 'streamflow', parameters: dict = None):
        super(NWMRequest, self).__init__(version, output, parameters)


class XYZRequest(MaaSRequest):
    """
    Represents requests that may be made to the XYZ model
    """
    model_name = 'XYZ'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'hydraulic_conductivity',
        'land_cover',
        'nudge'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'streamflow',
        'precipitation'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 15
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = -2
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 5
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    def __init__(self, version: float = 0.0, output: str = 'streamflow', parameters: dict = None):
        super(XYZRequest, self).__init__(version, output, parameters)


class YetAnotherRequest(MaaSRequest):
    """
    Represents requests that may be made for the YetAnother model
    """
    model_name = 'YetAnother'
    """(:class:`str`) The name of the model to be used"""

    parameters = [
        'This',
        'Is',
        'An',
        'Example'
    ]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = [
        'chance_of_earthquake',
        'rain_chance'
    ]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 15
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = -2
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 5
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = [
        'normal',
        'wonky',
        'exponential'
    ]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    def __init__(self, version: float = 0.0, output: str = 'streamflow', parameters: dict = None):
        super(YetAnotherRequest, self).__init__(version, output, parameters)


def get_parameters() -> dict:
    """
    Maps each model to the natural and human readable forms of all of their parameters

    Say we have the models:

    * NWM : hydro_whatever, land_cover
    * XYZ : hydro_whatever, land_cover

    This will give us:

    {
        'NWM': [{'value': 'hydro_whatever', 'name': 'Hydro Whatever'}, {'value': 'land_cover', 'name': 'Land Cover'}],

        'XYZ': [{'value': 'hydro_whatever', 'name': 'Hydro Whatever'}, {'value': 'land_cover', 'name': 'Land Cover'}]
    }

    :return: A mapping between the name of the model and actual/human readable names of their parameters
    """
    parameters = dict()

    for model_name, model in get_available_models().items():  # type: str, MaaSRequest
        # Say our model is 'NWM'
        model_parameters = list()

        for parameter in model.get_parameters():
            # Say out parameter is 'land_cover'
            parameter_value = dict()
            parameter_value['name'] = " ".join(parameter.split("_")).title()
            parameter_value['value'] = parameter

            # We'll now have {'name': 'Land Cover', 'value': 'land_cover'}, which we'll stick in the list for 'NWM'
            model_parameters.append(parameter_value)

        # This will give us: {'NWM': [{'name': 'Land Cover', 'value': 'land_cover'}]}
        parameters[model_name] = model_parameters

    return parameters


def get_request(model: str, version: float = 0.0, output: str = 'streamflow', parameters: dict = None,
                session_secret: str = '') -> MaaSRequest:
    """
    Converts a basic definition of a request into a proper request object

    :param str model: The type of model we want to run
    :param float version: The version of the model to run
    :param str output: What we want the model to generate
    :param dict parameters: A mapping of all the parameters for the model that we want to set and their values
    :param str session_secret: The session secret for the right session when communicating with the MaaS request handler
    :return: A request object that may be converted into context data for a web request
    """
    if model not in get_available_models():
        raise ValueError(
            "{} is not an allowable model; "
            "the only acceptable models are: {}".format(model, get_available_models())
        )

    if parameters is None:
        parameters = dict()

    return get_available_models()[model](version, output, parameters, session_secret)
