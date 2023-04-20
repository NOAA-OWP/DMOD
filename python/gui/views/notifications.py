"""
Defines a view to be used to send messages to every active browser
"""
import os
import typing

from django.views.generic import TemplateView

from maas_experiment import application_values

from utilities import CodeViews


class AnnouncementSender(TemplateView):
    template_name = "announcer.html"

    def get_context_data(self, channel_name: str = None, **kwargs):
        context = super().get_context_data(**kwargs)
        announcer_url = f"ws/announce/{channel_name or application_values.NOTIFICATION_CHANNEL}"
        context['announcer_url'] = announcer_url
        code_views = CodeViews()
        code_views.add(
            name="notifications",
            container="announcement-wrapper",
            textarea="announcement-box"
        )
        context['code_views'] = code_views.to_json()
        return context
