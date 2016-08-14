import urllib2
import logging
import requests
import re
import sys
import math
import traceback
from urlparse import urlparse

from django.conf import settings
from lxml import etree
from owslib.csw import CatalogueServiceWeb, CswRecord
from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder

from hypermap.aggregator.enums import SERVICE_TYPES
from lxml.etree import XMLSyntaxError

LOGGER = logging.getLogger(__name__)


def create_layer_from_metadata_xml(resourcetype, xml, monitor=False):
    """
    Create a layer / keyword list from a metadata record if it does not already exist.
    """
    from models import gen_anytext, Layer

    if resourcetype == 'http://www.opengis.net/cat/csw/2.0.2':  # Dublin core
        md = CswRecord(etree.fromstring(xml))

    layer = Layer(
        is_monitored=monitor,
        name=md.title,
        title=md.title,
        abstract=md.abstract,
        bbox_x0=format_float(md.bbox.minx),
        bbox_y0=format_float(md.bbox.miny),
        bbox_x1=format_float(md.bbox.maxx),
        bbox_y1=format_float(md.bbox.maxy),
        xml=xml,
        anytext=gen_anytext(md.title, md.abstract, md.subjects)
    )

    layer.wkt_geometry = bbox2wktpolygon([md.bbox.minx, md.bbox.miny, md.bbox.maxx, md.bbox.maxy])

    return layer, md.subjects


def create_service_from_endpoint(endpoint, service_type, title=None, abstract=None, catalog=None):
    """
    Create a service from an endpoint if it does not already exists.
    """
    from models import Service
    if Service.objects.filter(url=endpoint, catalog=catalog).count() == 0:
        # check if endpoint is valid
        request = requests.get(endpoint)
        if request.status_code == 200:
            print 'Creating a %s service for endpoint=%s catalog=%s' % (service_type, endpoint, catalog)
            service = Service(
                        type=service_type, url=endpoint, title=title, abstract=abstract,
                        csw_type='service', catalog=catalog
                        )
            service.save()
            return service
        else:
            print 'This endpoint is invalid, status code is %s' % request.status_code
    else:
        print 'A service for this endpoint %s in catalog %s already exists' % (endpoint, catalog)
        return None


