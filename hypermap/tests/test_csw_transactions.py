# -*- coding: utf-8 -*-
import os
import time
import unittest
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from hypermap.aggregator.elasticsearch_client import ESHypermap
from hypermap.aggregator.models import Catalog, Layer, Service
from hypermap.aggregator.solr import SolrHypermap
from hypermap.aggregator.tasks import index_cached_layers

BROWSER_HYPERMAP_URL = os.environ.get("BROWSER_HYPERMAP_URL",
                                      "http://localhost")
BROWSER_SEARCH_URL = "{0}/_elastic".format(BROWSER_HYPERMAP_URL)
SEARCH_TYPE = settings.REGISTRY_SEARCH_URL.split('+')[0]
SEARCH_URL = settings.REGISTRY_SEARCH_URL.split('+')[1]
SEARCH_TYPE_SOLR = 'solr'
SEARCH_TYPE_ES = 'elasticsearch'
catalog_test_slug = 'hypermap'


class TestCSWTransactions(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create(username='admin')
        user.set_password('admin')
        user.save()
        self.client.login(username="admin", password="admin")

        Catalog.objects.get_or_create(
            name=catalog_test_slug
        )

        Layer.objects.all().delete()
        Service.objects.all().delete()

        if SEARCH_TYPE == SEARCH_TYPE_SOLR:
            self.solr = SolrHypermap()
            self.solr.update_schema(catalog=catalog_test_slug)
            self.solr.clear_solr(catalog=catalog_test_slug)
        elif SEARCH_TYPE == SEARCH_TYPE_ES:
            es = ESHypermap()
            es.clear_es()
        else:
            raise Exception("SEARCH_TYPE not valid=%s" % SEARCH_TYPE)

    def test_post(self):
        """
        test CSV transactions.
        :return:
        """

        print ""
        print ">>> with env:"
        print "REGISTRY_SKIP_CELERY: %s" % settings.REGISTRY_SKIP_CELERY
        print "REGISTRY_LIMIT_LAYERS: %s" % settings.REGISTRY_LIMIT_LAYERS
        print "REGISTRY_CHECK_PERIOD: %s" % settings.REGISTRY_CHECK_PERIOD
        print "REGISTRY_SEARCH_URL: %s" % settings.REGISTRY_SEARCH_URL
        print "REGISTRY_HARVEST_SERVICES: %s" % settings.REGISTRY_HARVEST_SERVICES
        print ""

        # Post the 10 Layers contained in this file: data/cswt_insert.xml
        path = os.path.join(settings.PROJECT_DIR, "..",
                            "data", "cswt_insert.xml")
        payload = open(path, 'rb').read()
        content_type = "application/xml"

        url = "/registry/{0}/csw".format(catalog_test_slug)

        res = self.client.post(url, data=payload, content_type=content_type)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Layer.objects.all().count(), 10)

        # List the Layers posted above
        url = "/registry/{0}/csw?service=CSW&version=2.0.2&request=" \
              "GetRecords&typenames=csw:Record&elementsetname=full&" \
              "resulttype=results".format(catalog_test_slug)
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.count("Airports (OSM)"), 1)
        self.assertEqual(res.content.count("Manaus Roads (OSM May 2016)"), 2)

        # Search one Layer posted above
        url = "/registry/{0}/csw?mode=opensearch&service=CSW&version" \
              "=2.0.2&request=GetRecords&elementsetname=full&typenames=" \
              "csw:Record&resulttype=results" \
              "&q=Airport".format(catalog_test_slug)

        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.count("Airports (OSM)"), 1)

        # Flush layers in the cache.
        index_cached_layers()

        # Give celery some time.
        time.sleep(3)

        # are Layers in index?
        url = "{0}hypermap/_search".format(
             SEARCH_URL
        )
        res = requests.get(url)
        results_ok_in_search_backend = res.json()
        self.assertTrue("hits" in results_ok_in_search_backend)
        self.assertTrue("total" in results_ok_in_search_backend["hits"])
        self.assertEqual(results_ok_in_search_backend["hits"]["total"], 10)

    def tearDown(self):
        pass
