from django.urls import re_path
from .cbv.EditView import EditView
from .cbv.DatasetManagementView import DatasetManagementView
from .cbv.DatasetApiView import DatasetApiView
from .cbv.MapView import MapView, Fabrics, FabricNames, FabricTypes, ConnectedFeatures

from .cbv.configuration import CreateConfiguration
from .cbv.execution import Execute
from .cbv.crosswalk import Crosswalk

app_name = 'MaaS'

urlpatterns = [
    re_path(r'^$', EditView.as_view()),
    # TODO: add this later
    #re_path(r'ngen$', NgenWorkflowView.as_view(), name="ngen-workflow"),
    re_path(r'datasets', DatasetManagementView.as_view(), name="dataset-management"),
    re_path(r'dataset-api', DatasetApiView.as_view(), name="dataset-api"),
    re_path(r'map$', MapView.as_view(), name="map"),
    re_path(r'map/connections$', ConnectedFeatures.as_view(), name="connections"),
    re_path(r'fabric/names$', FabricNames.as_view(), name='fabric-names'),
    re_path(r'fabric/types$', FabricTypes.as_view(), name='fabric-types'),
    re_path(r'fabric/(?P<fabric>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Fabrics.as_view(), name='fabrics'),
    re_path(r'config/edit', CreateConfiguration.as_view(), name='create_config'),
    re_path(r'config/execute', Execute.as_view(), name='execute'),
    re_path(r'crosswalk/(?P<crosswalk>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Crosswalk.as_view(), name='crosswalk')
]
