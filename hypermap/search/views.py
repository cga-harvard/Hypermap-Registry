# from django.shortcuts import render

# Create your views here.

import os

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import loader, RequestContext
from django.views.decorators.csrf import csrf_exempt

from pycsw import server

from hypermap.aggregator.models import Catalog


@csrf_exempt
def csw_global_dispatch(request):
    """pycsw wrapper"""

    msg = None

    # test for authentication and authorization
    if any(word in request.body for word in ['Harvest ', 'Transaction ']):
        if not _is_authenticated():
            msg = 'Not authenticated'
        if not _is_authorized():
            msg = 'Not authorized'

        if msg is not None:
            template = loader.get_template('search/csw-2.0.2-exception.xml')
            context = RequestContext(request, {
                'exception_text': msg
            })
            return HttpResponseForbidden(template.render(context), content_type='application/xml')

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

    response = HttpResponse(content, content_type=csw.contenttype)

    response['Access-Control-Allow-Origin'] = '*'
    return response


@csrf_exempt
def csw_global_dispatch_by_catalog(request, catalog_slug):
    """pycsw wrapper"""

    catalog = get_object_or_404(Catalog, slug=catalog_slug)

    # TODO: Implement pycsw per catalog
    if catalog:
        pass

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

    response = HttpResponse(content, content_type=csw.contenttype)

    response['Access-Control-Allow-Origin'] = '*'
    return response


def opensearch_dispatch(request):
    """OpenSearch wrapper"""

    ctx = {
        'shortname': settings.PYCSW['metadata:main']['identification_title'],
        'description': settings.PYCSW['metadata:main']['identification_abstract'],
        'developer': settings.PYCSW['metadata:main']['contact_name'],
        'contact': settings.PYCSW['metadata:main']['contact_email'],
        'attribution': settings.PYCSW['metadata:main']['provider_name'],
        'tags': settings.PYCSW['metadata:main']['identification_keywords'].replace(',', ' '),
        'url': settings.SITE_URL.rstrip('/')
    }

    return render_to_response('search/opensearch_description.xml', ctx,
                              content_type='application/opensearchdescription+xml')


def _is_authenticated():
    """stub to test for authenticated user TODO: implementation"""

    return True


def _is_authorized():
    """stub to test for authorized user TODO: implementation"""

    return True
