# from django.shortcuts import render
from hypermap.aggregator.models import Layer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from mapproxy.config.config import load_default_config, load_config
from mapproxy.config.spec import validate_options
from mapproxy.config.validator import validate_references
from mapproxy.config.loader import ProxyConfiguration, ConfigurationError
from mapproxy.wsgiapp import MapProxyApp

from webtest import TestApp as TestApp_

import os
import yaml
import logging
import tempfile
log = logging.getLogger('mapproxy.config')


class TestApp(TestApp_):
    """
    Wraps webtest.TestApp and explicitly converts URLs to strings.
    Behavior changed with webtest from 1.2->1.3.
    """
    def get(self, url, *args, **kw):
        kw['expect_errors'] = True
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

    url = str(layer.service.url)

    layer_name = simple_name(layer.name)

    srs = 'EPSG:4326'
    bbox_srs = 'EPSG:4326'
    grid_srs = 'EPSG:3857'

    if layer.type == 'WARPER':
        url = str(layer.url.replace("maps//wms", "maps/wms"))
        grid_srs = 'EPSG:900913'

    if layer.type == 'WM':
        url = str(layer.url.replace("maps//wms", "maps/wms"))

    default_source = {
             'type': 'wms',
             'coverage': {
              'bbox': bbox,
              'srs': srs,
              'bbox_srs': bbox_srs,
              'supported_srs': ['EPSG:4326', 'EPSG:900913', 'EPSG:3857'],
              },
             'req': {
                'layers': layer_name,
                'url': url,
                'transparent': True,
              },
           }

    if layer.type == 'ESRI:ArcGIS:MapServer' or layer.type == 'ESRI:ArcGIS:ImageServer':
        # blindly replace it with /arcgis/
        url = url.replace("/ArcGIS/rest/", "/arcgis/")
        # same for uppercase
        url = url.replace("/arcgis/rest/", "/arcgis/")
        # and for old versions
        url = url.replace("ArcX/rest/services", "arcx/services")
        # in uppercase or lowercase
        url = url.replace("arcx/rest/services", "arcx/services")

        srs = 'EPSG:3857'
        bbox_srs = 'EPSG:3857'

        default_source = {
                  'type': 'arcgis',
                  'req': {
                     'url': str(layer.service.url).split('?')[0],
                     'grid': 'default_grid',
                     'transparent': True,
                  },
        }

    # A source is the WMS config
    sources = {
      'default_source': default_source
    }

    # A grid is where it will be projects (Mercator in our case)
    grids = {
             'default_grid': {
                 'tile_size': [256, 256],
                 'srs': grid_srs,
                 'origin': 'nw',
                 }
             }

    # A cache that does not store for now. It needs a grid and a source.
    caches = {'default_cache':
              {
               'cache':
               {
                   'type': 'file',
                   'directory_layout': 'tms',
                   'directory': os.path.join(tempfile.gettempdir(),
                                             'mapproxy',
                                             'layer',
                                             '%s' % layer.id,
                                             'map',
                                             'wmts',
                                             layer_name,
                                             'default_grid',
                                             ),
               },
               'grids': ['default_grid'],
               'sources': ['default_source']},
              }

    # The layer is connected to the cache
    layers = [
        {'name': layer_name,
         'sources': ['default_cache'],
         'title': str(layer.title),
         },
    ]

    # Services expose all layers.
    # WMS is used for reprojecting
    # TMS is used for easy tiles
    # Demo is used to test our installation, may be disabled in final version
    services = {
      'wms': {'image_formats': ['image/png'],
              'md': {'abstract': 'This is the Harvard HyperMap Proxy.',
                     'title': 'Harvard HyperMap Proxy'},
              'srs': ['EPSG:4326', 'EPSG:3857'],
              'versions': ['1.1.1']},
      'wmts': {
              'restful': True,
              'restful_template':
              '/{Layer}/{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.png',
              },
      'tms': {
              'origin': 'nw',
              },
      'demo': None,
    }

    global_config = {
      'http': {'ssl_no_cert_checks': True},
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
        'globals': global_config,
    }

    yaml_config = yaml.dump(extra_config, default_flow_style=False)
    # If you want to test the resulting configuration. Turn on the next
    # line and use that to generate a yaml config.
    # assert False

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
    return TestApp(app), yaml_config


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


def layer_tms(request,  layer_id, z, y, x):
    # Get Layer with matching primary key
    layer = get_object_or_404(Layer, pk=layer_id)

    layer_name = simple_name(layer.name)

    path_info = '/tms/1.0.0/%s/%s/%s/%s.png' % (layer_name, z, y, x)

    return layer_mapproxy(request, layer_id, path_info)
