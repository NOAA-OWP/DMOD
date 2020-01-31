from django.conf.urls import url
from .cbv.EditView import EditView

from . import views

app_name = 'MaaS'


urlpatterns = [
    url(r'^$', EditView.as_view())
]