from django.conf import settings
from urlparse import urlparse


def resource_urls(request):
    """Global values to pass to templates"""
    REGISTRY_SEARCH_URL = getattr(settings, "REGISTRY_SEARCH_URL", "elasticsearch+http://localhost:9200")

    SEARCH_TYPE = REGISTRY_SEARCH_URL.split('+')[0]
    SEARCH_URL = REGISTRY_SEARCH_URL.split('+')[1]

    url_parsed = urlparse(SEARCH_URL)
    defaults = dict(
        SITE_URL=settings.SITE_URL.rstrip('/'),
        SEARCH_TYPE=SEARCH_TYPE,
        SEARCH_URL=SEARCH_URL,
        SEARCH_IP='%s://%s:%s' % (url_parsed.scheme, url_parsed.hostname, url_parsed.port)
    )
    return defaults
