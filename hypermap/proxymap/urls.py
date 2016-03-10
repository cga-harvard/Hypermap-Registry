from django.conf import settings
from django.conf.urls import include, patterns, url

from . import views

urlpatterns = [
    url(r'^(?P<layer_id>\d+)/wms(?P<path_info>/.*)$', views.layer_mapproxy, name='layer_mapproxy'),
]
