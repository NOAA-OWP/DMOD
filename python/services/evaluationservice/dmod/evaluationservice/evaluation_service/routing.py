#!/usr/bin/env python3
from django.conf.urls import url, re_path

from service.application_values import CHANNEL_NAME_PATTERN

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
    re_path(r'ws/test$', consumers.TestConsumer.as_asgi()),
    re_path(f'ws/test/(?P<evaluation_id>{CHANNEL_NAME_PATTERN})$', consumers.TestConsumer.as_asgi()),
    re_path(f'ws/channel/(?P<channel_name>{CHANNEL_NAME_PATTERN})/?', consumers.ChannelConsumer.as_asgi(), name="Channel")
]
