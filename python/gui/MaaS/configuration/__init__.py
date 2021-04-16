
import typing
from django.http import HttpRequest

from .. import utilities

COMPILERS: typing.Dict[str, typing.Any] = utilities.get_neighbor_modules(
    file_name=__file__,
    package_name=__package__,
    required_members_and_values=["IS_COMPILER", "FRIENDLY_NAME", "DESCRIPTION", "EDITOR"],
    required_functions=["compile_configuration", "form_editor_payload"]
)


def get_configuration_types() -> typing.Dict[str, str]:
    return {
        name: compiler.FRIENDLY_NAME
        for name, compiler in COMPILERS.items()
    }


def get_generator(configuration_type: str):
    generator = COMPILERS.get(configuration_type)

    if generator is None:
        raise ValueError("A configuration generator could not be found for {}".format(configuration_type))

    return generator


def get_configuration(configuration_type: str, request: HttpRequest):
    return get_generator(configuration_type).compile_configuration(request)


def get_editor_parameters(configuration_type: str, request_arguments: dict) -> dict:
    return get_generator(configuration_type).form_editor_payload(request_arguments)


def get_editor_name(configuration_type: str) -> str:
    return get_generator(configuration_type).EDITOR


def get_editors() -> typing.List[typing.Dict[str, str]]:
    editors = list()

    for module_name, module in COMPILERS.items():
        editors.append({
            "name": module_name,
            "description": module.DESCRIPTION,
            "friendly_name": module.FRIENDLY_NAME
        })

    return editors
