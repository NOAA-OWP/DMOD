from django.conf.urls import url
from MaaS.cbv.EditView import EditView

from . import views

app_name = 'MaaS'


urlpatterns = [
    url(r'^$', EditView.as_view())
]