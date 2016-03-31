import urllib2
import requests
import re
import sys
import math
import traceback
import json
import datetime
from dateutil.parser import parse

from django.core.urlresolvers import reverse

from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder
from arcrest import MapService as ArcMapService, ImageService as ArcImageService

from models import Layer, LayerDate, LayerWM, SpatialReferenceSystem


def create_service_from_endpoint(endpoint, service_type, title=None, abstract=None):
    """
    Create a service from an endpoint if it does not already exists.
    """
    from models import Service
    if Service.objects.filter(url=endpoint).count() == 0:
        # check if endpoint is valid
        request = requests.get(endpoint)
        if request.status_code == 200:
            print 'Creating a %s service for endpoint %s' % (service_type, endpoint)
            service = Service(
                 type=service_type, url=endpoint, title=title, abstract=abstract
            )
            service.save()
            return service
        else:
            print 'This endpoint is invalid, status code is %s' % request.status_code
    else:
        print 'A service for this endpoint %s already exists' % endpoint
        return None


def create_services_from_endpoint(url):
    """
    Generate service/services from an endpoint.
    WMS, WMTS, TMS endpoints correspond to a single service.
    ESRI, CWS endpoints corrispond to many services.
    """
    num_created = 0
    endpoint = get_sanitized_endpoint(url)
    try:
        urllib2.urlopen(endpoint, timeout=10)
    except Exception as e:
        print 'ERROR! Cannot open this endpoint: %s' % endpoint
        message = traceback.format_exception(*sys.exc_info())
        return False, message

    detected = False

    # test if it is WMS, TMS, WMTS or Esri
    # WMS
    try:
        service = WebMapService(endpoint, timeout=10)
        service_type = 'OGC:WMS'
        detected = True
        service = create_service_from_endpoint(
            endpoint,
            service_type,
            title=service.identification.title,
            abstract=service.identification.abstract
        )
        if service is not None:
            num_created = num_created + 1
    except Exception as e:
        print str(e)

    # TMS
    if not detected:
        try:
            service = TileMapService(endpoint, timeout=10)
            service_type = 'OGC:TMS'
            detected = True
            create_service_from_endpoint(
                endpoint,
                service_type,
                title=service.identification.title,
                abstract=service.identification.abstract
            )
            if service is not None:
                num_created = num_created + 1
        except Exception as e:
            print str(e)

    # WMTS
    if not detected:
        try:
            service = WebMapTileService(endpoint, timeout=10)
            service_type = 'OGC:WMTS'
            detected = True
            create_service_from_endpoint(
                endpoint,
                service_type,
                title=service.identification.title,
                abstract=service.identification.abstract
            )
            if service is not None:
                num_created = num_created + 1
        except Exception as e:
            print str(e)

    # Esri
    # a good sample is here: https://gis.ngdc.noaa.gov/arcgis/rest/services
    if not detected:
        try:
            esri = ArcFolder(endpoint)
            services = esri.services

            service_type = 'ESRI'
            detected = True

            # root
            root_services = process_esri_services(services)
            num_created = num_created + len(root_services)

            # folders
            for folder in esri.folders:
                folder_services = process_esri_services(folder.services)
                num_created = num_created + len(folder_services)

        except Exception as e:
            print str(e)

    if detected:
        return True, '%s service/s created' % num_created
    else:
        return False, 'ERROR! Could not detect service type for endpoint %s or already existing' % endpoint


def process_esri_services(esri_services):
    services_created = []
    for esri_service in esri_services:
        # for now we process only MapServer and ImageServer
        if '/MapServer/' in esri_service.url or '/ImageServer/' in esri_service.url:
            if '/ImageServer/' in esri_service.url:
                service = create_service_from_endpoint(
                    esri_service.url,
                    'ESRI_ImageServer',
                    '',
                    esri_service.serviceDescription
                )
            if '/MapServer/' in esri_service.url:
                # we import only MapServer with at least one layer
                if hasattr(esri_service, 'layers'):
                    service = create_service_from_endpoint(
                        esri_service.url,
                        'ESRI_MapServer',
                        esri_service.mapName,
                        esri_service.description
                    )
            services_created.append(service)
    return services_created


