import typing

from dmod.core.common import get_subclasses

from .action import ActionDescriber
from .listener import ChannelConsumer
from .listener import LaunchConsumer
from .action import SUPPORTED_LANGUAGES


def get_clients() -> typing.Sequence[str]:
    client_classes: typing.Sequence[typing.Type[ActionDescriber]] = get_subclasses(ActionDescriber)
    return [
        client_class.get_client_name()
        for client_class in client_classes
    ]


def get_consumer_by_client_name(client_name: str) -> typing.Optional[typing.Type[ActionDescriber]]:
    client_classes: typing.Sequence[typing.Type[ActionDescriber]] = get_subclasses(ActionDescriber)
    client_mapping = {
        subclass.get_client_name(): subclass
        for subclass in client_classes
    }
    return client_mapping.get(client_name)
