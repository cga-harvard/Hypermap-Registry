import sys
import logging
import math
import json

from urlparse import urlparse
from django.conf import settings
from django.utils.html import strip_tags

from elasticsearch import Elasticsearch
from shapely.geometry import box

from hypermap.aggregator.utils import mercator_to_llbbox, get_date

REGISTRY_MAPPING_PRECISION = getattr(settings, "REGISTRY_MAPPING_PRECISION", "500m")
REGISTRY_SEARCH_URL = getattr(settings, "REGISTRY_SEARCH_URL", "elasticsearch+http://localhost:9200")

SEARCH_TYPE = REGISTRY_SEARCH_URL.split('+')[0]
SEARCH_URL = REGISTRY_SEARCH_URL.split('+')[1]

LOGGER = logging.getLogger(__name__)


class ESHypermap(object):

    es_url = SEARCH_URL
    es = Elasticsearch(hosts=[es_url])
    index_name = 'hypermap'

    def __init__(self):
        # TODO: this create_indices() should not happen here:
        # ES creates the indexes automaticaly.
        super(ESHypermap, self).__init__()

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
    def get_bbox(layer):
        candidate_bbox = layer.bbox_x0, layer.bbox_y0, layer.bbox_x1, layer.bbox_y1
        if None not in candidate_bbox:
            return [float(coord) for coord in candidate_bbox]

        wkt = layer.wkt_geometry
        # If a coordinate is None and 'POLYGON'
        if 'POLYGON' in wkt:
            from shapely.wkt import loads
            return loads(wkt).bounds

        return (-180.0, -90.0, 180.0, 90.0)

    @staticmethod
    def layer_to_es(layer, with_bulk=False):
        category = None
        username = None
        LOGGER.info("Elasticsearch: record to save: [%s] %s" % (layer.catalog.slug, layer.id))

        try:
            bbox = ESHypermap.get_bbox(layer)
            for proj in layer.service.srs.values():
                if proj['code'] in ('102113', '102100'):
                    bbox = mercator_to_llbbox(bbox)
            if (ESHypermap.good_coords(bbox)) is False:
                LOGGER.debug('Elasticsearch: There are not valid coordinates for this layer ', layer.title)
                LOGGER.error('Elasticsearch: There are not valid coordinates for layer id: %s' % layer.id)
                return False
            if (ESHypermap.good_coords(bbox)):
                minX = bbox[0]
                minY = bbox[1]
                maxX = bbox[2]
                maxY = bbox[3]
                if (minY > maxY):
                    minY, maxY = maxY, minY
                if (minX > maxX):
                    minX, maxX = maxX, minX
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
                rectangle = box(minX, minY, maxX, maxY)
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
                # ESHypermap.es.delete('hypermap', 'layer', layer.id)
                # now we add the index
                es_record = {
                    "id": str(layer.id),
                    "type": 'Layer',
                    "layer_id": str(layer.id),
                    "name": layer.name,
                    "title": layer.title,
                    "layer_originator": originator,
                    "service_id": str(layer.service.id),
                    "service_type": layer.service.type,
                    "layer_category": category,
                    "layer_username": username,
                    "url": layer.url,
                    "reliability": layer.reliability,
                    "recent_reliability": layer.recent_reliability,
                    "last_status": layer.last_status,
                    "is_public": layer.is_public,
                    "availability": "Online",
                    "location": '{"layer_info": "' + layer.get_absolute_url + '"}',
                    "abstract": abstract,
                    "domain_name": layer.service.get_domain,
                    # "SrsProjectionCode": layer.srs.values_list('code', flat=True),
                    "min_y": minY,
                    "min_x": minX,
                    "max_x": maxX,
                    "max_y": maxY,
                    "area": area,
                    "bbox": wkt,
                    "centroid_x": rectangle.centroid.x,
                    "centroid_y": rectangle.centroid.y,
                    "srs": [srs.encode('utf-8') for srs in layer.service.srs.values_list('code', flat=True)],
                    "layer_geoshape": {
                       "type": "envelope",
                    "coordinates": [
                           [minX, maxY], [maxX, minY]
                       ]
                    },
                }

                es_date, type = get_date(layer)
                if es_date is not None:
                    es_record['layer_date'] = es_date
                    es_record['layer_datetype'] = type

                es_record['registry'] = layer.registry_tags()

                if layer.get_tile_url():
                    es_record['tile_url'] = layer.get_tile_url()

                if with_bulk:
                    es_record = {
                        "_id": str(layer.id),
                        "_type": "layer",
                        "_index": layer.catalog.slug,
                        "_source": es_record,
                    }

                LOGGER.info(es_record)
                # TODO: cache index creation.
                ESHypermap.create_indices(layer.catalog.slug)
                if not with_bulk:
                    ESHypermap.es.index(layer.catalog.slug, 'layer', json.dumps(es_record), id=layer.id,
                                        request_timeout=20)
                    LOGGER.info("Elasticsearch: record saved for layer with id: %s" % layer.id)
                    return True, None

                # If we want to index with bulk we need to return the layer dictionary.
                return es_record

        except Exception, e:
            LOGGER.error(e, exc_info=True)
            LOGGER.error("Elasticsearch: Error saving record for layer with id: %s - %s" % (
                         layer.id, sys.exc_info()[1]))
            return False, sys.exc_info()[1]

    @staticmethod
    def clear_es():
        """Clear all indexes in the es core"""
        # TODO: should receive a catalog slug.
        ESHypermap.es.indices.delete(ESHypermap.index_name, ignore=[400, 404])
        LOGGER.debug('Elasticsearch: Index cleared')

    @staticmethod
    def create_indices(catalog_slug):
        """Create ES core indices """
        # TODO: enable auto_create_index in the ES nodes to make this implicit.
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-index_.html#index-creation
        # http://support.searchly.com/customer/en/portal/questions/
        # 16312889-is-automatic-index-creation-disabled-?new=16312889
        mapping = {
            "mappings": {
                "layer": {
                    "properties": {
                        "layer_geoshape": {
                           "type": "geo_shape",
                           "tree": "quadtree",
                           "precision": REGISTRY_MAPPING_PRECISION
                        }
                    }
                }
            }
        }
        ESHypermap.es.indices.create(catalog_slug, ignore=[400, 404], body=mapping)
