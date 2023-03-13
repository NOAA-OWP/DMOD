"""
Defines the routes that will be acknowledged within the app to connect a websocket url to its consumer
"""
import typing

from django.urls import re_path
from django.urls.resolvers import URLResolver
from django.urls.resolvers import URLPattern


websocket_urlpatterns = [
    # re_path(f'ws/example/route', consumers.ExampleConsumer.as_asgi(), name="ExampleSocketConsumer")
]
