from django.urls import re_path

from service.application_values import CHANNEL_NAME_PATTERN
from service.application_values import CHANNEL_NAME_PATTERN as SAFE_STRING_NAME

import evaluation_service.views as views

# Enable views to be access via "evaluation_service:<name>" when using the "url" directive in templates or the
# 'reverse' function
app_name = 'evaluation_service'

urlpatterns = [
    re_path(f'status/?(?P<name>{CHANNEL_NAME_PATTERN})?/?$', views.EvaluationStatus.as_view(), name="Status"),
    re_path(f'listen/(?P<channel_name>{CHANNEL_NAME_PATTERN})/?$', views.Listen.as_view(), name="Listen"),
    re_path(r'launch$', views.LaunchEvaluation.as_view(), name="Launch"),
    re_path(r'build$', views.ReadyEvaluation.as_view(), name="Build"),
    re_path(r'build_async$', views.ReadyListenEvaluation.as_view(), name="BuildAndRun"),
    re_path(r'^$', views.EvaluationList.as_view(), name="EvaluationList"),
    re_path(r'clean$', views.Clean.as_view(), name="Clean"),
    re_path(f'output/(?P<evaluation_name>{CHANNEL_NAME_PATTERN})/?$', views.helpers.GetOutput.as_view(), name="Output"),
    re_path('geometry/?$', views.GetGeometryDatasets.as_view(), name="GeometryList"),
    re_path(f"geometry/(?P<dataset_id>\d+)/?$", views.GetGeometry.as_view(), name="GetGeometry"),
    re_path(
        f"geometry/(?P<dataset_id>\d+)/(?P<geometry_name>{SAFE_STRING_NAME})/?$",
        views.GetGeometry.as_view(),
        name="GetGeometryByName"
    ),
]