def inverse_mercator(xy):
    """
        Given coordinates in spherical mercator, return a lon,lat tuple.
    """
    lon = (xy[0] / 20037508.34) * 180
    lat = (xy[1] / 20037508.34) * 180
    lat = 180 / math.pi * \
        (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
    return (lon, lat)


def mercator_to_llbbox(bbox):
    minlonlat = inverse_mercator([bbox[0], bbox[1]])
    maxlonlat = inverse_mercator([bbox[2], bbox[3]])
    return [minlonlat[0], minlonlat[1], maxlonlat[0], maxlonlat[1]]


def get_sanitized_endpoint(url):
    """
    Sanitize an endpoint, as removing unneeded parameters
    """
    # sanitize esri
    sanitized_url = url
    esri_string = '/rest/services'
    if esri_string in url:
        match = re.search(esri_string, sanitized_url)
        sanitized_url = url[0:(match.start(0)+len(esri_string))]
    return sanitized_url


def get_esri_service_name(url):
    """
    A method to get a service name from an esri endpoint.
    For example: http://example.com/arcgis/rest/services/myservice/mylayer/MapServer/?f=json
    Will return: myservice/mylayer
    """
    result = re.search('rest/services/(.*)/[MapServer|ImageServer]', url)
    if result is None:
        return url
    else:
        return result.group(1)


def flip_coordinates(c1, c2):
    if c1 > c2:
        print 'Flipping coordinates %s, %s' % (c1, c2)
        temp = c1
        c1 = c2
        c2 = temp
    return c1, c2


def format_float(value):
    if value is None:
        return None
    try:
        value = float(value)
        if value > 999999999:
            return None
        return value
    except ValueError:
        return None


def add_dates_to_layer(dates, layer):
    default = datetime.datetime(2016, 1, 1)
    for date in dates:
        if date:
            date = '%s' % date
            if date != '':
                dt = parse(date, default=default)
                iso_date = dt.isoformat()
                print 'Adding date %s to layer %s' % (iso_date, layer.id)
                layerdate, created = LayerDate.objects.get_or_create(layer=layer, date=iso_date, type=1)


def update_layers_wms(service):
    """
    Update layers for an OGC_WMS service.
    """
    wms = WebMapService(service.url)
    layer_names = list(wms.contents)
    for layer_name in layer_names:
        ows_layer = wms.contents[layer_name]
        print 'Updating layer %s' % ows_layer.name
        # get or create layer
        layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service)
        if layer.active:
            # update fields
            layer.title = ows_layer.title
            layer.abstract = ows_layer.abstract
            layer.url = service.url
            layer.page_url = reverse('layer_detail', kwargs={'layer_id': layer.id})
            # bbox
            bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
            layer.bbox_x0 = bbox[0]
            layer.bbox_y0 = bbox[1]
            layer.bbox_x1 = bbox[2]
            layer.bbox_y1 = bbox[3]
            # keywords
            for keyword in ows_layer.keywords:
                layer.keywords.add(keyword)
            # crsOptions
            # TODO we may rather prepopulate with fixutres the SpatialReferenceSystem table
            for crs_code in ows_layer.crsOptions:
                srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
                layer.srs.add(srs)
            layer.save()


def update_layers_wmts(service):
    """
    Update layers for an OGC_WMTS service.
    """
    wmts = WebMapTileService(service.url)
    layer_names = list(wmts.contents)
    for layer_name in layer_names:
        ows_layer = wmts.contents[layer_name]
        print 'Updating layer %s' % ows_layer.name
        layer, created = Layer.objects.get_or_create(name=ows_layer.name, service=service)
        if layer.active:
            layer.title = ows_layer.title
            layer.abstract = ows_layer.abstract
            layer.url = service.url
            layer.page_url = reverse('layer_detail', kwargs={'layer_id': layer.id})
            bbox = list(ows_layer.boundingBoxWGS84 or (-179.0, -89.0, 179.0, 89.0))
            layer.bbox_x0 = bbox[0]
            layer.bbox_y0 = bbox[1]
            layer.bbox_x1 = bbox[2]
            layer.bbox_y1 = bbox[3]
            layer.save()


