from ..parameter import Scalar
from ..distribution import Distribution


class NWMConfig:

    parameters = ["hydraulic_conductivity", "land_cover"]
    """(:class:`list`) The collection of parameters to use"""

    output_variables = ["streamflow"]
    """(:class:`list`) The collection of output variables that the model may generate"""

    max_distribution = 10
    """(:class:`int`) The maximum value for a distribution for a parameter that the model may handle"""

    min_distribution = 0
    """(:class:`int`) The minimum value for a distribution for a parameter that the model may handle"""

    min_scalar = 0
    """(:class:`int`) The minimum scalar value for a parameter that the model may handle"""

    max_scalar = 10
    """(:class:`int`) The maximum scalar value for a parameter that the model may handle"""

    distribution_types = ["normal", "lognormal"]
    """(:class:`list`) The collection of distribution types that the model may handle"""

    @classmethod
    def get_distribution_types(cls) -> list:
        """
        :return: All distribution types that this model uses
        """
        return cls.distribution_types

    @classmethod
    def get_output_variables(cls) -> list:
        """
        :return: The variables that the model is able to generate
        """
        return cls.output_variables

    @classmethod
    def get_parameters(cls) -> list:
        """
        :return: The parameters for the model that may be configured
        """
        return cls.parameters

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
                "{} is too low of a scalar value for {}. It must be greater than or equal to {}.".format(
                    scalar.scalar, parameter_name, cls.min_scalar
                )
            )
        elif scalar.scalar > cls.max_scalar:
            raise ValueError(
                "{} is too high of a scalar value for {}. It must be less than or equal to {}.".format(
                    scalar.scalar, parameter_name, cls.max_scalar
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
                "{} is too low of a distribution value for {} for. "
                "It must be greater than or equal to {}".format(
                    distribution.minimum, parameter_name, cls.min_distribution
                )
            )

        if distribution.minimum > cls.max_distribution:
            messages.append(
                "{} is too high of a distribution value for {}. "
                "It must be less than or equal to {}".format(
                    distribution.maximum, parameter_name, cls.max_distribution
                )
            )

        if distribution.minimum > distribution.maximum:
            messages.append(
                "The minimum value for the distribution ({}) is higher than the maximum ({}) "
                "for the {} parameter".format(
                    distribution.minimum, distribution.maximum, parameter_name
                )
            )

        if distribution.distribution_type not in cls.distribution_types:
            messages.append(
                "The {} distribution type may not be used for the {} parameter".format(
                    distribution.distribution_type, parameter_name
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
            raise ValueError("{} is not supported by NWM model.".format(output))

    def __init__(
        self, data_id: str, version: float, output: str, domain: str, parameters: dict
    ):
        self.data_id = data_id

        # TODO: add something to set these from a dataset
        self._version = version
        self._output = output
        self._domain = domain
        self.parameters = parameters if parameters is not None else {}

        # We want to check each parameter if they are formally defined by the model request
        if len(self.get_parameters()) > 0:
            for parameter in parameters:
                # If the parameter isn't approved, we want to fail
                if parameter not in self.get_parameters():
                    raise ValueError(
                        "{} is not a valid parameter; "
                        "the only acceptable parameters are: {}".format(
                            parameter, self.get_parameters()
                        )
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

    @property
    def version(self) -> float:
        """
        :return: the version of the model to run
        """
        return self._version

    @property
    def domain(self) -> str:
        """
        :return: domain name the model is executing on
        """
        return self._domain
