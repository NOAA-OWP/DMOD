"""
ASGI config for service project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""
import typing
import os

import django

from django.core.asgi import get_asgi_application

from django.urls import re_path
from django.urls.resolvers import URLResolver
from django.urls.resolvers import URLPattern

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter

import forwarding
import consumers
import MaaS.routing

from maas_experiment import application_values
from maas_experiment.forwarding import SOCKET_FORWARDING_CONFIGURATION

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service.settings')


def get_consumers() -> typing.List[typing.Union[URLResolver, URLPattern]]:
    urlpatterns: typing.List[typing.Union[URLResolver, URLPattern]] = list()
    urlpatterns.extend(MaaS.routing.websocket_urlpatterns)

    present_routes: typing.List[str] = list()

    for pattern_or_resolver in urlpatterns:  # type: typing.Union[URLPattern, URLResolver]
        if isinstance(pattern_or_resolver, URLResolver):
            present_routes.append(str(pattern_or_resolver.pattern.name))
        else:
            present_routes.append(pattern_or_resolver.pattern)

    for configuration in SOCKET_FORWARDING_CONFIGURATION:
        if configuration.route in present_routes:
            raise ValueError(
                f"Cannot add the {configuration.name} websocket proxy - "
                f"there is already a route defined for {configuration.route}"
            )

        new_path = re_path(
            configuration.route_pattern,
            forwarding.ForwardingSocket.asgi_from_configuration(configuration),
            name=configuration.name
        )
        urlpatterns.append(new_path)
        present_routes.append(configuration.route_pattern)

    # Add a websocket consumer specifically for notifications
    urlpatterns.append(
        consumers.Notifier.make_path(
            "ws/notifications",
            name="notifications"
        )
    )

    urlpatterns.append(
        consumers.Announcer.make_path(
            f"ws/announce/(?P<channel_name>{application_values.CHANNEL_NAME_PATTERN})",
            name="announce"
        )
    )

    # Add a websocket consumer for just about any other channel that might be available
    urlpatterns.append(
        consumers.PubSubConsumer.make_path(
            f"ws/listen/(?P<channel_name>{application_values.CHANNEL_NAME_PATTERN})",
            purpose="listen",
            name="listen"
        )
    )

    return urlpatterns


application = ProtocolTypeRouter({
    "http": get_asgi_application(),     # For Http Connection
    "websocket": AuthMiddlewareStack(   # For Websocket Connection
        URLRouter(
            get_consumers()
        )
    ),
})