def update_layers_wm(service):
    """
    Update layers for an WorldMap.
    """
    response = requests.get('http://worldmap.harvard.edu/data/search/api?start=0&limit=10')
    data = json.loads(response.content)
    total = data['total']

    for i in range(0, total, 10):
        url = 'http://worldmap.harvard.edu/data/search/api?start=%s&limit=10' % i
        print 'Fetching %s' % url
        response = requests.get(url)
        data = json.loads(response.content)
        for row in data['rows']:
            name = row['name']
            title = row['title']
            abstract = row['abstract']
            bbox = row['bbox']
            page_url = row['detail']
            category = ''
            if 'topic_category' in row:
                category = row['topic_category']
            username = ''
            if 'owner_username' in row:
                username = row['owner_username']
            temporal_extent_start = ''
            if 'temporal_extent_start' in row:
                temporal_extent_start = row['temporal_extent_start']
            temporal_extent_end = ''
            if 'temporal_extent_end' in row:
                temporal_extent_end = row['temporal_extent_end']
            # we use the geoserver virtual layer getcapabilities for wm endpoint
            endpoint = 'http://worldmap.harvard.edu/geoserver/geonode/%s/wms?' % name
            is_public = True
            if '_permissions' in row:
                if not row['_permissions']['view']:
                    is_public = False
            layer, created = Layer.objects.get_or_create(name=name, service=service)
            if layer.active:
                # update fields
                layer.title = title
                layer.abstract = abstract
                layer.is_public = is_public
                layer.url = endpoint
                layer.page_url = page_url
                # category and owner username
                layer_wm, created = LayerWM.objects.get_or_create(layer=layer)
                layer_wm.category = category
                layer_wm.username = username
                layer_wm.temporal_extent_start = temporal_extent_start
                layer_wm.temporal_extent_end = temporal_extent_end
                layer_wm.save()
                # bbox
                x0 = format_float(bbox['minx'])
                y0 = format_float(bbox['miny'])
                x1 = format_float(bbox['maxx'])
                y1 = format_float(bbox['maxy'])
                # In many cases for some reason to be fixed GeoServer has x coordinates flipped in WM.
                x0, x1 = flip_coordinates(x0, x1)
                y0, y1 = flip_coordinates(y0, y1)
                layer.bbox_x0 = x0
                layer.bbox_y0 = y0
                layer.bbox_x1 = x1
                layer.bbox_y1 = y1
                # keywords
                for keyword in row['keywords']:
                    layer.keywords.add(keyword)
                # crsOptions
                for crs_code in [3857, 4326, 900913]:
                    srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
                    layer.srs.add(srs)
                layer.save()


def update_layers_warper(service):
    """
    Update layers for a Warper service.
    """
    params = {'field': 'title', 'query': '', 'show_warped': '1', 'format': 'json'}
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    request = requests.get(service.url, headers=headers, params=params)
    records = json.loads(request.content)
    total_pages = int(records['total_pages'])

    for i in range(1, total_pages + 1):
        params = {'field': 'title', 'query': '', 'show_warped': '1', 'format': 'json', 'page': i}
        request = requests.get(service.url, headers=headers, params=params)
        records = json.loads(request.content)
        print 'Fetched %s' + request.url
        layers = records['items']
        for layer in layers:
            name = layer['id']
            title = layer['title']
            abstract = layer['description']
            bbox = layer['bbox']
            # dates
            dates = []
            if 'published_date' in layer:
                dates.append(layer['published_date'])
            if 'date_depicted' in layer:
                dates.append(layer['date_depicted'])
            if 'depicts_year' in layer:
                dates.append(layer['depicts_year'])
            if 'issue_year' in layer:
                dates.append(layer['issue_year'])
            layer, created = Layer.objects.get_or_create(name=name, service=service)
            if layer.active:
                # update fields
                layer.title = title
                layer.abstract = abstract
                layer.is_public = True
                layer.url = '%s/wms/%s?' % (service.url, name)
                layer.page_url = '%s/%s' % (service.url, name)
                # bbox
                x0 = None
                y0 = None
                x1 = None
                y1 = None
                if bbox:
                    bbox_list = bbox.split(',')
                    x0 = format_float(bbox_list[0])
                    y0 = format_float(bbox_list[1])
                    x1 = format_float(bbox_list[2])
                    y1 = format_float(bbox_list[3])
                layer.bbox_x0 = x0
                layer.bbox_y0 = y0
                layer.bbox_x1 = x1
                layer.bbox_y1 = y1
                # crsOptions
                for crs_code in [3857, 4326, 900913]:
                    srs, created = SpatialReferenceSystem.objects.get_or_create(code=crs_code)
                    layer.srs.add(srs)
                layer.save()
                add_dates_to_layer(dates, layer)


