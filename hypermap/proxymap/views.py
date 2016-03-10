# from django.shortcuts import render
from aggregator.models import Layer
from django.shortcuts import get_object_or_404
from mapproxy.config.loader import load_configuration
from mapproxy.wsgiapp import MapProxyApp
from mapproxy.test.image import is_png
from django_wsgi.embedded_wsgi import call_wsgi_app
from django_wsgi.handler import DjangoWSGIRequest
from webtest import TestApp as TestApp_
from itertools import chain
from traceback import format_exc

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest, STATUS_CODE_TEXT
from django.core.urlresolvers import RegexURLResolver
from django.http import Http404, HttpResponseNotFound, HttpResponse
from django.utils.html import escape

class TestApp(TestApp_):
    """
    Wraps webtest.TestApp and explicitly converts URLs to strings.
    Behavior changed with webtest from 1.2->1.3.
    """
    def get(self, url, *args, **kw):
        return TestApp_.get(self, str(url), *args, **kw)


def get_mapproxy(services_conf='/webapps/hypermap/hypermap/hypermap/boo.yaml'):
    conf = load_configuration(mapproxy_conf=services_conf, ignore_warnings=False)
    services = conf.configured_services()

    app = MapProxyApp(services, conf.base_config)

    return TestApp(app)


class ClosingIterator(object):
    def __init__(self, iterator, close_callback):
        self.iterator = iter(iterator)
        self.close_callback = close_callback

    def __iter__(self):
        return self

    def next(self):
        return self.iterator.next()

    def close(self):
        self.close_callback()


def layer_mapproxy(request,  layer_id, path_info):
    layer = get_object_or_404(Layer, pk=layer_id)

    mp = get_mapproxy()

    mp_response = mp.get(path_info)

    response = HttpResponse(mp_response.body, status=mp_response.status_int)

    for header, value in mp_response.headers.iteritems():
        response[header] = value

    return response
