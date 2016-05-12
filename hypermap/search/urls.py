from django.conf import settings
from django.conf.urls import include, patterns, url

from search import views

urlpatterns = [
    url(r'^search/csw$', views.csw_global_dispatch, name='csw_global_dispatch'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