def update_layers_esri_mapserver(service):
    """
    Update layers for an ESRI REST MapServer.
    """
    esri_service = ArcMapService(service.url)
    # check if it has a WMS interface
    if 'supportedExtensions' in esri_service._json_struct:
        if 'WMSServer' in esri_service._json_struct['supportedExtensions']:
            # we need to change the url
            # http://cga1.cga.harvard.edu/arcgis/rest/services/ecuador/ecuadordata/MapServer?f=pjson
            # http://cga1.cga.harvard.edu/arcgis/services/ecuador/ecuadordata/MapServer/WMSServer?request=GetCapabilities&service=WMS
            wms_url = service.url.replace('/rest/services/', '/services/')
            if '?f=pjson' in wms_url:
                wms_url = wms_url.replace('?f=pjson', 'WMSServer?')
            if '?f=json' in wms_url:
                wms_url = wms_url.replace('?f=json', 'WMSServer?')
            print 'This ESRI REST endpoint has an WMS interface to process: %s' % wms_url
            # import here as otherwise is circular (TODO refactor)
            from utils import create_service_from_endpoint
            create_service_from_endpoint(wms_url, 'OGC_WMS')
    # now process the REST interface
    for esri_layer in esri_service.layers:
        # in some case the json is invalid
        # esri_layer._json_struct
        # {u'currentVersion': 10.01,
        # u'error':
        # {u'message': u'An unexpected error occurred processing the request.', u'code': 500, u'details': []}}
        if 'error' not in esri_layer._json_struct:
            print 'Updating layer %s' % esri_layer.name
            layer, created = Layer.objects.get_or_create(name=esri_layer.id, service=service)
            if layer.active:
                layer.title = esri_layer.name
                layer.abstract = esri_service.serviceDescription
                layer.url = service.url
                layer.page_url = reverse('layer_detail', kwargs={'layer_id': layer.id})
                # set a default srs
                srs = 4326
                try:
                    layer.bbox_x0 = esri_layer.extent.xmin
                    layer.bbox_y0 = esri_layer.extent.ymin
                    layer.bbox_x1 = esri_layer.extent.xmax
                    layer.bbox_y1 = esri_layer.extent.ymax
                    # crsOptions
                    srs = esri_layer.extent.spatialReference.wkid
                    # this is needed as esri_layer.extent can fail because of custom wkid in json
                except KeyError:
                    pass
                try:
                    layer.bbox_x0 = esri_layer._json_struct['extent']['xmin']
                    layer.bbox_y0 = esri_layer._json_struct['extent']['ymin']
                    layer.bbox_x1 = esri_layer._json_struct['extent']['xmax']
                    layer.bbox_y1 = esri_layer._json_struct['extent']['ymax']
                    wkt_text = esri_layer._json_struct['extent']['spatialReference']['wkt']
                    if wkt_text:
                        params = {'exact': 'True', 'error': 'True', 'mode': 'wkt', 'terms': wkt_text}
                        req = requests.get('http://prj2epsg.org/search.json', params=params)
                        object = json.loads(req.content)
                        srs = int(object['codes'][0]['code'])
                except Exception:
                    pass
                layer.save()
                srs, created = SpatialReferenceSystem.objects.get_or_create(code=srs)
                layer.srs.add(srs)


def update_layers_esri_imageserver(service):
    """
    Update layers for an ESRI REST ImageServer.
    """
    esri_service = ArcImageService(service.url)
    obj = json.loads(esri_service._contents)
    layer, created = Layer.objects.get_or_create(name=obj['name'], service=service)
    if layer.active:
        layer.title = obj['name']
        layer.abstract = esri_service.serviceDescription
        layer.url = service.url
        layer.bbox_x0 = str(obj['extent']['xmin'])
        layer.bbox_y0 = str(obj['extent']['ymin'])
        layer.bbox_x1 = str(obj['extent']['xmax'])
        layer.bbox_y1 = str(obj['extent']['ymax'])
        layer.page_url = reverse('layer_detail', kwargs={'layer_id': layer.id})
        layer.save()
        # crsOptions
        srs = obj['spatialReference']['wkid']
        srs, created = SpatialReferenceSystem.objects.get_or_create(code=srs)
        layer.srs.add(srs)
