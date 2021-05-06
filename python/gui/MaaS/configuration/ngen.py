import json
import re
import logging

from .. import models

logger = logging.getLogger("gui_log")

IS_COMPILER = True
"""States that this module is a configuration compilier"""

FRIENDLY_NAME = "NextGen"
"""A short, friendly name for the framework that this module supports"""

DESCRIPTION = "The Next Generation Water Model"
"""A long(er) form description of the framework"""

EDITOR = 'maas/configuration/ngen.html'
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

    payload = {
        'formulations': models.Formulation.objects.all(),
        'catchments': catchments
    }

    return payload


def isolate_parameters(
        feature_key: str,
        total_parameters: dict,
        declared_formulations: dict,
        start_date: str,
        end_date: str
) -> dict:
    """
    Parses all passed parameters and gathers and packages the ones appropriate for the given feature

    The parameters will contain the superset of all possible parameters, meaning that it will have parameters for
    each model in a pattern somewhat like <feature>-<formulation-type>-<parameter>. Only the correct formulation must
    be chosen, only those parameters should be considered, and their names must be shortened to only describe the
    parameters.

    Args:
        feature_key:
            The ID for the feature
        total_parameters:
            The dictionary containing all possibly configured fields for all features and their values
        declared_formulations:
            All formulations that were possibly configured
        start_date:
            The start date of the simulation
        end_date:
            The end date of the simulation
    Returns:
        A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.
    """
    # Start off with the general overarching format of the results
    isolated_parameters = {
        feature_key: {}
    }

    # Separate out the fields that pertain to this location
    parameters = {
        key.replace(feature_key + "-", ""): value
        for key, value in total_parameters.items()
        if key.startswith(feature_key)
    }

    # Get the key of the field containing the type of formulation to use
    formulation_type_keys = [key for key in parameters.keys() if key.endswith("formulation-type")]

    # If no key could be found we can't continue so we error out
    if len(formulation_type_keys) == 0:
        raise ValueError("No formulation type was passed for {}".format(feature_key))

    # Get the key for the field
    type_key = formulation_type_keys[0]

    # Get the value of the formulation type
    passed_formulation_type = parameters[type_key]

    # If the value states that the global formulation should be used, just move on
    if passed_formulation_type == "global":
        return isolated_parameters

    # Now that we know that we can use the formulation, start by defining the forcing
    isolated_parameters[feature_key]['forcing'] = {
        "start_date": start_date,
        "end_date": end_date
    }

    # Extract the path and patterns configured so that we can add that to the configuration
    forcing_paths = [value for key, value in parameters.items() if key == "forcing-path"]

    # If any path is given, attach it to the configuration
    if len(forcing_paths) == 1 and forcing_paths[0] not in [""]:
        isolated_parameters[feature_key]['forcing']["path"] = forcing_paths[0]

        # Find and attach any patterns if defined
        forcing_patterns = [value for key, value in parameters.items() if key == "forcing-pattern"]
        if len(forcing_patterns) == 1 and forcing_patterns[0] not in ["", "*"]:
            isolated_parameters[feature_key]['forcing']['file_pattern'] = forcing_patterns[0]

    # Get the name of the formulation so that we can remove them from the keys from our parameters
    clean_formulation_type = declared_formulations[passed_formulation_type]

    # Remove the name of the formulation type from each parameter key so something like 'cfe-param'
    # simply becomes 'param'
    parameters = {
        key.replace(clean_formulation_type + "-", ""): value
        for key, value in parameters.items()
        if key.startswith(clean_formulation_type)
    }

    # Get the formulation model so that we can continue with the configuration with the correct fields
    formulation = models.Formulation.objects.filter(pk=int(passed_formulation_type)).first()

    # Now separate out parameter groups
    grouped_parameters = dict()

    for field_name, field_value in parameters.items():
        # Try to find the metadata for the configured parameter
        possible_parameter = formulation.formulationparameter_set.filter(name=field_name)

        # Add the parameter to the configuration if it pertains to the formulation
        if possible_parameter.exists():
            # Extract the parameter instance from the collection
            parameter: models.FormulationParameter = possible_parameter.first()

            # If the parameter doesn't belong to a group, we don't need to nest
            if parameter.group is None or parameter.group == "":
                approved_value = field_value

                # Cast the configured value to the correct type based on the model
                if parameter.is_list and parameter.value_type == "number":
                    approved_value = [float(value) for value in field_value.split(",")]
                elif parameter.value_type == "number":
                    approved_value = float(field_value)
                elif parameter.is_list:
                    approved_value = field_value.split(",")

                # Add the parameter value to the configuration
                grouped_parameters[field_name] = approved_value
            else:
                # The parameter belongs to a group, so we need to nest it so that it can be added under the group name
                if parameter.group not in grouped_parameters:
                    grouped_parameters[parameter.group] = dict()

                approved_value = field_value

                # Cast the configured value to the correct type based on the model
                if parameter.is_list and parameter.value_type == "number":
                    approved_value = [float(value) for value in field_value.split(",")]
                elif parameter.value_type == "number":
                    approved_value = float(field_value)
                elif parameter.is_list:
                    approved_value = field_value.split(",")

                # Nest the approved value under the group name
                grouped_parameters[parameter.group][field_name] = approved_value

    # Add the extracted parameters to the overarching dictionary
    isolated_parameters[feature_key][formulation.name] = grouped_parameters

    return isolated_parameters


def compile_configuration(request) -> dict:
    """
    Form a framework configuration based on a passed in http request

    Args:
        request:
            The request from a REST call
    Returns:
        A configuration in the NGEN format that is ready to be submitted
    """
    collected_configuration = dict()

    # Get the list of all passed in features
    feature_pattern = request.POST['features']
    if len(feature_pattern) > 0:
        feature_pattern += "|"
    feature_pattern += "global"

    # Use the feature pattern as a regular expression to separate out all fields that relate directly to the
    # framework, excluding those that don't. For instance, if we had the fields:
    #     - cat-27-cfe-whatever
    #     - cat-27-cfe-whenever
    #     - cat-52-cfe-whatever
    #     - features
    #     - cat-52-cfe-whenever
    #     - global-cfe-whatever
    # A pattern of 'cat-27|cat-52|global' will exclude 'features'
    parameters = {key: value for key, value in request.POST.items() if re.match(feature_pattern, key)}

    # Split out all features that will be configured. `feature_pattern` is not used since it includes the global config
    features = request.POST['features'].split("|")

    # Extract the start and end dates for forcing
    start_date = request.POST['start-time']
    end_date = request.POST['end-time']

    # Convert the definitions for possible formulations into an easily interpretable dictionary
    declared_formulations = json.loads(request.POST['formulations'])

    logger.debug("Now processing form configuration")

    # Form the global configuration and add it to the overarching configuration
    global_configuration = isolate_parameters("global", parameters, declared_formulations, start_date, end_date)
    collected_configuration.update(global_configuration)

    # Add a configuration for each encountered feature
    for feature in features:
        if "catchments" not in collected_configuration:
            collected_configuration["catchments"] = dict()

        single_configuration = isolate_parameters(feature, parameters, declared_formulations, start_date, end_date)
        collected_configuration["catchments"].update(single_configuration)

    return collected_configuration
