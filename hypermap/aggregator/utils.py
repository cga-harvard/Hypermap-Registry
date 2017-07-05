import arcrest
import urllib2
import logging
import requests
import re
import sys
import math
import traceback
import datetime
from urlparse import urlparse

from django.utils.html import strip_tags
from django.conf import settings

from lxml import etree
from owslib.csw import CatalogueServiceWeb, CswRecord
from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService

from hypermap.aggregator.enums import SERVICE_TYPES
from lxml.etree import XMLSyntaxError
from shapely.geometry import box

LOGGER = logging.getLogger(__name__)


def create_layer_from_metadata_xml(resourcetype, xml, monitor=False, service=None, catalog=None):
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
        xml=xml,
        service=service,
        catalog=catalog,
        anytext=gen_anytext(md.title, md.abstract, md.subjects)
    )

    if hasattr(md, 'alternative'):
        layer.name = md.alternative

    if md.bbox is not None:
        layer.bbox_x0 = format_float(md.bbox.minx)
        layer.bbox_y0 = format_float(md.bbox.miny)
        layer.bbox_x1 = format_float(md.bbox.maxx)
        layer.bbox_y1 = format_float(md.bbox.maxy)

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
            LOGGER.debug('Creating a %s service for endpoint=%s catalog=%s' % (service_type, endpoint, catalog))
            service = Service(
                        type=service_type, url=endpoint, title=title, abstract=abstract,
                        csw_type='service', catalog=catalog
                        )
            service.save()
            return service
        else:
            LOGGER.warning('This endpoint is invalid, status code is %s' % request.status_code)
    else:
        LOGGER.warning('A service for this endpoint %s in catalog %s already exists' % (endpoint, catalog))
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
        LOGGER.error('Cannot open this endpoint: %s' % endpoint)
        LOGGER.error('ERROR MESSAGE: %s' % message)
        LOGGER.error(e, exc_info=True)

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

        if 'csw_harvest_pagesize' in settings.REGISTRY_PYCSW['manager']:
            pagesize = int(settings.REGISTRY_PYCSW['manager']['csw_harvest_pagesize'])
        else:
            pagesize = 10

        LOGGER.debug('Harvesting CSW %s' % endpoint)
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

        LOGGER.info('Harvesting %d CSW records' % matches)

        # loop over all catalogue records incrementally
        for r in range(1, matches+1, pagesize):
            LOGGER.info('Parsing %s from %s' % (r, matches))
            try:
                csw.getrecords2(typenames=typenames, startposition=r,
                                maxrecords=pagesize, outputschema=outputschema, esn='full')
            except Exception as err:  # this is a CSW, but server rejects query
                raise RuntimeError(csw.response)
            for k, v in csw.records.items():
                # try to parse metadata
                try:
                    LOGGER.info('Looking for service links')

                    LOGGER.debug('Looking for service links via dct:references')
                    if v.references:
                        for ref in v.references:
                            scheme = None

                            if ref['scheme'] in [st[0] for st in SERVICE_TYPES]:
                                if ref['url'] not in service_links:
                                    scheme = ref['scheme']
                                    service_links[ref['url']] = scheme
                            else:  # loose detection
                                scheme = detect_metadata_url_scheme(ref['url'])
                                if scheme is not None:
                                    if ref['url'] not in service_links:
                                        service_links[ref['url']] = scheme

                            if scheme is None:
                                continue
                            try:
                                service = create_service_from_endpoint(ref['url'], scheme, catalog=catalog)

                                if service is not None:
                                    num_created = num_created + 1
                                    LOGGER.info('Found %s services on endpoint' % num_created)
                            except Exception, e:
                                LOGGER.error('Could not create service for %s : %s' % (scheme, ref['url']))
                                LOGGER.error(e, exc_info=True)
                    LOGGER.debug('Looking for service links via the GeoNetwork-ish dc:URI')
                    if v.uris:
                        for u in v.uris:  # loose detection
                            scheme = detect_metadata_url_scheme(u['url'])
                            if scheme is not None:
                                if u['url'] not in service_links:
                                    service_links[u['url']] = scheme
                            else:
                                continue

                            try:
                                service = create_service_from_endpoint(u['url'], scheme, catalog=catalog)

                                if service is not None:
                                    num_created = num_created + 1
                                    LOGGER.info('Found %s services on endpoint' % num_created)
                            except Exception, e:
                                LOGGER.error('Could not create service for %s : %s' % (scheme, u['url']))
                                LOGGER.error(e, exc_info=True)

                except Exception as err:  # parsing failed for some reason
                    LOGGER.warning('Metadata parsing failed %s', err)
                    LOGGER.error(err, exc_info=True)

    except XMLSyntaxError as e:
        # This is not XML, so likely not a CSW. Moving on.
        pass
    except Exception as e:
        LOGGER.error(e, exc_info=True)
        messages.append(str(e))

    # WMS
    if not detected:
        try:
            service = get_wms_version_negotiate(endpoint, timeout=10)
            service_type = 'OGC:WMS'
            title = service.identification.title,
            abstract = service.identification.abstract
            detected = True
        except XMLSyntaxError as e:
            # This is not XML, so likely not a WMS. Moving on.
            pass
        except Exception as e:
            LOGGER.error(e, exc_info=True)
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
            LOGGER.error(e, exc_info=True)
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
            LOGGER.error(e, exc_info=True)
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
            LOGGER.error(e, exc_info=True)
            messages.append(str(e))

    # Esri
    # a good sample is here: https://gis.ngdc.noaa.gov/arcgis/rest/services

    # we can safely assume the following condition (at least it is true for 1170 services)
    # we need to test this as arcrest.Folder can freeze with not esri url such as this one:
    # http://hh.worldmap.harvard.edu/admin/aggregator/service/?q=%2Frest%2Fservices

    if '/rest/services' in endpoint:
        if not detected:
            try:
                esri = arcrest.Folder(endpoint)
                service_type = 'ESRI'
                detected = True

                service_to_process, folder_to_process = esri.services, esri.folders
                if not greedy_opt:
                    folder_to_process = []
                    sections = service_url_parse(url)
                    service_to_process = get_single_service(esri, sections)

                processed_services = process_esri_services(service_to_process, catalog)
                num_created = num_created + len(processed_services)

                for folder in folder_to_process:
                    folder_services = process_esri_services(folder.services, catalog)
                    num_created = num_created + len(folder_services)

            except Exception as e:
                LOGGER.error(e, exc_info=True)
                messages.append(str(e))

    if detected:
        return True, '%s service/s created' % num_created
    else:
        m = '|'.join(messages)
        return False, 'ERROR! Could not detect service type for ' \
                      'endpoint %s or already existing. messages=(%s)' % (endpoint, m)


