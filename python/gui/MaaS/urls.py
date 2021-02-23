from django.conf.urls import url
from .cbv.EditView import EditView
from .cbv.MapView import MapView

from . import views

app_name = 'MaaS'


urlpatterns = [
    url(r'^$', EditView.as_view()),
    url(r'map', MapView.as_view()),
]
