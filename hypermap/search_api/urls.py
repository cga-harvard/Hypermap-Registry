from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework import routers
from hypermap.search_api import views


router = routers.DefaultRouter()
router.register(r'catalogs', views.CatalogViewSet)


urlpatterns = [
    url(r'^search/(?P<catalog_slug>[-\w]+)/$', views.Search.as_view(), name="search_api"),
    url(r'^docs/$', TemplateView.as_view(template_name='search_api/swagger/index.html')),
    url(r'^', include(router.urls)),
]