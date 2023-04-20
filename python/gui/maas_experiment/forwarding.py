"""
Provides direct access to configured web socket and REST forwarding settings
"""
import os
import typing

from . import application_values

from forwarding import ForwardingConfiguration


def load_socket_forwarding_configuration() -> typing.Iterable[ForwardingConfiguration]:
    configurations = ForwardingConfiguration.load(application_values.SOCKET_FORWARDING_CONFIG_PATH)
    return configurations


def load_rest_forwarding_configuration() -> typing.Iterable[ForwardingConfiguration]:
    configurations = ForwardingConfiguration.load(application_values.REST_FORWARDING_CONFIG_PATH)
    return configurations


def get_forward_rest_route(name: str, *args) -> str:
    """
    Get the route to a forwarded REST service by name

    Example:
        >>> get_forward_rest_route("EvaluationService")
        "evaluations"
        >>> get_forward_rest_route("EvaluationService", "geometry", 1)
        "evaluations/geometry/1"

    Args:
        name: The name of the REST service to find
        args: Additional paths to append to the route


    """
    for configuration in REST_FORWARDING_CONFIGURATION:
        if configuration.name.lower() == name.lower():
            route = configuration.route

            for path in args:
                route = os.path.join(route, str(path))

            return route
    raise KeyError(f"No REST forwarding can be found with the name {name}")


def get_forward_socket_route(name: str, *args) -> str:
    for configuration in SOCKET_FORWARDING_CONFIGURATION:
        if configuration.name.lower() == name.lower():
            route = configuration.route

            for path in args:
                route = os.path.join(route, str(path))

            return route
    raise KeyError(f"No socket forwarding can be found with the name {name}")


SOCKET_FORWARDING_CONFIGURATION = load_socket_forwarding_configuration()
REST_FORWARDING_CONFIGURATION = load_rest_forwarding_configuration()
