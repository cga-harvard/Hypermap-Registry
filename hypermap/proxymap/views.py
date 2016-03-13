# from django.shortcuts import render
from aggregator.models import Layer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django_wsgi.embedded_wsgi import call_wsgi_app
from django_wsgi.handler import DjangoWSGIRequest

from mapproxy.config.config import load_default_config, load_config
from mapproxy.config.spec import validate_options
from mapproxy.config.validator import validate_references
from mapproxy.config.loader import ProxyConfiguration, ConfigurationError
from mapproxy.wsgiapp import MapProxyApp

from webtest import TestApp as TestApp_

import yaml
import logging
log = logging.getLogger('mapproxy.config')


class TestApp(TestApp_):
    """
    Wraps webtest.TestApp and explicitly converts URLs to strings.
    Behavior changed with webtest from 1.2->1.3.
    """
    def get(self, url, *args, **kw):
        return TestApp_.get(self, str(url), *args, **kw)

def simple_name(layer_name):
    layer_name = str(layer_name)

    if ':' in layer_name:
        layer_name = layer_name.split(':')[1]

    return layer_name


def get_mapproxy(layer, seed=False, ignore_warnings=True, renderd=False):
    """Creates a mapproxy config for a given layers
    """
    bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]

    if layer.service.type == 'OGC_WMS':
        default_source = {
                 'coverage': {
                  'bbox': bbox,
                  'srs': 'EPSG:4326',
                  'supported_srs' : ['EPSG:4326', 'EPSG:900913'],
                  },
                 'req': {
                    'layers':  simple_name(layer.name),
                    'url': str(layer.service.url),
                  },
                  'type': 'wms',
               }

    elif layer.service.type == 'ESRI_MapServer':
        default_source = {
                  'type': 'tile',
                  'url': str(layer.service.url).split('?')[0] + 'tile/%(z)s/%(y)s/%(x)s',
                  'grid': 'default_grid',
                  #'transparent': True,
               }
    else:
        assert False

    # A source is the WMS config
    sources = {
      'default_source': default_source
    }

    # A grid is where it will be projects (Mercator in our case)
    grids = {
             'default_grid': {
                 'tile_size': [256, 256],
                 'srs': 'EPSG:900913',
                 'origin': 'nw',
                 }
             }

    # A cache that does not store for now. It needs a grid and a source.
    caches = {'default_cache':
               {
               'disable_storage': True,
               'cache':
                   {'type': 'mbtiles',
                    'filename': '/tmp/proxymap-%s.mbtiles' % layer.id,},
                'grids': ['default_grid'],
                'sources': ['default_source']},
    }

    # The layer is connected to the cache
    layers =  [
        {'name': simple_name(layer.name),
         'sources': ['default_cache'],
         'title': str(layer.title),
         },
    ]

    # Services expose all layers.
    # WMS is used for reprojecting
    # TMS is used for easy tiles
    # Demo is used to test our installation, may be disabled in final version
    services =  {
      'wms': {'image_formats': ['image/png'],
              'md': {'abstract': 'This is the Harvard HyperMap Proxy.',
                     'title': 'Harvard HyperMap Proxy'},
              'srs': ['EPSG:4326', 'CRS:83', 'EPSG:900913'],
              'versions': ['1.1.1']},
      'tms': {
              'origin': 'nw',
              },
      'demo': None,
    }

    # Start with a sane configuration using MapProxy's defaults
    conf_options = load_default_config()

    # Populate a dictionary with custom config changes
    extra_config = {
        'caches': caches,
        'grids': grids,
        'layers': layers,
        'services': services,
        'sources': sources,
    }

    # for debugging
    yaml_config = yaml.dump(extra_config, default_flow_style=False)

    # Merge both
    load_config(conf_options, config_dict=extra_config)

    # Make sure the config is valid.
    errors, informal_only = validate_options(conf_options)
    for error in errors:
        log.warn(error)
    if not informal_only or (errors and not ignore_warnings):
        raise ConfigurationError('invalid configuration')

    errors = validate_references(conf_options)
    for error in errors:
        log.warn(error)

    conf = ProxyConfiguration(conf_options, seed=seed, renderd=renderd)

    # Create a MapProxy App
    app = MapProxyApp(conf.configured_services(), conf.base_config)

    # Wrap it in an object that allows to get requests by path as a string.
    return TestApp(app)


def layer_mapproxy(request,  layer_id, path_info):
    # Get Layer with matching primary key
    layer = get_object_or_404(Layer, pk=layer_id)

    # Set up a mapproxy app for this particular layer
    mp = get_mapproxy(layer)

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


    # Get a response from MapProxy as if it was running standalone.
    mp_response = mp.get(path_info, params, headers)


    # Create a Django response from the MapProxy WSGI response.
    response = HttpResponse(mp_response.body, status=mp_response.status_int)
    for header, value in mp_response.headers.iteritems():
        response[header] = value

    return response


def layer_tms(request,  layer_id, z, y, x):
    # Get Layer with matching primary key
    layer = get_object_or_404(Layer, pk=layer_id)

    layer_name = simple_name(layer.name)

    path_info = '/tms/1.0.0/%s/%s/%s/%s.png' % (layer_name, z, y ,x)

    return layer_mapproxy(request, layer_id, path_info)
