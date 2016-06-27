# from django.shortcuts import render
from hypermap.aggregator.models import Layer
from djmp.views import get_mapproxy

import logging
log = logging.getLogger('mapproxy.config')


def layer_mapproxy(request,  layer_id, path_info):
    # Get Layer with matching primary key
    layer = get_object_or_404(Layer, pk=layer_id)

    # Set up a mapproxy app for this particular layer
    mp, yaml_config = get_mapproxy(layer)

    query = request.META['QUERY_STRING']

    if len(query) > 0:
        path_info = path_info + '?' + query

    params = {}
    headers = {
       'X-Script-Name': '/layer/%s/map' % layer.id,
       'X-Forwarded-Host': request.META['HTTP_HOST'],
       'HTTP_HOST': request.META['HTTP_HOST'],
       'SERVER_NAME': request.META['SERVER_NAME'],
    }

    if path_info == '/config':
        response = HttpResponse(yaml_config, content_type='text/plain')
        return response

    # Get a response from MapProxy as if it was running standalone.
    mp_response = mp.get(path_info, params, headers)

    # Create a Django response from the MapProxy WSGI response.
    response = HttpResponse(mp_response.body, status=mp_response.status_int)
    for header, value in mp_response.headers.iteritems():
        response[header] = value

    return response
