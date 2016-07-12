from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from hypermap.api import views

urlpatterns = [
    url(r'^search/$', views.Search.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)