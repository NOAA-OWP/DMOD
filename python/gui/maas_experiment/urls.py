"""maas_experiment URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import typing
from django.conf.urls import include
from django.urls import path
from django.urls import re_path
from django.contrib import admin
from django.urls import URLPattern
from django.urls import URLResolver
from django.conf.urls.static import static
from django.conf import settings

import forwarding
import views

from maas_experiment import application_values
from maas_experiment.forwarding import REST_FORWARDING_CONFIGURATION

from django.views.generic.base import TemplateView
# from django.views.static import serve
# import gui.settings as settings

RouteAndURL = typing.NamedTuple("RouteAndURL", route=str, app_url_module=str)

APPLICATION_URL_ROUTES = [
    RouteAndURL("admin/", admin.site.urls),
    RouteAndURL(r"", include("MaaS.urls"))
]


def get_views() -> typing.List[typing.Union[URLResolver, URLPattern]]:
    patterns = list()

    present_routes: typing.List[str] = list()

    announcement_path = f"notify/(?P<channel_name>{application_values.CHANNEL_NAME_PATTERN})?"
    patterns.append(re_path(announcement_path, views.AnnouncementSender.as_view(), name="announce"))

    for configuration in REST_FORWARDING_CONFIGURATION:
        if configuration.route in present_routes:
            raise ValueError(
                f"Cannot add {configuration.name} for REST forwarding - "
                f"there is already a route defined for {configuration.route}"
            )

        new_path = re_path(
            configuration.route_pattern,
            forwarding.ForwardingView.view_from_configuration(configuration),
            name=configuration.name
        )

        patterns.append(new_path)
        present_routes.append(configuration.route)

    for route_and_url in APPLICATION_URL_ROUTES:
        if route_and_url.route in present_routes:
            raise ValueError(
                f"Cannot add an HTTP route for the urls in {route_and_url.app_url_module} - "
                f"there is already a route defined for {route_and_url.route}"
            )
        patterns.append(re_path(route_and_url.route, route_and_url.app_url_module))

    return patterns


urlpatterns = get_views()

if settings.DEBUG:
    urlpatterns.extend(
        static(prefix=settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    )