from django.conf import settings
from urlparse import urlparse

from . import __description__, __version__


def resource_urls(request):
    """Global values to pass to templates"""

    url_parsed = urlparse(settings.SEARCH_URL)
    defaults = dict(
        APP_NAME=__description__,
        APP_VERSION=__version__,
        SITE_URL=settings.SITE_URL.rstrip('/'),
        SEARCH_TYPE=settings.SEARCH_TYPE,
        SEARCH_URL=settings.SEARCH_URL,
        SEARCH_IP='%s://%s:%s' % (url_parsed.scheme, url_parsed.hostname, url_parsed.port)
    )
    return defaults
