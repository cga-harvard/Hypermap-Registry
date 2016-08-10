import sys
import pysolr
import requests
import logging
import json
import datetime

from urlparse import urlparse
from django.conf import settings
from django.utils.html import strip_tags
from shapely.geometry import box

from hypermap.aggregator.utils import mercator_to_llbbox


def get_date(layer):
    """
    Returns a date for Solr. A date can be detected or from metadata.
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
        date = layer.created.date()
    # layer date > 2300 is invalid for sure
    # TODO put this logic in date miner
    if date.year > 2300:
        date = None
    if date_type == 0:
        date_type = "Detected"
    if date_type == 1:
        date_type = "From Metadata"
    return get_solr_date(date, (sign == '-')), date_type


def get_solr_date(pydate, is_negative):
    """
    Returns a date in a valid Solr format from a string.
    """
    # check if date is valid and then set it to solr format YYYY-MM-DDThh:mm:ssZ
    try:
        if isinstance(pydate, datetime.datetime):
            solr_date = '%sZ' % pydate.isoformat()[0:19]
            if is_negative:
                print '***** This layer has a negative date'
                solr_date = '-%s' % solr_date
            return solr_date
        else:
            return None
    except Exception:
        return None


class SolrHypermap(object):

    def get_domain(self, url):
        urlParts = urlparse(url)
        hostname = urlParts.hostname
        if hostname == "localhost":
            return "Harvard"  # assumption
        return hostname

    def layer_to_solr(self, layer):
        logger = logging.getLogger("hypermap")
        category = None
        username = None
        try:
            bbox = None
            if not layer.has_valid_bbox():
                message = 'There are not valid coordinates for layer id: %s' % layer.id
                logger.error(message)
            else:
                bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
                for proj in layer.service.srs.values():
                    if proj['code'] in ('102113', '102100'):
                        bbox = mercator_to_llbbox(bbox)
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
                wkt = "ENVELOPE({:f},{:f},{:f},{:f})".format(minX, maxX, maxY, minY)
                halfWidth = (maxX - minX) / 2.0
                halfHeight = (maxY - minY) / 2.0
                area = (halfWidth * 2) * (halfHeight * 2)
                rectangle = box(minX, minY, maxX, maxY)
            domain = self.get_domain(layer.service.url)
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
            # now we add the index
            solr_record = {
                           'id': layer.id,
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
                           'reliability': layer.reliability,
                           'recent_reliability': layer.recent_reliability,
                           'last_status': layer.last_status,
                           'is_public': layer.is_public,
                           'availability': 'Online',
                           'location': '{"layerInfoPage": "' + layer.get_absolute_url + '"}',
                           'abstract': abstract,
                           'domain_name': layer.service.get_domain
                           }

            solr_date, date_type = get_date(layer)
            if solr_date is not None:
                solr_record['layer_date'] = solr_date
                solr_record['layer_datetype'] = date_type
            if bbox is not None:
                solr_record['min_x'] = minX
                solr_record['min_y'] = minY
                solr_record['max_x'] = maxX
                solr_record['max_y'] = maxY
                solr_record['area'] = area
                solr_record['bbox'] = wkt
                solr_record['centroid_x'] = rectangle.centroid.x
                solr_record['centroid_y'] = rectangle.centroid.y

                srs_list = [srs.encode('utf-8') for srs in layer.service.srs.values_list('code', flat=True)]
                # solr_record['srs'] = ', '.join(srs_list)
                solr_record['srs'] = srs_list
            if layer.get_tile_url():
                solr_record['tile_url'] = layer.get_tile_url()

            # time to send request to solr
            url_solr_update = '%s/update/json/docs' % settings.SEARCH_URL
            headers = {"content-type": "application/json"}
            params = {"commitWithin": 1500}
            solr_json = json.dumps(solr_record)
            requests.post(url_solr_update, data=solr_json, params=params,  headers=headers)
            logger.info("Solr record saved for layer with id: %s" % layer.id)
            return True, None
        except Exception:
            logger.error("Error saving solr record for layer with id: %s - %s" % (layer.id, sys.exc_info()[1]))
            return False, sys.exc_info()[1]

    def clear_solr(self):
        """Clear all indexes in the solr core"""
        solr_url = settings.SEARCH_URL
        solr = pysolr.Solr(solr_url, timeout=60)
        solr.delete(q='*:*')
        print 'Solr core cleared'
