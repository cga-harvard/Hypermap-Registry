# Get multiple application dispatcher from mapproxy
from mapproxy.multiapp import make_wsgi_app
from django.conf import settings

application = make_wsgi_app(settings.MAPPROXY_CONFIG, allow_listing=True)
