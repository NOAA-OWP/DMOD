"""
Defines a package for generating configuration details for different modelling frameworks
"""

import typing
from django.http import HttpRequest

from .. import utilities

COMPILERS: typing.Dict[str, typing.Any] = utilities.get_neighbor_modules(
    file_name=__file__,
    package_name=__package__,
    required_members_and_values=["IS_COMPILER", "FRIENDLY_NAME", "DESCRIPTION", "EDITOR"],
    required_functions=["compile_configuration", "form_editor_payload"]
)
"""A mapping between the name of a framework and the module that can generate its configuration"""


def get_configuration_types() -> typing.Dict[str, str]:
    """
    Returns:
        A map between the name of a framework and a human friendly name for it
    """
    return {
        name: compiler.FRIENDLY_NAME
        for name, compiler in COMPILERS.items()
    }


def get_generator(configuration_type: str):
    """
    Get the module that can generate the configuration of the given framework

    Args:
        configuration_type:
            The name of the framework
    Returns:
        A module that can generate the necessary configuration for the given framework
    """
    generator = COMPILERS.get(configuration_type)
    print("Getting the configuration generator for {}".format(configuration_type))

    if generator is None:
        raise ValueError("A configuration generator could not be found for {}".format(configuration_type))

    return generator


def get_configuration(configuration_type: str, request: HttpRequest) -> dict:
    """
    Generate a dictionary outlining the skeleton of a configuration for a framework with the parameters of the
    given request

    Args:
        configuration_type:
            The name of the framework
        request:
            The submitted request that bears the parameters to be injected into the configuration
    Returns:
        A dictionary containing all of the configured options for a framework
    """
    return get_generator(configuration_type).compile_configuration(request)


def get_editor_parameters(configuration_type: str, request_arguments: dict) -> dict:
    """
    Get all of the values that must be sent to a template for rendering

    Args:
        configuration_type:
            The framework to configure
        request_arguments:
            Preconfigured options that may inform

    Returns:
        A dictionary, keyed by strings, representing some configurable setting(s) that need their value(s) changed.
    """
    return get_generator(configuration_type).form_editor_payload(request_arguments)


def get_editor_name(configuration_type: str) -> str:
    """
    Get the name of the HTML template for a framework configuration

    Args:
        configuration_type:
            The name of the framework to be configured
    Returns:
        The name of an HTML template to be used for rendering
    """
    return get_generator(configuration_type).EDITOR


def get_editors() -> typing.List[typing.Dict[str, str]]:
    """
    Forms a list of dictionaries defining all supported editors

    Each editor will contain:

    * 'name' : The name of the framework that the editor belongs to
    * 'description' : A long form explanation of the framework
    * 'friendly_name' : A human friendly name for the framework

    Returns:
        Basic details for all supported editors
    """
    editors = list()

    for module_name, module in COMPILERS.items():
        editors.append({
            "name": module_name,
            "description": module.DESCRIPTION,
            "friendly_name": module.FRIENDLY_NAME
        })

    return editors