def service_url_parse(url):
    """
    Function that parses from url the service and folder of services.
    """
    endpoint = get_sanitized_endpoint(url)
    url_split_list = url.split(endpoint + '/')
    if len(url_split_list) != 0:
        url_split_list = url_split_list[1].split('/')
    else:
        raise Exception('Wrong url parsed')

    # Remove unnecessary items from list of the split url.
    parsed_url = [s for s in url_split_list if '?' not in s if 'Server' not in s]

    return parsed_url


def get_single_service(esri, url_sections):
    service_to_process = esri
    for section in url_sections:
        service_to_process = service_to_process[section]

    # Determine return list depending on the type of the object.
    service_type = type(service_to_process)
    if service_type is arcrest.server.Folder:
        service_to_process = service_to_process.services
    elif service_type is arcrest.server.MapService:
        service_to_process = [service_to_process]
    elif service_type is arcrest.server.ImageService:
        service_to_process = [service_to_process]
    # Some services have ImageServer and MapServer in its endpoint (AmbiguousService).
    # We create a list with both services
    else:
        service_dict = service_to_process.__dict__
        service_to_process = {idx: val for idx, val in service_dict.iteritems()
                              if idx in ['ImageServer', 'MapServer']}.values()

    return service_to_process


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

        if '/ImageServer/' in esri_service.url:
            service = create_service_from_endpoint(
                esri_service.url,
                'ESRI:ArcGIS:ImageServer',
                '',
                esri_service.serviceDescription,
                catalog=catalog
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


def get_wms_version_negotiate(url, timeout=10):
    """
    OWSLib wrapper function to perform version negotiation against owslib.wms.WebMapService
    """

    try:
        LOGGER.debug('Trying a WMS 1.3.0 GetCapabilities request')
        return WebMapService(url, version='1.3.0', timeout=timeout)
    except Exception as err:
        LOGGER.warning('WMS 1.3.0 support not found: %s', err)
        LOGGER.debug('Trying a WMS 1.1.1 GetCapabilities request instead')
        return WebMapService(url, version='1.1.1', timeout=timeout)


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
    except KeyError, err:
        LOGGER.error(err, exc_info=True)

    return [extent, srs]


def flip_coordinates(c1, c2):
    if c1 > c2:
        LOGGER.debug('Flipping coordinates %s, %s' % (c1, c2))
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


def get_solr_date(pydate, is_negative):
    """
    Returns a date in a valid Solr format from a string.
    """
    # check if date is valid and then set it to solr format YYYY-MM-DDThh:mm:ssZ
    try:
        if isinstance(pydate, datetime.datetime):
            solr_date = '%sZ' % pydate.isoformat()[0:19]
            if is_negative:
                LOGGER.debug('%s This layer has a negative date' % solr_date)
                solr_date = '-%s' % solr_date
            return solr_date
        else:
            return None
    except Exception, e:
        LOGGER.error(e, exc_info=True)
        return None


def get_date(layer):
    """
    Returns a custom date representation. A date can be detected or from metadata.
    It can be a range or a simple date in isoformat.
    """
    date = None
    sign = '+'
    date_type = 1
    layer_dates = layer.get_layer_dates()
    # we index the first date!
    if layer_dates:
        sign = layer_dates[0][0]
        date = layer_dates[0][1]
        date_type = layer_dates[0][2]
    if date is None:
        date = layer.created
    # layer date > 2300 is invalid for sure
    # TODO put this logic in date miner
    if date.year > 2300:
        date = None
    if date_type == 0:
        date_type = "Detected"
    if date_type == 1:
        date_type = "From Metadata"
    return get_solr_date(date, (sign == '-')), date_type


def get_domain(url):
    urlParts = urlparse(url)
    hostname = urlParts.hostname
    if hostname == "localhost":
        return "Harvard"  # assumption
    return hostname


def layer2dict(layer):
    """
    Return a json representation for a layer.
    """

    category = None
    username = None

    # bbox must be valid before proceeding
    if not layer.has_valid_bbox():
        message = 'Layer id: %s has a not valid bbox' % layer.id
        return None, message

    # we can proceed safely
    bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
    minX = bbox[0]
    minY = bbox[1]
    maxX = bbox[2]
    maxY = bbox[3]
    # coords hack needed by solr
    if (minX < -180):
        minX = -180
    if (maxX > 180):
        maxX = 180
    if (minY < -90):
        minY = -90
    if (maxY > 90):
        maxY = 90
    rectangle = box(minX, minY, maxX, maxY)
    wkt = "ENVELOPE({:f},{:f},{:f},{:f})".format(minX, maxX, maxY, minY)
    halfWidth = (maxX - minX) / 2.0
    halfHeight = (maxY - minY) / 2.0
    area = (halfWidth * 2) * (halfHeight * 2)
    domain = get_domain(layer.service.url)
    if hasattr(layer, 'layerwm'):
        category = layer.layerwm.category
        username = layer.layerwm.username
    abstract = layer.abstract
    if abstract:
        abstract = strip_tags(layer.abstract)
    else:
        abstract = ''
    if layer.type == "WM":
        originator = username
    else:
        originator = domain

    layer_dict = {
                    'id': layer.id,
                    'uuid': str(layer.uuid),
                    'type': 'Layer',
                    'layer_id': layer.id,
                    'name': layer.name,
                    'title': layer.title,
                    'layer_originator': originator,
                    'service_id': layer.service.id,
                    'service_type': layer.service.type,
                    'layer_category': category,
                    'layer_username': username,
                    'url': layer.url,
                    'keywords': [kw.name for kw in layer.keywords.all()],
                    'reliability': layer.reliability,
                    'recent_reliability': layer.recent_reliability,
                    'last_status': layer.last_status,
                    'is_public': layer.is_public,
                    'is_valid': layer.is_valid,
                    'availability': 'Online',
                    'location': '{"layerInfoPage": "' + layer.get_absolute_url + '"}',
                    'abstract': abstract,
                    'domain_name': layer.service.get_domain
                    }

    solr_date, date_type = get_date(layer)
    if solr_date is not None:
        layer_dict['layer_date'] = solr_date
        layer_dict['layer_datetype'] = date_type
    if bbox is not None:
        layer_dict['min_x'] = minX
        layer_dict['min_y'] = minY
        layer_dict['max_x'] = maxX
        layer_dict['max_y'] = maxY
        layer_dict['area'] = area
        layer_dict['bbox'] = wkt
        layer_dict['centroid_x'] = rectangle.centroid.x
        layer_dict['centroid_y'] = rectangle.centroid.y
        srs_list = [srs.encode('utf-8') for srs in layer.service.srs.values_list('code', flat=True)]
        layer_dict['srs'] = srs_list
    if layer.get_tile_url():
        layer_dict['tile_url'] = layer.get_tile_url()

    message = 'Layer %s successfully converted to json' % layer.id
    return layer_dict, message


def detect_metadata_url_scheme(url):
    """detect whether a url is a Service type that HHypermap supports"""

    scheme = None
    url_lower = url.lower()

    if any(x in url_lower for x in ['wms', 'service=wms']):
        scheme = 'OGC:WMS'
    if any(x in url_lower for x in ['wmts', 'service=wmts']):
        scheme = 'OGC:WMTS'
    elif all(x in url for x in ['/MapServer', 'f=json']):
        scheme = 'ESRI:ArcGIS:MapServer'
    elif all(x in url for x in ['/ImageServer', 'f=json']):
        scheme = 'ESRI:ArcGIS:ImageServer'

    return scheme
