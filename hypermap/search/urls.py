from django.conf import settings
from django.conf.urls import include, patterns, url

from . import views

urlpatterns = [
    url(r'^search/csw/(?P<catalog_slug>[\w-]+)/$', views.csw_global_dispatch_by_catalog,
        name='csw_global_dispatch_by_catalog'),
    url(r'^search/csw$', views.csw_global_dispatch, name='csw_global_dispatch'),
    url(r'^search/opensearch$', views.opensearch_dispatch, name='opensearch_dispatch')
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
