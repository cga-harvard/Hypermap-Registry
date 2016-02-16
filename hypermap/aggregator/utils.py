import pysolr
import requests
import urllib2
import re
import logging
import time
import math
import json
import sys
import traceback
from datetime import datetime

from django.conf import settings
from urlparse import urlparse

from owslib.wms import WebMapService
from owslib.tms import TileMapService
from owslib.wmts import WebMapTileService
from arcrest import Folder as ArcFolder

from models import Service, Layer


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


class OGP_utils(object):

    @staticmethod
    def good_coords(coords):
        """ passed a string array """
        if (len(coords) != 4):
            return False
        for coord in coords[0:3]:
            try:
                num = float(coord)
                if (math.isnan(num)):
                    return False
                if (math.isinf(num)):
                    return False
            except ValueError:
                return False
        return True

    solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:8983/solr/geonode24')
    solr = pysolr.Solr(solr_url, timeout=60)
    logger = logging.getLogger("hypermap.aggregator.utils")

    @staticmethod
    def get_domain(url):
        urlParts = urlparse(url)
        hostname = urlParts.hostname
        if hostname == "localhost":
            return "Harvard"  # assumption
        return hostname

    @staticmethod
    def extract_date(layer):
        year = re.search('\d{4}', layer.title)
        if year is None:
            year = re.search('\d{4}', layer.abstract)
        if year is not None:
            year = year.group(0).strip()
            year = year.strip()
            year = int(year)
            if (year < 1000 or year > datetime.now().year):
                year = None
            else:
                year = datetime(year=year, month=1, day=1)
        return year

    @staticmethod
    def is_solr_up():
        solr_url = getattr(settings, 'SOLR_URL', 'http://localhost:8983/solr/geonode24')
        solr_url_parts = solr_url.split('/')
        admin_url = '/'.join(solr_url_parts[:-1]) + '/admin/cores'
        params = {'action': 'STATUS', 'wt': 'json'}
        try:
            req = requests.get(admin_url, params=params)
            response = json.loads(req.text)
            status = response['status']
            if status:
                response = True
        except requests.exceptions.RequestException:
            response = False
        return response

    @staticmethod
    def layer_to_solr(layer, i=0):
        try:
            bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
            for proj in layer.srs.values():
                if '102113' == proj['code']:
                    bbox = mercator_to_llbbox(bbox)
            storeType = "remoteStore"  # to do need to figure out it hypermap will only be dealing with remote servives
            date = layer.created
            if (OGP_utils.good_coords(bbox)) is False:
                print 'no coords in layer ', layer.title
                return
            if (OGP_utils.good_coords(bbox)):
                print 'in utils.layer_to_solr, bbox = ', bbox
                username = ""
                minX = bbox[0]
                minY = bbox[1]
                maxX = bbox[2]
                maxY = bbox[3]
                if (minY > maxY):
                    tmp = minY
                    minY = maxY
                    maxY = tmp
                if (minX > maxX):
                    tmp = minX
                    minX = maxX
                    maxX = tmp
                centerY = (maxY + minY) / 2.0
                centerX = (maxX + minX) / 2.0
                halfWidth = (maxX - minX) / 2.0
                halfHeight = (maxY - minY) / 2.0
                area = (halfWidth * 2) * (halfHeight * 2)
                if (minX < -180):
                    minX = -180
                if (maxX > 180):
                    maxX = 180
                if (minY < -90):
                    minY = -90
                if (maxY > 90):
                    maxY = 90
                # ENVELOPE(minX, maxX, maxY, minY) per https://github.com/spatial4j/spatial4j/issues/36
                wkt = "ENVELOPE({:f},{:f},{:f},{:f})".format(minX, maxX, maxY, minY)
                # default for now as we do not have capabilitty to resolve vector/raster layers
                dataType = "Polygon"
                institution = "Harvard"
                servicetype = layer.service.type
                owsUrl = layer.service.url
                if storeType == "remoteStore":
                    institution = "Remote"
                    if servicetype == "ESRI":
                        dataType = "RESTServices"
                    else:
                        dataType = "WMSServices"
                domain = OGP_utils.get_domain(owsUrl)
                if (i == 0):
                    i = layer.title
                # we will need to resolve the projection issue at a later date
                OGP_utils.solr.add([{
                                    "LayerId": "HyperMapLayer_" + str(i),
                                    "Name": layer.title,
                                    "LayerDisplayName": layer.title,
                                    "Institution": institution,
                                    "Publisher": username,
                                    "Originator": domain,
                                    "ServiceType": servicetype,
                                    "ContentDate": date,
                                    "Access": "Public",
                                    "DataType": dataType,
                                    "Availability": "Online",
                                    "Location": '{"layerInfoPage": "' + layer.get_absolute_url() + '"}',
                                    "Abstract": "abstract",
                                    "SrsProjectionCode": 'EPSG:4326',
                                    "MinY": minY,
                                    "MinX": minX,
                                    "MaxY": maxY,
                                    "MaxX": maxX,
                                    "CenterY": centerY,
                                    "CenterX": centerX,
                                    "HalfWidth": halfWidth,
                                    "HalfHeight": halfHeight,
                                    "Area": area,
                                    "bbox_rpt": wkt}])
                OGP_utils.logger.error("solr record saved: " + layer.title)
        except Exception as e:
            if e.message.startswith("Connection") or e.message.startswith("[Reason: java.lang.OutOfMemoryError:"):
                OGP_utils.solr.add([{
                                     "LayerId": "HarvardWorldMapLayer_" + str(i),
                                     "Name": layer.title,
                                     "LayerDisplayName": layer.title,
                                     "Institution": institution,
                                     "Publisher": username,
                                     "Originator": domain,
                                     "ServiceType": servicetype,
                                     "ContentDate": date,
                                     "Access": "Public",
                                     "DataType": dataType,
                                     "Availability": "Online",
                                     "Location": '{"layerInfoPage": "' + layer.get_absolute_url() + '"}',
                                     "Abstract": "abstract",
                                     "SrsProjectionCode": 'EPSG:4326',
                                     "MinY": minY,
                                     "MinX": minX,
                                     "MaxY": maxY,
                                     "MaxX": maxX,
                                     "CenterY": centerY,
                                     "CenterX": centerX,
                                     "HalfWidth": halfWidth,
                                     "HalfHeight": halfHeight,
                                     "Area": area,
                                 }])
                OGP_utils.logger.error("failed solr record saved after retry: " + layer.title)
            else:
                OGP_utils.logger.error("error in layer_to_solr processing layer: " + e.message)

    @staticmethod
    def geonode_to_solr():
        """create Solr records of layer objects in sql database"""
        layers = Layer.objects.all()
        print "original number of layers = ", len(layers)
        # layers = [layers[0]]  # just the first
        i = 1
        for layer in layers:
            OGP_utils.layer_to_solr(layer, i)
            i = i+1
            time.sleep(.1)

        OGP_utils.solr.optimize()
        print 'hypermap layers processed ', i-1

    @staticmethod
    def solr_to_solr():
        """create Solr records for layers in another Solr OGP instance"""
        ogp_solr = pysolr.Solr('http://geodata.tufts.edu/solr/')
        wm_solr = pysolr.Solr('http://localhost:8983/solr/all', timeout=60)
        count = 3200
        while (True):
            docs = ogp_solr.search("*:*", start=count)
            count += len(docs)
            if (len(docs) == 0):
                return
            time.sleep(1)
            print "count = ", count
            for doc in docs:
                minX = doc['MinX']
                minY = doc['MinY']
                maxX = doc['MaxX']
                maxY = doc['MaxY']
                wkt = "ENVELOPE({:f},{:f},{:f},{:f})".format(minX, maxX, maxY, minY)
                if (-90 <= minY <= 90 and -90 <= maxY <= 90 and -180 <= minX <= 180 and -180 <= maxX <= 180):
                    try:
                        wm_solr.add([{
                            "LayerId": doc['LayerId'],
                            "Name": doc['Name'],
                            "LayerDisplayName": doc['LayerDisplayName'],
                            "Institution": "OGP-" + doc['Institution'],  # "Harvard",
                            "Publisher": doc['Publisher'],
                            "Originator": doc['Originator'],
                            "Access": 'Public',
                            "DataType": doc['DataType'],
                            "ContentDate": doc['ContentDate'],
                            "Availability": doc['Availability'],
                            "Location": doc['Location'],
                            "Abstract": doc['Abstract'],
                            "MinY": doc['MinY'],
                            "MinX": doc['MinX'],
                            "MaxY": doc['MaxY'],
                            "MaxX": doc['MaxX'],
                            "CenterY": doc['CenterY'],
                            "CenterX": doc['CenterX'],
                            "HalfWidth": doc['HalfWidth'],
                            "HalfHeight": doc['HalfHeight'],
                            "Area": doc['Area'],
                            "bbox_rpt": wkt}])
                    except KeyError as e:
                        print doc['LayerDisplayName', e]
                else:
                    print "bad bounds: ", doc
