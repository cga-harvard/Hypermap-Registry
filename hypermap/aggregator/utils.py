import urllib2
import re
import sys
import math
import traceback


from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder

from models import Service


def create_service_from_endpoint(endpoint, service_type, title=None, abstract=None):
    """
    Create a service from an endpoint if it does not already exists.
    """
    if Service.objects.filter(url=endpoint).count() == 0:
        print 'Creating a %s service for endpoint %s' % (service_type, endpoint)
        service = Service(
             type=service_type, url=endpoint, title=title, abstract=abstract
        )
        service.save()
        return service
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
    if not detected:
        try:
            esri = ArcFolder(endpoint)
            services = esri.services
            service_type = 'ESRI'
            detected = True

            # root
            for esri_service in services:
                if hasattr(esri_service, 'layers'):
                    service = create_service_from_endpoint(
                        esri_service.url,
                        service_type,
                        esri_service.mapName,
                        esri_service.description
                    )
                    if service is not None:
                        num_created = num_created + 1
            # folders
            for folder in esri.folders:
                for esri_service in folder.services:
                    if hasattr(esri_service, 'layers'):
                        service = create_service_from_endpoint(
                            esri_service.url,
                            service_type,
                            esri_service.mapName,
                            esri_service.description)
                        if service is not None:
                            num_created = num_created + 1

        except Exception as e:
            print str(e)

    if detected:
        return True, '%s service/s created' % num_created
    else:
        return False, 'ERROR! Could not detect service type for endpoint %s or already existing' % endpoint


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
