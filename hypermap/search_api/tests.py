import requests
from django.test import TestCase

from hypermap.search_api import utils


class SearchApiTestCase(TestCase):
    # TODO: create tests based in local solr endpoint.

    def setUp(self):
        self.search_engine_endpoint = "http://54.221.223.91:8983/solr/hypermap/select"
        self.search_engine = "solr"
        self.test_url = "http://localhost:8000/registry/api/search/hypermap"

        # TODO: delete solr documents
        # TODO: add test solr documents

    def test_q_text(self):
        params = {
            "search_engine_endpoint": self.search_engine_endpoint,
            "search_engine": self.search_engine,
            "q_text": "a"
        }
        res = requests.get(self.test_url, params=params)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data.get("a.matchDocs", 0), 0)

    def test_q_geo(self):
        params = {
            "search_engine_endpoint": self.search_engine_endpoint,
            "search_engine": self.search_engine,
            "q_geo": "[-90,-180 TO 90,180]"
        }
        res = requests.get(self.test_url, params=params)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data.get("a.matchDocs", 0), 0)

    def test_parse_datetime_range(self):
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


    def test_parse_ISO8601(self):
        quantity, units = utils.parse_ISO8601("P3D")
        self.assertEqual(quantity, 3)
        self.assertEqual(units[0], "DAYS")

    def test_gap_to_sorl(self):
        value = utils.gap_to_sorl("P3D")
        self.assertEqual(value, "+3DAYS")

    def test_parse_geo_box(self):
        value = utils.parse_geo_box("[-90,-180 TO 90,180]")
        self.assertEqual(value.bounds[0], -90)
        self.assertEqual(value.bounds[1], -180)
        self.assertEqual(value.bounds[2], 90)
        self.assertEqual(value.bounds[3], 180)

    def test_request_time_facet(self):
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

    def asterisk_to_min_max(self):
        # TODO: make mock
        pass
