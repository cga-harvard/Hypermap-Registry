from django.conf import settings
from urlparse import urlparse

import hypermap


def resource_urls(request):
    """Global values to pass to templates"""
    url_parsed = urlparse(settings.SEARCH_URL)
    defaults = dict(
        APP_NAME=hypermap.__description__,
        APP_VERSION=hypermap.__version__,
        SITE_URL=settings.SITE_URL.rstrip('/'),
        SEARCH_URL=settings.SEARCH_URL,
        SEARCH_IP='%s://%s:%s' % (url_parsed.scheme, url_parsed.hostname, url_parsed.port)
    )
    return defaults
