from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^service/(?P<service_id>\d+)/$', views.service_detail, name='service_detail'),
    url(r'^layer/(?P<layer_id>\d+)/$', views.layer_detail, name='layer_detail'),
]