def create_services_from_endpoint(url, catalog, greedy_opt=True):
    """
    Generate service/services from an endpoint.
    WMS, WMTS, TMS endpoints correspond to a single service.
    ESRI, CSW endpoints corrispond to many services.
    :return: imported, message
    """

    # this variable will collect any exception message during the routine.
    # will be used in the last step to send a message if "detected" var is False.
    messages = []

    num_created = 0
    endpoint = get_sanitized_endpoint(url)
    try:
        urllib2.urlopen(endpoint, timeout=10)
    except Exception as e:
        message = traceback.format_exception(*sys.exc_info())
        print 'ERROR! Cannot open this endpoint: %s' % endpoint
        print 'ERROR MESSAGE: %s' % message
        return False, message

    detected = False

    # handle specific service types for some domains (WorldMap, Wrapper...)
    parsed_uri = urlparse(endpoint)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    if domain == 'http://worldmap.harvard.edu/':
        service_type = 'Hypermap:WorldMap'
        title = 'Harvard WorldMap'
        abstract = 'Harvard WorldMap'
        endpoint = domain
        detected = True
    if domain in [
        'http://maps.nypl.org/',
        'http://mapwarper.net/',
        'http://warp.worldmap.harvard.edu/',
    ]:
        service_type = 'Hypermap:WARPER'
        title = 'Warper at %s' % domain
        abstract = 'Warper at %s' % domain
        detected = True

    # test if it is CSW, WMS, TMS, WMTS or Esri
    # CSW
    try:
        csw = CatalogueServiceWeb(endpoint)
        service_type = 'OGC:CSW'
        service_links = {}
        detected = True

        typenames = 'csw:Record'
        outputschema = 'http://www.opengis.net/cat/csw/2.0.2'

        if 'csw_harvest_pagesize' in settings.PYCSW['manager']:
            pagesize = int(settings.PYCSW['manager']['csw_harvest_pagesize'])
        else:
            pagesize = 10

        print 'Harvesting CSW %s' % endpoint
        # now get all records
        # get total number of records to loop against
        try:
            csw.getrecords2(typenames=typenames, resulttype='hits',
                            outputschema=outputschema)
            matches = csw.results['matches']
        except:  # this is a CSW, but server rejects query
            raise RuntimeError(csw.response)

        if pagesize > matches:
            pagesize = matches

        print 'Harvesting %d CSW records' % matches

        # loop over all catalogue records incrementally
        for r in range(1, matches+1, pagesize):
            try:
                csw.getrecords2(typenames=typenames, startposition=r,
                                maxrecords=pagesize, outputschema=outputschema, esn='full')
            except Exception as err:  # this is a CSW, but server rejects query
                raise RuntimeError(csw.response)
            for k, v in csw.records.items():
                # try to parse metadata
                try:
                    LOGGER.info('Looking for service links')
                    if v.references:  # not empty
                        for ref in v.references:
                            if ref['scheme'] in [st[0] for st in SERVICE_TYPES]:
                                if ref['url'] not in service_links:
                                    service_links[ref['url']] = ref['scheme']
                except Exception as err:  # parsing failed for some reason
                    LOGGER.warning('Metadata parsing failed %s', err)

        LOGGER.info('Service links found: %s', service_links)
        for k, v in service_links.items():
            try:
                service = create_service_from_endpoint(k, v, catalog=catalog)
                if service is not None:
                    num_created = num_created + 1
            except Exception as err:
                raise RuntimeError('HHypermap error: %s' % err)
    except XMLSyntaxError as e:
        # This is not XML, so likely not a CSW. Moving on.
        pass
    except Exception as e:
        print str(e)
        messages.append(str(e))

    # WMS
    if not detected:
        try:
            service = WebMapService(endpoint, timeout=10)
            service_type = 'OGC:WMS'
            title = service.identification.title,
            abstract = service.identification.abstract
            detected = True
        except XMLSyntaxError as e:
            # This is not XML, so likely not a WMS. Moving on.
            pass
        except Exception as e:
            print str(e)
            messages.append(str(e))

    # TMS
    if not detected:
        try:
            service = TileMapService(endpoint, timeout=10)
            service_type = 'OSGeo:TMS'
            title = service.identification.title,
            abstract = service.identification.abstract
            detected = True
        except XMLSyntaxError as e:
            # This is not XML, so likely not a TsMS. Moving on.
            pass
        except Exception as e:
            print str(e)
            messages.append(str(e))

    # WMTS
    if not detected:
        try:
            # @tomkralidis timeout is not implemented for WebMapTileService?
            service = WebMapTileService(endpoint)
            service_type = 'OGC:WMTS'
            title = service.identification.title,
            abstract = service.identification.abstract
            detected = True
        except XMLSyntaxError as e:
            # This is not XML, so likely not a WMTS. Moving on.
            pass
        except Exception as e:
            print str(e)
            messages.append(str(e))

    # if detected, let's create the service
    if detected and service_type != 'OGC:CSW':
        try:
            service = create_service_from_endpoint(
                endpoint,
                service_type,
                title,
                abstract=abstract,
                catalog=catalog
            )
            if service is not None:
                num_created = num_created + 1
        except XMLSyntaxError as e:
            # This is not XML, so likely not a OGC:CSW. Moving on.
            pass
        except Exception as e:
            print str(e)
            messages.append(str(e))

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

                # Enable the user to fetch a single service of a single folder.
                if not greedy_opt:
                    # Get folder and service from endpoint url.
                    url_token = '/rest/services/'
                    components = url.strip().split(url_token)[1].split('/')
                    esri_folder, esri_service = components[0], components[1]

                    def split_service(s):
                        return s.url.split(url_token)[1].split('/')

                    # Get folder class from the list of esri services for the given endpoint.
                    services_folder = [f for f in esri.folders if split_service(f)[0] == esri_folder][0]

                    fs = services_folder.services

                    # Get service class from the folder for the given endpoint.
                    service_to_process = [s for s in fs if split_service(s)[1] == esri_service]

                    folder_services = process_esri_services(service_to_process, catalog=catalog)
                    num_created = num_created + len(folder_services)
                else:
                    root_services = process_esri_services(services, catalog=catalog)
                    num_created = num_created + len(root_services)
                    for folder in esri.folders:
                        folder_services = process_esri_services(folder.services, catalog=catalog)
                        num_created = num_created + len(folder_services)
            except Exception as e:
                print str(e)
                messages.append(str(e))

    if detected:
        return True, '%s service/s created' % num_created
    else:
        m = '|'.join(messages)
        return False, 'ERROR! Could not detect service type for ' \
                      'endpoint %s or already existing. messages=(%s)' % (endpoint, m)


def process_esri_services(esri_services, catalog):
    services_created = []
    for esri_service in esri_services:
        # for now we process only MapServer
        if '/MapServer/' in esri_service.url:
            # we import only MapServer with at least one layer
            if hasattr(esri_service, 'layers'):
                service = create_service_from_endpoint(
                    esri_service.url,
                    'ESRI:ArcGIS:MapServer',
                    esri_service.mapName,
                    esri_service.description,
                    catalog=catalog
                )
                services_created.append(service)

        # Don't process ImageServer until the following issue has been resolved:
        # https://github.com/mapproxy/mapproxy/issues/235
        # if '/ImageServer/' in esri_service.url:
        #     service = create_service_from_endpoint(
        #         esri_service.url,
        #         'ESRI:ArcGIS:ImageServer',
        #         '',
        #         esri_service.serviceDescription
        #     )
        #      services_created.append(service)

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
    sanitized_url = url.rstrip()
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
    Return OGC WKT Polygon of a simple bbox list of strings
    """

    minx = float(bbox[0])
    miny = float(bbox[1])
    maxx = float(bbox[2])
    maxy = float(bbox[3])
    return 'POLYGON((%.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f))' \
        % (minx, miny, minx, maxy, maxx, maxy, maxx, miny, minx, miny)
