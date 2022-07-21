import typing
import logging
import re

import dmod.communication as communication
from dmod.communication import ExternalRequest

from .. import utilities

logger = logging.getLogger("gui_log")

IS_COMPILER = True
"""States that this module is a configuration compilier"""

FRIENDLY_NAME = "National Water Model"
"""A short, friendly name for the framework that this module supports"""

DESCRIPTION = "The National Water Model"
"""A long(er) form description of the framework"""

EDITOR = 'maas/configuration/nwm.html'
"""The path to the template to render the configuration screen in"""


def form_editor_payload(request_arguments: dict) -> dict:
    """
    Accumulate and return all parameters needed to render the configuration screen

    Args:
        request_arguments:
            Parameters passed via an HttpRequest
    Returns:
        A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.
    """
    catchments = request_arguments.get('feature-ids', None)

    if catchments is not None:
        catchments = catchments.split("|")

    output_types = list()
    distribution_types = list()

    # Create a mapping between each output type and a friendly representation of it
    for output in communication.get_available_outputs():
        output_definition = dict()
        output_definition['name'] = utilities.humanize(output)
        output_definition['value'] = output
        output_types.append(output_definition)

    # Create a mapping between each distribution type and a friendly representation of it
    for distribution_type in communication.ExternalRequest.get_distribution_types():
        type_definition = dict()
        type_definition['name'] = utilities.humanize(distribution_type)
        type_definition['value'] = distribution_type
        distribution_types.append(type_definition)

    payload = {
        'catchments': catchments,
        'output_types': output_types,
        'distribution_types': distribution_types,
        'parameters': [
            {"value": parameter, "name": utilities.humanize(parameter)}
            for parameter in ExternalRequest.get_parameters()
        ]
    }

    return payload


def form_parameter(
        model: str,
        variable: str,
        parameter_configuration: dict
) -> typing.Union[communication.Scalar, communication.Distribution]:
    """
    Converts a subset of http parameters into Scalar or Distribution objects that serve as parameters

    Args:
        model:
            The name of the model used (will most likely always be 'nwm'
        variable:
            The name of the variable being evaluated
        parameter_configuration:
            Fields from the web form that pertain to this parameter
    Returns:
        A Scalar or Distribution object to be sent along with MaaS request
    """
    key_prefix = model + "_" + variable + "_"

    # Get the type of parameter that was selected; options as of writing are 'Scalar' or 'Distribution'
    parameter_type = parameter_configuration.get(key_prefix + "parameter_type")

    # If the selection was scalar, use the scalar field to create a simple scalar object
    if parameter_type.lower() == "scalar":
        parameter = communication.Scalar(int(float(parameter_configuration[key_prefix + "scalar"])))
    else:
        # Use the series of distribution fields to create a distribution object
        minimum = int(float(parameter_configuration[key_prefix + "distribution_min"]))
        maximum = int(float(parameter_configuration[key_prefix + "distribution_max"]))
        distribution_type = parameter_configuration[key_prefix + "distribution_type"]
        parameter = communication.Distribution(minimum, maximum, distribution_type)

    return parameter


def isolate_parameters(total_parameters: dict) -> dict:
    """
    Parses all passed parameters and gathers and packages the ones appropriate for the given feature

    The parameters will contain the superset of all possible parameters, meaning that it will have parameters for
    each model in a pattern somewhat like <feature>-<formulation-type>-<parameter>. Only the correct formulation must
    be chosen, only those parameters should be considered, and their names must be shortened to only describe the
    parameters.

    Args:
        total_parameters:
            The dictionary containing all possibly configured fields for all features and their values
    Returns:
        A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.
    """
    isolated_parameters = dict()

    model: str = total_parameters['model']

    # Get the list of parameters for this model - we'll get the parameters of the form:
    #   [{'value': 'hydro_whatever', 'name': 'Hydro Whatever'}, {'value': 'land_cover', 'name': 'Land Cover'}]
    allowed_parameters: typing.List[typing.Dict[str, str]] = communication.get_parameters()[model]

    for parameter_details in allowed_parameters:
        name = parameter_details['value']

        # Create a subset of the passed fields that will help form formal parameters
        key_pattern = "{}_{}_.+".format(model, name)
        parameter_fields = {
            key: value for key, value in total_parameters.items()
            if re.search(key_pattern, key)
        }

        isolated_parameters[name] = form_parameter(model, name, parameter_fields)

    logger.debug(isolated_parameters)

    return isolated_parameters


def compile_configuration(request) -> dict:
    """
    Form a framework configuration based on a passed in http request

    Args:
        request:
            The request from a REST call
    Returns:
        A configuration in the NWM format that is ready to be submitted
    """
    return isolate_parameters(request.POST)
