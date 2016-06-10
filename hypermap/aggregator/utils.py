import urllib2
import logging
import requests
import re
import sys
import math
import traceback

from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder


LOGGER = logging.getLogger(__name__)


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
                 type=service_type, url=endpoint, title=title, abstract=abstract,
                 csw_type='service'
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
            service_type = 'OSGeo:TMS'
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

    # we can safely assume the following condition (at least it is true for 1170 services)
    # we need to test this as ArcFolder can freeze with not esri url such as this one:
    # http://hh.worldmap.harvard.edu/admin/aggregator/service/?q=%2Frest%2Fservices
    if '/rest/services' in endpoint:
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
                    'ESRI:ArcGIS:ImageServer',
                    '',
                    esri_service.serviceDescription
                )
            if '/MapServer/' in esri_service.url:
                # we import only MapServer with at least one layer
                if hasattr(esri_service, 'layers'):
                    service = create_service_from_endpoint(
                        esri_service.url,
                        'ESRI:ArcGIS:MapServer',
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


def get_esri_extent(esriobj):
    """
    Get the extent of an ESRI resource
    """

    extent = None
    srs = None

    if 'fullExtent' in esriobj._json_struct:
        extent = esriobj._json_struct['fullExtent']
    if 'extent' in esriobj._json_struct:
        extent = esriobj._json_struct['extent']

    try:
        srs = extent['spatialReference']['wkid']
    except KeyError as err:
        LOGGER.error(err)

    return [extent, srs]


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


def bbox2wktpolygon(bbox):
    """
    Return OGC WKT Polygon of a simple bbox string
    """

    minx = float(bbox[0])
    miny = float(bbox[1])
    maxx = float(bbox[2])
    maxy = float(bbox[3])
    return 'POLYGON((%.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f))' \
        % (minx, miny, minx, maxy, maxx, maxy, maxx, miny, minx, miny)
