import pysolr
import requests
import logging
import math
import json
import re

from urlparse import urlparse
from dateutil.parser import parse
from django.conf import settings
from django.utils.html import strip_tags

from aggregator.utils import mercator_to_llbbox


class SolrHypermap(object):

    solr_url = settings.SOLR_URL
    solr = pysolr.Solr(solr_url, timeout=60)
    logger = logging.getLogger("hypermap.aggregator.solr")

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
    def layer_to_solr(layer, i=0):
        success = True
        category = None
        username = None
        try:
            bbox = [float(layer.bbox_x0), float(layer.bbox_y0), float(layer.bbox_x1), float(layer.bbox_y1)]
            for proj in layer.srs.values():
                if proj['code'] in ('102113', '102100'):
                    bbox = mercator_to_llbbox(bbox)
            if (SolrHypermap.good_coords(bbox)) is False:
                print 'no coords in layer ', layer.title
                return
            if (SolrHypermap.good_coords(bbox)):
                print 'in solr.layer_to_solr, bbox = ', bbox
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
                date = layer.get_date()[0]
                if 'TO' in layer.get_date()[0]:
                    date = re.findall('\d{4}', layer.get_date()[0])[0]
                    date = parse(str(date+'-01'+'-01'))
                SolrHypermap.solr.add([{
                                    "LayerId": str(layer.id),
                                    "LayerName": layer.name,
                                    "LayerTitle": layer.title,
                                    "Originator": originator,
                                    "ServiceType": layer.service.type,
                                    "LayerCategory": category,
                                    "LayerUsername": username,
                                    "LayerUrl": layer.url,
                                    "LayerReliability": layer.reliability,
                                    "LayerDate": date,
                                    "LayerDateRange": layer.get_date()[0],
                                    "LayerDateType": layer.get_date()[1],
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
                                    "bbox": wkt}])
                SolrHypermap.logger.info("Solr record saved for layer with id: %s" % layer.id)
                return True
        except Exception:
            success = False
            SolrHypermap.logger.error("Error svaing solr record for layer with id: %s" % layer.id)
            return False
        print 'Layer status into solr core %s ' % (success)

    @staticmethod
    def clear_solr():
        """Clear all indexes in the solr core"""
        SolrHypermap.solr.delete(q='*:*')
        print 'Solr core cleared'
