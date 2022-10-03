from django.conf.urls import url
from .cbv.EditView import EditView
from .cbv.DatasetManagementView import DatasetManagementView
from .cbv.DatasetApiView import DatasetApiView
from .cbv.MapView import MapView, Fabrics, FabricNames, FabricTypes, ConnectedFeatures

from .cbv.configuration import CreateConfiguration
from .cbv.execution import Execute
from .cbv.crosswalk import Crosswalk

app_name = 'MaaS'

urlpatterns = [
    url(r'^$', EditView.as_view()),
    # TODO: add this later
    #url(r'ngen$', NgenWorkflowView.as_view(), name="ngen-workflow"),
    url(r'datasets', DatasetManagementView.as_view(), name="dataset-management"),
    url(r'dataset-api', DatasetApiView.as_view(), name="dataset-api"),
    url(r'map$', MapView.as_view(), name="map"),
    url(r'map/connections$', ConnectedFeatures.as_view(), name="connections"),
    url(r'fabric/names$', FabricNames.as_view(), name='fabric-names'),
    url(r'fabric/types$', FabricTypes.as_view(), name='fabric-types'),
    url(r'fabric/(?P<fabric>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Fabrics.as_view(), name='fabrics'),
    url(r'config/edit', CreateConfiguration.as_view(), name='create_config'),
    url(r'config/execute', Execute.as_view(), name='execute'),
    url(r'crosswalk/(?P<crosswalk>[a-zA-Z0-9_-]+(\s\([a-zA-Z0-9_-]+\))*)?', Crosswalk.as_view(), name='crosswalk')
]
