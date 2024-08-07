from .model_exec_request import ModelExecRequest, get_available_models
from deprecated import deprecated


@deprecated("Avoid broken util functions not updated for recent message changes")
def get_available_outputs() -> set:
    """
    :return: A collection of all valid outputs across any model
    """
    all_outputs = set()

    for model in get_available_models().values():  # type: ModelExecRequest
        all_outputs = all_outputs.union(set(model.get_output_variables()))

    return all_outputs


@deprecated("Avoid broken util functions not updated for recent message changes")
def get_distribution_types() -> set:
    """
    :return: The distribution types used across any model
    """
    all_types = set()

    for model in get_available_models().values():
        all_types = all_types.union(set(model.get_distribution_types()))

    return all_types


@deprecated("Avoid broken util functions not updated for recent message changes")
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

    for (
        model_name,
        model,
    ) in get_available_models().items():  # type: str, MaaSJobRequest
        # Say our model is 'NWM'
        model_parameters = list()

        for parameter in model.get_parameters():
            # Say out parameter is 'land_cover'
            parameter_value = dict()
            parameter_value["name"] = " ".join(parameter.split("_")).title()
            parameter_value["value"] = parameter

            # We'll now have {'name': 'Land Cover', 'value': 'land_cover'}, which we'll stick in the list for 'NWM'
            model_parameters.append(parameter_value)

        # This will give us: {'NWM': [{'name': 'Land Cover', 'value': 'land_cover'}]}
        parameters[model_name] = model_parameters

    return parameters


def get_request(
    model: str, config_data_id: str, session_secret: str = "", *args, **kwargs
) -> ModelExecRequest:
    """
    Converts a basic definition of a request into a proper request object

    Parameters
    ----------
    model : str
        The type of model we want to run.
    config_data_id : str
        The model configuration dataset for the request.
    session_secret : str
        The session secret for the right session when communicating with the MaaS request handler.

    Returns
    -------
    ModelExecRequest
        A request object that may be converted into context data for a web request.
    """
    if model not in get_available_models():
        err_msg = "{} is not an allowable model; the only acceptable models are: {}"
        raise ValueError(err_msg.format(model, get_available_models()))

    return get_available_models()[model](
        config_data_id=config_data_id, session_secret=session_secret, *args, **kwargs
    )
