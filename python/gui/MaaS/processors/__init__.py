
import typing

from .processor import BaseProcessor
from .. import utilities

PROCESSORS: typing.Dict[str, typing.Any] = utilities.get_neighbor_modules(
    file_name=__file__,
    package_name=__package__,
    required_members_and_values=["IS_PROCESSOR", "FRIENDLY_NAME", "Processor"],
    required_functions=["create_processor"]
)


def get_processor_types() -> typing.Dict[str, str]:
    return {
        name: compiler.FRIENDLY_NAME
        for name, compiler in PROCESSORS.items()
    }


def get_processor(framework: str, secret: str = None) -> BaseProcessor:
    processor_module = PROCESSORS.get(framework)

    if framework is None:
        raise ValueError("A request processor could not be found for {}".format(framework))

    return processor_module.create_processor(secret)
