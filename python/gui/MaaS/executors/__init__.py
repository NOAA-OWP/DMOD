
import typing
from django.http import HttpResponse

from .. import utilities

EXECUTORS: typing.Dict[str, typing.Any] = utilities.get_neighbor_modules(
    file_name=__file__,
    package_name=__package__,
    required_members_and_values=["IS_EXECUTOR", "FRIENDLY_NAME"],
    required_functions=["execute"]
)


def get_executor_types() -> typing.Dict[str, str]:
    return {
        name: compiler.FRIENDLY_NAME
        for name, compiler in EXECUTORS.items()
    }


def execute(configuration_type: str, configuration: dict) -> HttpResponse:
    executor = EXECUTORS.get(configuration_type)

    if executor is None:
        raise ValueError("An executor could not be found for {}".format(configuration_type))

    return executor.execute(configuration)
