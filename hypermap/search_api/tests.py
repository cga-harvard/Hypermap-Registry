import json
import datetime
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import signals
from django.test import TestCase

from hypermap.aggregator.models import Catalog, layer_post_save, service_post_save, Layer, Service
from hypermap.search_api import utils
from hypermap.aggregator.elasticsearch_client import ESHypermap
from hypermap.aggregator.solr import SolrHypermap


SEARCH_TYPE = settings.REGISTRY_SEARCH_URL.split('+')[0]
SEARCH_URL = settings.REGISTRY_SEARCH_URL.split('+')[1]
SEARCH_TYPE_SOLR = 'solr'
SEARCH_TYPE_ES = 'elasticsearch'


class SearchApiTestCase(TestCase):
    """
    run me
    python manage.py test hypermap.search_api --settings=hypermap.settings.test --failfast
    """

    def tearDown(self):
        signals.post_save.connect(layer_post_save, sender=Layer)
        signals.post_save.connect(service_post_save, sender=Service)

    def setUp(self):
        signals.post_save.disconnect(layer_post_save, sender=Layer)
        signals.post_save.disconnect(service_post_save, sender=Service)

        catalog_test_slug = "hypermap"

        if SEARCH_TYPE == SEARCH_TYPE_SOLR:
            self.solr = SolrHypermap()
            # delete solr documents
            # add the schema
            print '> updating schema'.format(SEARCH_URL)
            self.solr.update_schema(catalog=catalog_test_slug)
            print '> clearing SEARCH_URL={0}'.format(SEARCH_URL)
            self.solr.clear_solr(catalog=catalog_test_slug)

            self.search_engine_endpoint = '{0}/solr/{1}/select'.format(
                SEARCH_URL, catalog_test_slug
            )
        elif SEARCH_TYPE == SEARCH_TYPE_ES:
            es = ESHypermap()
            # delete ES documents
            es.clear_es()
            self.search_engine_endpoint = '{0}/{1}/_search'.format(
                SEARCH_URL, catalog_test_slug
            )
        else:
            raise Exception("SEARCH_TYPE not valid=%s" % SEARCH_TYPE)

        catalog, created = Catalog.objects.get_or_create(
            name=catalog_test_slug
        )

        service = Service(
            url='http://fakeurl.com',
            title='Title',
            type='OGC:WMS',
            catalog=catalog
        )
        service.save()

        layer = Layer(
            name='Layer 1',
            bbox_x0=-40.0,
            bbox_x1=-20.0,
            bbox_y0=-40.0,
            bbox_y1=-20.0,
            service=service,
            catalog=catalog
        )
        layer.title = layer.name
        layer.save()
        layer.created = datetime.datetime(2000, 3, 1, 0, 0, 0)
        layer.save()
        service.layer_set.add(layer)

        layer = Layer(
            name='Layer 2',
            bbox_x0=-40.0,
            bbox_x1=-20.0,
            bbox_y0=20.0,
            bbox_y1=40.0,
            service=service,
            catalog=catalog
        )
        layer.title = layer.name
        layer.save()
        layer.created = datetime.datetime(2001, 3, 1, 0, 0, 0)
        layer.save()
        service.layer_set.add(layer)

        layer = Layer(
            name='Layer 3',
            bbox_x0=20.0,
            bbox_x1=40.0,
            bbox_y0=20.0,
            bbox_y1=40.0,
            service=service,
            catalog=catalog
        )
        layer.title = layer.name
        layer.save()
        layer.created = datetime.datetime(2002, 3, 1, 0, 0, 0)
        layer.save()
        service.layer_set.add(layer)

        layer = Layer(
            name='Layer 4',
            bbox_x0=20.0,
            bbox_x1=40.0,
            bbox_y0=-40.0,
            bbox_y1=-20.0,
            service=service,
            catalog=catalog
        )
        layer.title = layer.name
        layer.save()
        layer.created = datetime.datetime(2003, 3, 1, 0, 0, 0)
        layer.save()
        service.layer_set.add(layer)

        # solr have commitWithin 1500.
        # before to proceed with the tests wait for 2 secs.
        # otherwise it will return zero docs in the next test.
        service.index_layers(with_cache=False)
        time.sleep(2)

        self.api_url = "{0}{1}".format(
            settings.SITE_URL, reverse("search_api", args=[catalog_test_slug])
        )
        self.default_params = {
            "search_engine": SEARCH_TYPE,
            "search_engine_endpoint": self.search_engine_endpoint,
            "q_time": "[* TO *]",
            "q_geo": "[-90,-180 TO 90,180]",
            "d_docs_limit": 0,
            "d_docs_page": 1,
            "d_docs_sort": "score"
        }

    def test_catalogs(self):
        print '> testing catalogs'
        url = settings.SITE_URL + reverse("catalog-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        catalogs = json.loads(res.content)
        self.assertEqual(len(catalogs), Catalog.objects.all().count())

    def test_all_match_docs(self):
        print '> testing match all docs'
        params = self.default_params
        print "searching on [{}]".format(self.api_url)
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], Layer.objects.all().count())

    def test_q_text(self):
        print '> testing q text'
        layer = Layer.objects.all()[0]
        params = self.default_params
        params["q_text"] = "title:\"{0}\"".format(layer.title)
        params["d_docs_limit"] = 100

        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)

        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], 1)

        for doc in results.get("d.docs", []):
            self.assertEqual(doc["title"], layer.title)


    def test_q_geo(self):
        print '> testing q geo'
        params = self.default_params

        # top right square
        params["q_geo"] = "[0,0 TO 30,30]"
        results = self.client.get(self.api_url, params)

        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], 1)

        # bottom left square
        params["q_geo"] = "[-30,-30 TO 0,0]"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], 1)

        # big square
        params["q_geo"] = "[-30,-30 TO 30,30]"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], 4)

        # center where no layers
        params["q_geo"] = "[-5,-5 TO 5,5]"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], 0)

        # bad format
        params["q_geo"] = "[-5,-5 5,5]"
        results = self.client.get(self.api_url, params)
        # validate the format
        print '> testing q geo (format validations)'
        self.assertEqual(results.status_code, 400)


    def test_q_time(self):
        print '> testing q time (format validations)'
        params = self.default_params

        # test validations
        params["q_time"] = "[2000-01-01 - 2001-01-01T00:00:00]"
        results = self.client.get(self.api_url, params)
        # requires [X TO Y]
        self.assertEqual(400, results.status_code)

        print '> testing q time'
        # test asterisks
        # all times
        params["q_time"] = "[* TO *]"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        # all records
        self.assertEqual(results["a.matchDocs"], Layer.objects.all().count())

        # test range
        # entire year 2000
        params["q_time"] = "[2000-01-01 TO 2001-01-01T00:00:00]"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        # 1 in year 2000
        self.assertEqual(results["a.matchDocs"], 1)

        # test complete min and max when q time is asterisks
        params["q_time"] = "[* TO *]"
        params["a_time_limit"] = 1
        if SEARCH_TYPE == SEARCH_TYPE_ES:
            # TODO: a_time_limit is WIP in ES, today requires a a_time_gap to be completed.
            params["a_time_gap"] = "P1Y"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], Layer.objects.all().count())

        if SEARCH_TYPE == SEARCH_TYPE_SOLR:
            # TODO: fix on Solr or ES? see next TODO.
            # * TO * to first date and last date.
            self.assertEqual(results["a.time"]["start"].upper(), "2000-03-01T00:00:00Z")
            self.assertEqual(results["a.time"]["end"].upper(), "2003-03-01T00:00:00Z")
        else:
            # TODO: ES and SOLR returns facets by default spliting the data yearly. first record is on 2000-03,
            # ES facets are returned from 2000-01... to 2003-01.
            # SOLR facets are returned from 2000-03... to 2003-03.
            # SOLR data seems more accurate since first and last Layers are in month 03.
            # Example: http://panchicore.d.pr/12ESP
            # * TO * to first date and last date.
            self.assertEqual(results["a.time"]["start"].upper(), "2000-01-01T00:00:00Z")
            self.assertEqual(results["a.time"]["end"].upper(), "2003-01-01T00:00:00Z")

        # test facets
        params["q_time"] = "[2000 TO 2022]"
        params["a_time_limit"] = 1
        params["a_time_gap"] = "P1Y"
        results = self.client.get(self.api_url, params)
        self.assertEqual(results.status_code, 200)
        results = json.loads(results.content)
        self.assertEqual(results["a.matchDocs"], Layer.objects.all().count())
        # 2000 to complete datetime format
        self.assertEqual(results["a.time"]["start"].upper(), "2000-01-01T00:00:00Z")
        # 2022 to complete datetime format

        if SEARCH_TYPE == SEARCH_TYPE_SOLR:
            # TODO: solr creates entire time span and brings facets with empty entries. (2000 to 2022)
            # fix by removing facets with zero counts?.
            self.assertEqual(results["a.time"]["end"].upper(), "2022-01-01T00:00:00Z")
        else:
            self.assertEqual(results["a.time"]["end"].upper(), "2003-01-01T00:00:00Z")
        # the facet counters are all facets excluding < 2000
        self.assertEqual(len(results["a.time"]["counts"]), Layer.objects.all().count())

    def test_utilities(self):
        print '> testing utilities functions'
        # test_parse_datetime_range
        start, end = utils.parse_datetime_range("[2013-03-01 TO 2014-05-02T23:00:00]")
        self.assertTrue(start.get("is_common_era"))
        self.assertEqual(start.get("parsed_datetime").year, 2013)
        self.assertEqual(start.get("parsed_datetime").month, 3)
        self.assertEqual(start.get("parsed_datetime").day, 1)
        self.assertTrue(end.get("is_common_era"))
        self.assertEqual(end.get("parsed_datetime").year, 2014)
        self.assertEqual(end.get("parsed_datetime").month, 5)
        self.assertEqual(end.get("parsed_datetime").day, 2)
        self.assertEqual(end.get("parsed_datetime").hour, 23)
        self.assertEqual(end.get("parsed_datetime").minute, 0)
        self.assertEqual(end.get("parsed_datetime").second, 0)

        start, end = utils.parse_datetime_range("[-500000000 TO 2014-05-02T23:00:00]")
        self.assertFalse(start.get("is_common_era"))
        self.assertEqual(start.get("parsed_datetime"), "-500000000-01-01T00:00:00Z")

        start, end = utils.parse_datetime_range("[* TO *]")
        self.assertTrue(start.get("is_common_era"))
        self.assertEqual(start.get("parsed_datetime"), None)
        self.assertEqual(end.get("parsed_datetime"), None)

        # test_parse_ISO8601
        quantity, units = utils.parse_ISO8601("P3D")
        self.assertEqual(quantity, 3)
        self.assertEqual(units[0], "DAYS")

        # test_gap_to_sorl
        value = utils.gap_to_sorl("P3D")
        self.assertEqual(value, "+3DAYS")

        # test_parse_geo_box
        value = utils.parse_geo_box("[-90,-180 TO 90,180]")
        self.assertEqual(value.bounds[0], -90)
        self.assertEqual(value.bounds[1], -180)
        self.assertEqual(value.bounds[2], 90)
        self.assertEqual(value.bounds[3], 180)

        # test_request_time_facet
        d = utils.request_time_facet("x", "[2000 TO 2014-01-02T11:12:13]", None, 1000)
        self.assertEqual(type(d), dict)
        self.assertEqual(d['f.x.facet.range.start'], '2000-01-01T00:00:00Z')
        self.assertEqual(d['f.x.facet.range.end'], '2014-01-02T11:12:13Z')
        self.assertEqual(d['f.x.facet.range.gap'], '+6DAYS')
        self.assertEqual(d['facet.range'], 'x')

        d = utils.request_time_facet("y", "[-5000000 TO 2016]", "P1D", 1)
        self.assertEqual(d['f.y.facet.range.start'], '-5000000-01-01T00:00:00Z')
        self.assertEqual(d['f.y.facet.range.end'], '2016-01-01T00:00:00Z')
        self.assertEqual(d['f.y.facet.range.gap'], '+1DAYS')
        self.assertEqual(d['facet.range'], 'y')
