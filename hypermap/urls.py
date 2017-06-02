from django.conf.urls import patterns, include, url
from django.conf import settings

from django.contrib import admin
from django.contrib.auth import views as auth_views

from .aggregator import views

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)),
    (r'^registry/', include('hypermap.search_api.urls')),
    (r'^registry/', include('hypermap.search.urls')),
    (r'^registry/', include('hypermap.aggregator.urls')),

    url(r'^login/$', auth_views.login, {'template_name': 'aggregator/login.html'}),
    url(r'^logout/$', auth_views.logout, {'template_name': 'aggregator/logout.html'}),
    url(r'^password_change/$', auth_views.password_change, {'template_name': 'aggregator/password_change.html'}),
    url(r'^password_change/done/$', auth_views.password_change_done, {'template_name': 'aggregator/password_change_done.html'}),
    url(r'^', include('django.contrib.auth.urls')),
)

urlpatterns += patterns(
    '',
    url(r'^media/(?P<path>.*)$',
        'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT, }),
)
