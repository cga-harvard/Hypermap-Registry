# -*- coding: utf-8 -*-
import os
import unittest

import requests
import time
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from hypermap.aggregator.elasticsearch_client import ESHypermap
from hypermap.aggregator.models import Catalog, Layer, Service
from hypermap.aggregator.solr import SolrHypermap

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

        print '> clearing SEARCH_URL={0}'.format(SEARCH_URL)
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

        # Post the 10 Layers contained in this file: data/cswt_insert.xml
        path = os.path.join(settings.PROJECT_DIR, "..",
                            "data", "cswt_insert.xml")
        payload = open(path, 'rb').read()
        content_type = "application/xml"

        url = "/registry/{0}/csw/?service=CSW&request=Transaction".format(
            catalog_test_slug
        )

        res = self.client.post(url, data=payload, content_type=content_type)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Layer.objects.all().count(), 10)

        # List the Layers posted above
        url = "/registry/{0}/csw/?service=CSW&version=2.0.2&request=" \
              "GetRecords&typenames=csw:Record&elementsetname=full&" \
              "resulttype=results".format(catalog_test_slug)
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.count("Airports (OSM)"), 1)
        self.assertEqual(res.content.count("Manaus Roads (OSM May 2016)"), 2)

        # Search one Layer posted above
        url = "/registry/{0}/csw/?mode=opensearch&service=CSW&version" \
              "=2.0.2&request=GetRecords&elementsetname=full&typenames=" \
              "csw:Record&resulttype=results" \
              "&q=Airport".format(catalog_test_slug)

        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.count("Airports (OSM)"), 1)

        # are Layers in index?
        time.sleep(3)
        url = "{0}hypermap/_search".format(
            SEARCH_URL
        )
        res = requests.get(url)
        results = res.json()

        self.assertTrue("hits" in results)
        self.assertTrue("total" in results["hits"])
        self.assertEqual(results["hits"]["total"], 10)

    def tearDown(self):
        pass
