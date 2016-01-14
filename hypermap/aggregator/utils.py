import urllib2
import re

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
        print 'Creating a %s for endpoint %s' % (service_type, endpoint)
        service, created = Service.objects.get_or_create(
             type=service_type, url=endpoint, title=title, abstract=abstract
        )
        return service


def create_services_from_endpoint(endpoint):
    """
    Generate service/services from an endpoint.
    WMS, WMTS, TMS endpoints correspond to a single service.
    ESRI, CWS endpoints corrispond to many services.
    """
    try:
        urllib2.urlopen(endpoint, timeout=5)
    except urllib2.URLError, e:
        print 'ERROR! Cannot open this endpoint: %s' % endpoint
        print str(e)
        return None

    detected = False

    # test if it is WMS, TMS, WMTS or Esri
    # WMS
    try:
        service = WebMapService(endpoint, timeout=10)
        service_type = 'OGC:WMS'
        detected = True
        create_service_from_endpoint(
            endpoint,
            service_type,
            title=service.identification.title,
            abstract=service.identification.abstract
        )
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
            # folders
            for folder in esri.folders:
                for esri_service in folder.services:
                    if hasattr(esri_service, 'layers'):
                        service = create_service_from_endpoint(
                            esri_service.url,
                            service_type,
                            esri_service.mapName,
                            esri_service.description)

        except Exception as e:
            print str(e)

    if detected:
        print 'OK! Created service/services for %s' % endpoint
    else:
        print 'ERROR! Could not detect service type for endpoint %s' % endpoint
        return None


def get_sanitized_endpoint(url):
    """
    Sanitize an endpoint, as removing unneeded parameters
    """
    # sanitize esri
    sanitized_url = url
    esri_string = '/rest/services'
    if esri_string in url:
        match = re.search(esri_string, sanitized_url)
        sanitized_url = url[0:(match.start(0)+len(esri_string)-1)]
    return sanitized_url
