# from django.shortcuts import render

# Create your views here.

import os

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import loader, RequestContext
from django.views.decorators.csrf import csrf_exempt
from django_basic_auth import logged_in_or_basicauth

from pycsw import server

from hypermap.aggregator.models import Catalog


@csrf_exempt
@logged_in_or_basicauth()
def csw_global_dispatch(request, url=None, catalog_id=None):
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

    # TODO: remove this workaround
    # HH should be able to pass env['wsgi.input'] without hanging
    # details at https://github.com/cga-harvard/HHypermap/issues/94
    if request.method == 'POST':
        from StringIO import StringIO
        env['wsgi.input'] = StringIO(request.body)

    env.update({'local.app_root': os.path.dirname(__file__),
                'REQUEST_URI': request.build_absolute_uri()})

    # if this is a catalog based CSW, then update settings
    if url is not None:
        settings.REGISTRY_PYCSW['server']['url'] = url
    if catalog_id is not None:
        settings.REGISTRY_PYCSW['repository']['filter'] = 'catalog_id = %d' % catalog_id

    csw = server.Csw(settings.REGISTRY_PYCSW, env, version='2.0.2')

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
@logged_in_or_basicauth()
def csw_global_dispatch_by_catalog(request, catalog_slug):
    """pycsw wrapper for catalogs"""

    catalog = get_object_or_404(Catalog, slug=catalog_slug)

    if catalog:  # define catalog specific settings
        url = settings.SITE_URL.rstrip('/') + request.path.rstrip('/')
        return csw_global_dispatch(request, url=url, catalog_id=catalog.id)


def opensearch_dispatch(request):
    """OpenSearch wrapper"""

    ctx = {
        'shortname': settings.REGISTRY_PYCSW['metadata:main']['identification_title'],
        'description': settings.REGISTRY_PYCSW['metadata:main']['identification_abstract'],
        'developer': settings.REGISTRY_PYCSW['metadata:main']['contact_name'],
        'contact': settings.REGISTRY_PYCSW['metadata:main']['contact_email'],
        'attribution': settings.REGISTRY_PYCSW['metadata:main']['provider_name'],
        'tags': settings.REGISTRY_PYCSW['metadata:main']['identification_keywords'].replace(',', ' '),
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
