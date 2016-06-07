# from django.shortcuts import render

# Create your views here.

import os

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from pycsw import server

from hypermap.aggregator.models import Catalog


@csrf_exempt
def csw_global_dispatch(request):
    """pycsw wrapper"""

    env = request.META.copy()
    env.update({'local.app_root': os.path.dirname(__file__),
                'REQUEST_URI': request.build_absolute_uri()})

    csw = server.Csw(settings.PYCSW, env, version='2.0.2')

    content = csw.dispatch_wsgi()

    # pycsw 2.0 has an API break:
    # pycsw < 2.0: content = xml_response
    # pycsw >= 2.0: content = [http_status_code, content]
    # deal with the API break

    if isinstance(content, list):  # pycsw 2.0+
        content = content[1]

    return HttpResponse(content, content_type=csw.contenttype)


@csrf_exempt
def csw_global_dispatch_by_catalog(request, catalog_slug):
    """pycsw wrapper"""

    catalog = get_object_or_404(Catalog, slug=catalog_slug)

    env = request.META.copy()
    env.update({'local.app_root': os.path.dirname(__file__),
                'REQUEST_URI': request.build_absolute_uri()})

    csw = server.Csw(settings.PYCSW, env, version='2.0.2')

    content = csw.dispatch_wsgi()

    # pycsw 2.0 has an API break:
    # pycsw < 2.0: content = xml_response
    # pycsw >= 2.0: content = [http_status_code, content]
    # deal with the API break

    if isinstance(content, list):  # pycsw 2.0+
        content = content[1]

    return HttpResponse(content, content_type=csw.contenttype)