import sys
import pysolr
import requests
import logging
import math
import json
import re
import datetime

from urlparse import urlparse
from dateutil.parser import parse
from django.conf import settings
from django.utils.html import strip_tags

from aggregator.utils import mercator_to_llbbox


def get_date(layer):
    """
    Returns a date for Solr. A date can be detected or from metadata.
    It can be a range or a simple date in isoformat.
    """
    date = None
    type = 1
    # for WM layer we may have a range
    if hasattr(layer, 'layerwm'):
        if layer.layerwm.temporal_extent_start and layer.layerwm.temporal_extent_end:
            date = "[%s TO %s]" % (layer.layerwm.temporal_extent_start, layer.layerwm.temporal_extent_end)
        if layer.layerwm.temporal_extent_end and not layer.layerwm.temporal_extent_start:
            date = layer.layerwm.temporal_extent_end
        if layer.layerwm.temporal_extent_start and not layer.layerwm.temporal_extent_end:
            date = layer.layerwm.temporal_extent_start
    if layer.layerdate_set.values_list() and date is None:
        date_text = layer.layerdate_set.values_list('date', flat=True)
        for text in date_text:
            if 'TO' in text:
                date = "[%s]" % text
                type = layer.layerdate_set.get(date=text).type
        # will resolve this later by adding them to list to get the min(dates) while removing any TO's
        if date is None:
            date = layer.layerdate_set.values_list('date', flat=True)[0]
            type = layer.layerdate_set.values_list('type', flat=True)[0]
    if date is None:
        date = layer.created.date().isoformat()
    if 'TO' not in date:
        dates_info = date.split('-')
        if len(dates_info) != 3:
            if len(dates_info) == 2:
                date = parse(str(date+'-01')).isoformat()
            else:
                date = parse(str(date+'-01'+'-01')).isoformat()
    if type == 0:
        type = "Detected"
    if type == 1:
        type = "From Metadata"
    return date, type


def get_solr_date(date):
    """
    Returns a date in a valid Solr format from a string.
    """
    # check if date is valid and then set it to solr format YYYY-MM-DDThh:mm:ssZ
    try:
        pydate = parse(date, yearfirst=True)
        if isinstance(pydate, datetime.datetime):
            solr_date = '%sZ' % pydate.isoformat()[0:19]
            return solr_date
        else:
            return None
    except Exception:
        return None


class SolrHypermap(object):

    solr_url = settings.SOLR_URL
    solr = pysolr.Solr(solr_url, timeout=60)
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
    def is_solr_up():
        solr_url = settings.SOLR_URL
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
    def layer_to_solr(layer):
        category = None
        username = None
        try:
            bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
            for proj in layer.srs.values():
                if proj['code'] in ('102113', '102100'):
                    bbox = mercator_to_llbbox(bbox)
            if (SolrHypermap.good_coords(bbox)) is False:
                print 'There are not valid coordinates for this layer ', layer.title
                SolrHypermap.logger.error('There are not valid coordinates for layer id: %s' % layer.id)
                return False
            if (SolrHypermap.good_coords(bbox)):
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
                domain = SolrHypermap.get_domain(layer.service.url)
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
                date = get_date(layer)[0]
                check_range = None
                if 'TO' in get_date(layer)[0]:
                    check_range = 1 
                    date = re.findall('[+-]?\d{4}', get_date(layer)[0])[0]
                    date = str(date+'-01'+'-01')

                solr_record = {
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
                                "LayerDateRange": get_date(layer)[0],
                                "LayerDateType": get_date(layer)[1],
                                "Is_Public": layer.is_public,
                                "Availability": "Online",
                                "Location": '{"layerInfoPage": "' + layer.get_absolute_url() + '"}',
                                "Abstract": abstract,
                                "SrsProjectionCode": layer.srs.values_list('code', flat=True),
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
                # LayerDate sometime is missing
                if check_range:
                    solr_date = date
                else:
                    solr_date = get_solr_date(date)
                if solr_date is not None:
                    solr_record['LayerDate'] = solr_date
                SolrHypermap.solr.add([solr_record])
                SolrHypermap.logger.info("Solr record saved for layer with id: %s" % layer.id)
                return True
        except Exception:
            SolrHypermap.logger.error("Error saving solr record for layer with id: %s - %s"
                                      % (layer.id, sys.exc_info()[1]))
            return False

    @staticmethod
    def clear_solr():
        """Clear all indexes in the solr core"""
        SolrHypermap.solr.delete(q='*:*')
        print 'Solr core cleared'
