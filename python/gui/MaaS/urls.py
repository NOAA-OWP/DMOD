from django.conf.urls import url
from .cbv.EditView import EditView
from .cbv.MapView import MapView
from .cbv.NgenConfigView import NgenConfigView

from . import views

app_name = 'MaaS'


urlpatterns = [
    url(r'^$', EditView.as_view()),
    url(r'map', MapView.as_view()),
    url(r'config/ngen', NgenConfigView.as_view(), name='ngen_config')
]
