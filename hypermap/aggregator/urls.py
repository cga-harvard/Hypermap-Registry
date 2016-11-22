from django.conf import settings
from django.conf.urls import include, patterns, url

# TODO: Correct configuration of maploom urls
# from maploom_registry.geonode.urls import urlpatterns as maploom_urls
from hypermap.aggregator import views

uuid_regex = '[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^domains/$', views.domains, name='domains'),
    url(r'^tasks_runner/$', views.tasks_runner, name='tasks_runner'),

    url(r'^(?P<catalog_slug>[-\w]+)/$', views.index, name='index'),

    # services
    url(r'^(?P<catalog_slug>[-\w]+)/service/(?P<service_uuid>%s)/$' % uuid_regex,
        views.service_detail,
        name='service_detail'),
    url(r'^(?P<catalog_slug>[-\w]+)/service/(?P<service_uuid>%s)/checks/$' % uuid_regex,
        views.service_checks,
        name='service_checks'),

    # layers
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_uuid>%s)/$' % uuid_regex,
        views.layer_detail,
        name='layer_detail'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_uuid>%s)/checks/$' % uuid_regex,
        views.layer_checks,
        name='layer_checks'),

    # mapproxy
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_uuid>%s)/map(?P<path_info>/.*)$' % uuid_regex,
        views.layer_mapproxy,
        name='layer_mapproxy'),
    url(r'^(?P<catalog_slug>[-\w]+)/layer/(?P<layer_uuid>[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12})/map/config$',
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
