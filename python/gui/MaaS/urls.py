from maas_experiment import application_values

from django.urls import re_path
from .cbv.EditView import EditView
from .cbv.MapView import MapView, Fabrics, FabricNames, FabricTypes, ConnectedFeatures
from .cbv.evaluation import ReadyListenEvaluation
from .cbv.evaluation import EvaluationListing
from .cbv.configuration import CreateConfiguration
from .cbv.execution import Execute
from .cbv.crosswalk import Crosswalk
from .cbv.prototyping import RuntimePrototype

app_name = 'MaaS'

urlpatterns = [
    #re_path(r'^$', EditView.as_view()),
    re_path(r'map$', MapView.as_view(), name="map"),
    re_path(r'evaluation$', ReadyListenEvaluation.as_view(), name="ready-evaluation"),
    re_path(r'evaluation/listings$', EvaluationListing.as_view(), name="evaluation-listing"),
    re_path(r'map/connections$', ConnectedFeatures.as_view(), name="connections"),
    re_path(r'fabric/names$', FabricNames.as_view(), name='fabric-names'),
    re_path(r'fabric/types$', FabricTypes.as_view(), name='fabric-types'),
    re_path(r'fabric/(?P<fabric>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Fabrics.as_view(), name='fabrics'),
    re_path(r'config/edit', CreateConfiguration.as_view(), name='create_config'),
    re_path(r'config/execute', Execute.as_view(), name='execute'),
    re_path(r'crosswalk/(?P<crosswalk>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Crosswalk.as_view(), name='crosswalk')
]

if application_values.in_debug_mode():
    urlpatterns.append(
        re_path(r'proto/(?P<path>.+)', RuntimePrototype.as_view(), name="runtime-prototype")
    )
