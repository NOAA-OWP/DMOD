#!/usr/bin/env python3
import typing
import os

from django.views.generic import View
from django.shortcuts import render

from django.http import HttpResponse
from django.http import HttpRequest

import utilities

class Listen(View):
    template = "evaluation_service/evaluation_listener.html"

    def get(self, request: HttpRequest, channel_name: str) -> HttpResponse:
        context = {
            "channel_name": channel_name,
            "channel_key": utilities.get_channel_key(channel_name),
            "channel_route": f"/ws/channel/{channel_name}"
        }
        return render(request, template_name=self.template, context=context)
