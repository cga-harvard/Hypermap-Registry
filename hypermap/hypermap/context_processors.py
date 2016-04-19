from django.conf import settings
from urlparse import urlparse


def resource_urls(request):
    """Global values to pass to templates"""
    url_parsed = urlparse(settings.SOLR_URL)
    defaults = dict(
        SOLR_URL=settings.SOLR_URL,
        SOLR_IP='%s://%s:%s' % (url_parsed.scheme, url_parsed.hostname, url_parsed.port)
    )
    return defaults
