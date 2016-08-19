import sys
import pysolr
import requests
import logging
import json

from django.conf import settings

from hypermap.aggregator.utils import layer2dict


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
            requests.post(url_solr_update, data=layer_json, params=params,  headers=headers)
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
