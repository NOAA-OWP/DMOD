"""
ASGI config for service project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os
import os

import django

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter


from evaluation_service import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),     # For Http Connection
    "websocket": AuthMiddlewareStack(   # For Websocket Connection
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
