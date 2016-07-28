import requests
from django.test import TestCase

from hypermap.search_api import utils


class SearchApiTestCase(TestCase):
    # TODO: create tests based in local solr endpoint.

    def setUp(self):
        self.search_engine_endpoint = "http://54.221.223.91:8983/solr/hypermap/select"
        self.search_engine = "solr"
        self.test_url = "http://localhost:8000/registry/api/search/"

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

    def test_time_order(self):
        pass

    def test_time_facets(self):
        pass

    def test_time_facets_compute_gap(self):
        pass

    def test_utils_time_parse(self):
        dt = utils.parse_datetime("2013")
        self.assertEquals(dt.year, 2013)

    def test_parse_datetime_range(self):
        range = utils.parse_datetime_range("[2013-03-01 TO 2014-05-01T23:00:00]")
        self.assertEquals(len(range), 2)
        self.assertEquals(range[0].year, 2013)
        self.assertEquals(range[0].month, 3)
        self.assertEquals(range[0].day, 1)
        self.assertEquals(range[1].hour, 23)

        range = utils.parse_datetime_range("[* TO *]")
        self.assertIsNone(range[0])
        self.assertIsNone(range[1])

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
