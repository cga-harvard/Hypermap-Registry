import sys
import pysolr
import requests
import logging
import json

from django.conf import settings
from django.utils.html import strip_tags


from hypermap.aggregator.utils import layer2dict

SEARCH_URL = settings.REGISTRY_SEARCH_URL.split('+')[1]


logger = logging.getLogger("hypermap")


class SolrHypermap(object):

    def layers_to_solr(self, layers):
        """
        Sync n layers in Solr.
        """
        layers_list = []
        for layer in layers:
            layer_dict = layer2dict(layer)
            layers_list.append(layer_dict)
        layers_json = json.dumps(layers_list)
        try:
            url_solr_update = '%s/update/json/docs' % settings.SEARCH_URL
            headers = {"content-type": "application/json"}
            params = {"commitWithin": 1500}
            requests.post(url_solr_update, data=layers_json, params=params,  headers=headers)
            logger.info("Solr synced for the given layers.")
            return True, None
        except Exception:
            logger.error("Error saving solr records - %s" % sys.exc_info()[1])
            return False, sys.exc_info()[1]

    def layer_to_solr(self, layer):
        """
        Sync a layer in Solr.
        """
        layer_dict = layer2dict(layer)
        layer_json = json.dumps(layer_dict)
        try:
            url_solr_update = '%s/update/json/docs' % settings.SEARCH_URL
            headers = {"content-type": "application/json"}
            params = {"commitWithin": 1500}
            res = requests.post(url_solr_update, data=layer_json, params=params,  headers=headers)
            res = res.json()
            if 'error' in res:
                message = res["error"].get("msg")
                print "ERROR: {0}".format(message)
                return False, message
            else:
                logger.info("Solr record saved for layer with id: %s" % layer.id)

            return True, None
        except Exception:
            logger.error("Error saving solr record for layer with id: %s - %s" % (layer.id, sys.exc_info()[1]))
            return False, sys.exc_info()[1]

    def clear_solr(self, catalog="hypermap"):
        """Clear all indexes in the solr core"""
        solr_url = "{0}/solr/{1}".format(SEARCH_URL, catalog)
        solr = pysolr.Solr(solr_url, timeout=60)
        solr.delete(q='*:*')
        print 'Solr core cleared'

    def update_schema(self, catalog="hypermap"):
        """
        set the mapping in solr.
        :param catalog: core
        :return:
        """
        schema_url = "{0}/solr/{1}/schema".format(SEARCH_URL, catalog)

        fields = [
            {"name": "abstract", "type": "string"},
            {"name": "area", "type": "tdouble"},
            {"name": "availability", "type": "string"},
            {"name": "bbox", "type": "location_rpt"},
            {"name": "domain_name", "type": "string"},
            {"name": "id", "type": "tlong", "required": True},
            {"name": "is_public", "type": "boolean"},
            {"name": "last_status", "type": "boolean"},
            {"name": "layer_date", "type": "tdate", "docValues": True},
            {"name": "layer_datetype", "type": "string"},
            {"name": "layer_id", "type": "tlong"},
            {"name": "layer_originator", "type": "string"},
            {"name": "location", "type": "string"},
            {"name": "max_x", "type": "tdouble"},
            {"name": "max_y", "type": "tdouble"},
            {"name": "min_x", "type": "tdouble"},
            {"name": "min_y", "type": "tdouble"},
            {"name": "name", "type": "string"},
            {"name": "recent_reliability", "type": "tdouble"},
            {"name": "reliability", "type": "tdouble"},
            {"name": "service_id", "type": "tlong"},
            {"name": "service_type", "type": "string"},
            {"name": "srs", "type": "string", "multiValued": True},
            {"name": "tile_url", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "type", "type": "string"},
            {"name": "url", "type": "string"},
            {"name": "layer_username", "type": "string"},
            {"name": "layer_category", "type": "string"},
            {"name": "centroid_y", "type": "tdouble"},
            {"name": "centroid_x", "type": "tdouble"},
        ]

        headers = {
            "Content-type": "application/json"
        }

        for field in fields:
            data = {
                "add-field": field
            }
            requests.post(schema_url, json=data, headers=headers)
