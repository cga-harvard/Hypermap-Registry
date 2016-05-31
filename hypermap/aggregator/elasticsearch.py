import sys
import pyelasticsearch
import requests
import logging
import math
import json
import datetime

from urlparse import urlparse
from django.conf import settings
from django.utils.html import strip_tags

from hypermap.aggregator.utils import mercator_to_llbbox

from hypermap.aggregator.solr import get_date

class ESHypermap(object):

    es_url = settings.SEARCH_URL
    es = pyelasticsearch.ElasticSearch(es_url)
    logger = logging.getLogger("hypermap")

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

    @staticmethod
    def get_domain(url):
        urlParts = urlparse(url)
        hostname = urlParts.hostname
        if hostname == "localhost":
            return "Harvard"  # assumption
        return hostname

    @staticmethod
    def layer_to_es(layer):
        category = None
        username = None
        try:
            bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
            for proj in layer.srs.values():
                if proj['code'] in ('102113', '102100'):
                    bbox = mercator_to_llbbox(bbox)
            if (ESHypermap.good_coords(bbox)) is False:
                print 'There are not valid coordinates for this layer ', layer.title
                ESHypermap.logger.error('There are not valid coordinates for layer id: %s' % layer.id)
                return False
            if (ESHypermap.good_coords(bbox)):
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
                wkt = "ENVELOPE({:f},{:f},{:f},{:f})".format(minX, maxX, maxY, minY)
                domain = ESHypermap.get_domain(layer.service.url)
                if hasattr(layer, 'layerwm'):
                    category = layer.layerwm.category
                    username = layer.layerwm.username
                abstract = layer.abstract
                if abstract:
                    abstract = strip_tags(layer.abstract)
                else:
                    abstract = ''
                if layer.service.type == "WM":
                    originator = username
                else:
                    originator = domain
                # we need to remove the exising index in case there is already one
                #ESHypermap.es.delete('hypermap', 'layer', layer.id)
                # now we add the index
                es_record = {
                                "LayerId": str(layer.id),
                                "LayerName": layer.name,
                                "LayerTitle": layer.title,
                                "Originator": originator,
                                "ServiceId": str(layer.service.id),
                                "ServiceType": layer.service.type,
                                "LayerCategory": category,
                                "LayerUsername": username,
                                "LayerUrl": layer.url,
                                "LayerReliability": layer.reliability,
                                "Is_Public": layer.is_public,
                                "Availability": "Online",
                                "Location": '{"layerInfoPage": "' + layer.get_absolute_url() + '"}',
                                "Abstract": abstract,
                                #"SrsProjectionCode": layer.srs.values_list('code', flat=True),
                                "MinY": minY,
                                "MinX": minX,
                                "MaxY": maxY,
                                "MaxX": maxX,
                                "CenterY": centerY,
                                "CenterX": centerX,
                                "HalfWidth": halfWidth,
                                "HalfHeight": halfHeight,
                                "Area": area,
                                "bbox": wkt,
                                "DomainName": layer.service.get_domain,
                                }

                es_date, type = get_date(layer)
                if es_date is not None:
                    es_record['LayerDate'] = es_date
                    es_record['LayerDateType'] = type
                ESHypermap.logger.info(es_record)
                ESHypermap.es.index('hypermap', 'layer', json.dumps(es_record), id=layer.id)
                ESHypermap.logger.info("Elasticsearch record saved for layer with id: %s" % layer.id)
                return True, None
        except Exception:
            ESHypermap.logger.error(sys.exc_info())
            ESHypermap.logger.error("Error saving elasticsearch record for layer with id: %s - %s"
                                      % (layer.id, sys.exc_info()[1]))
            return False, sys.exc_info()[1]

    @staticmethod
    def clear_es():
        """Clear all indexes in the es core"""
        ESHypermap.es.delete_index('hypermap')
        print 'ES Index cleared'
