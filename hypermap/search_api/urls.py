from django.conf.urls import url, include
from django.views.generic import TemplateView
from rest_framework import routers
from hypermap.search_api import views


router = routers.DefaultRouter()
router.register(r'catalogs', views.CatalogViewSet)


urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api/docs/$', TemplateView.as_view(template_name='search_api/swagger/index.html')),
    url(r'^(?P<catalog_slug>[-\w]+)/api/$', views.Search.as_view(), name="search_api"),
]
