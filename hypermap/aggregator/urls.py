from django.conf import settings
from django.conf.urls import include, patterns, url

# TODO: Correct configuration of maploom urls
# from maploom_registry.geonode.urls import urlpatterns as maploom_urls
from hypermap.aggregator import views


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^domains/$', views.domains, name='domains'),
    url(r'^celery_monitor/$', views.celery_monitor, name='celery_monitor'),
    url(r'^update_progressbar/(?P<task_id>[^/]*)$', views.update_progressbar, name='update_progressbar'),
    url(r'^update_jobs_number/$', views.update_jobs_number, name='update_jobs_number'),

    url(r'^(?P<catalog_slug>[-\w]+)/$', views.index, name='index'),
    url(r'^(?P<catalog_slug>[-\w]+)/service/(?P<service_id>\d+)/$', views.service_detail, name='service_detail'),
    url(r'^(?P<catalog_slug>[-\w]+)/service/(?P<service_id>\d+)/checks/$',
        views.service_checks,
        name='service_checks'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_id>\d+)/$', views.layer_detail, name='layer_detail'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_id>\d+)/checks/$', views.layer_checks, name='layer_checks'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_id>\d+)/map(?P<path_info>/.*)$',
        views.layer_mapproxy,
        name='layer_mapproxy'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_id>\d+)/map/config$',
        views.layer_mapproxy,
        name='layer_mapproxy_config')
]

# urlpatterns += maploom_urls

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
