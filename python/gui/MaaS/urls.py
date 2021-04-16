from django.conf.urls import url
from .cbv.EditView import EditView
from .cbv.MapView import MapView, Fabrics, FabricNames

from .cbv.configuration import Compiler
from .cbv.configuration import CreateConfiguration

app_name = 'MaaS'

urlpatterns = [
    url(r'^$', EditView.as_view()),
    url(r'map$', MapView.as_view(), name="map"),
    url(r'fabric/names$', FabricNames.as_view(), name='fabric-names'),
    url(r'fabric/(?P<fabric>[a-zA-Z0-9_-]+)?', Fabrics.as_view(), name='fabrics'),
    url(r'config/edit', CreateConfiguration.as_view(), name='create_config'),
    url(r'config/compile', Compiler.as_view(), name="compile")
]
