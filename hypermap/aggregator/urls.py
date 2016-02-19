from django.conf import settings
from django.conf.urls import include, patterns, url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^service/(?P<service_id>\d+)/$', views.service_detail, name='service_detail'),
    url(r'^layer/(?P<layer_id>\d+)/$', views.layer_detail, name='layer_detail'),
    url(r'^celery_monitor/$', views.celery_monitor, name='celery_monitor'),
    url(r'^update_progressbar/(?P<task_id>[^/]*)$', views.update_progressbar, name='update_progressbar'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
