from django.urls import re_path

from service.application_values import CHANNEL_NAME_PATTERN
from service.application_values import CHANNEL_NAME_PATTERN as SAFE_STRING_NAME

import evaluation_service.views as views
from evaluation_service.views import ViewPath

from evaluation_service.views import templates
from evaluation_service.views import definitions

# Enable views to be access via "evaluation_service:<name>" when using the "url" directive in templates or the
# 'reverse' function
app_name = 'evaluation_service'

urlpatterns = [
    re_path(f'status/?(?P<name>{CHANNEL_NAME_PATTERN})?/?$', views.EvaluationStatus.as_view(), name="Status"),
    re_path(f'listen/(?P<channel_name>{CHANNEL_NAME_PATTERN})/?$', views.Listen.as_view(), name="Listen"),
    re_path(r'launch/?$', views.LaunchEvaluation.as_view(), name="Launch"),
    re_path(r'build/?$', views.ReadyListenEvaluation.as_view(), name="BuildAndRun"),
    re_path(r'^$', views.EvaluationList.as_view(), name="EvaluationList"),
    re_path(r'details$', views.EvaluationDetails.as_view(), name="EvaluationDetails"),
    re_path(r'clean$', views.Clean.as_view(), name="Clean"),
    re_path(f'output/(?P<evaluation_name>{CHANNEL_NAME_PATTERN})/?$', views.helpers.GetOutput.as_view(), name="Output"),
    re_path('geometry/?$', views.GetGeometryDatasets.as_view(), name="GeometryList"),
    re_path(r"geometry/(?P<dataset_id>\d+)/?$", views.GetGeometry.as_view(), name="GetGeometry"),
    re_path(
        f"geometry/(?P<dataset_id>\d+)/(?P<geometry_name>{SAFE_STRING_NAME})/?$",
        views.GetGeometry.as_view(),
        name="GetGeometryByName"
    ),
    re_path("metrics/?$", views.Metrics.as_view(), name="Metrics"),
    re_path(views.GetLibraryOptions.route(), views.GetLibraryOptions.as_view(), name="LibraryOptions"),
    re_path(views.GetLibrary.route(), views.GetLibrary.as_view(), name="GetLibrary"),
    re_path(r"library/select/?$", views.LibrarySelector.as_view(), name="SelectLibrary"),
    re_path(r"schema/?$", views.Schema.as_view(), name="Schema"),
    #re_path(r"templates/get/?$", templates.GetTemplate.as_view(), name="GetTemplate"),
    #re_path(
    #    r"templates/(?P<author>[-a-zA-Z .0-9_]+)/(?P<specification_type>[a-zA-Z_]+)/(?P<name>[-a-zA-Z0-9 .:]+)/?$",
    #    templates.GetTemplate.as_view(),
    #    name="GetTemplateParameterized"
    #),
    #re_path(r"templates/search/?$", templates.SearchTemplates.as_view(), name="SearchTemplates"),
    #re_path(r"templates/?$", templates.GetAllTemplates.as_view(), name="GetAllTemplates"),
    #re_path(r"definitions/?$", definitions.SearchForDefinition.as_view(), name="AllDefinitions"),
    #re_path(r"definitions/search/?$", definitions.SearchForDefinition.as_view(), name="SearchForDefinition"),
    #re_path(r"definitions/(?P<definition_id>\d+)/?$", definitions.GetDefinition.as_view(), name="GetDefinition"),
    #re_path(r"definitions/save/?$", definitions.SaveDefinition.as_view(), name="SaveDefinition"),
    #re_path(r"definitions/validate/?$", definitions.ValidateDefinition.as_view(), name="ValidateDefinition"),
]

views.MasterSchema.assign_message_views(
    urlpatterns,
    app_name,
    (templates.GetAllTemplates, r"templates/?$"),
    (templates.GetTemplate, r"templates/get/?$", "GetTemplate"),
    (templates.GetTemplateByID, r"templates/(?P<template_id>\d+)?$"),
    (templates.SearchTemplates, r"templates/search/?$"),
    (templates.GetTemplateSpecificationTypes, r"templates/types/?$"),
    (
        templates.SearchTemplates,
        r"templates/(?P<author>[-a-zA-Z .0-9_]+)/?$",
        "SearchTemplatesByAuthor"
    ),
    (
        templates.SearchTemplates,
        r"templates/(?P<author>[-a-zA-Z .0-9_]+)/(?P<specification_type>[a-zA-Z_]+)/?$",
        "SearchTemplatesByAuthorAndType"
    ),
    (
        templates.GetTemplate,
        r"templates/(?P<author>[-a-zA-Z .0-9_]+)/(?P<specification_type>[a-zA-Z_]+)/(?P<name>[-a-zA-Z0-9 .:]+)/?$",
        "GetTemplateParameterized"
    ),
    (
        definitions.SearchForDefinition,
        r"definitions/?",
        "AllDefinitions"
    ),
    (
        definitions.SearchForDefinition,
        r"definitions/search/?$",
        "SearchForDefinition"
    ),
    (definitions.GetDefinition, r"definitions/(?P<definition_id>\d+)/?$"),
    (definitions.SaveDefinition, r"definitions/save/?$"),
    (definitions.ValidateDefinition, r"definitions/validate/?$"),
)
