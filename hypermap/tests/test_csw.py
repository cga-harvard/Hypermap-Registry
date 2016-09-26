# -*- coding: utf-8 -*-
import json
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections
from django.db.utils import OperationalError
from django.test import Client, LiveServerTestCase
from lxml.etree import XMLSyntaxError
from owslib.csw import CatalogueServiceWeb
from owslib.fes import BBox, PropertyIsLike
from hypermap.aggregator.models import Catalog, Layer, Service

catalog_test_slug = 'hypermap'


class TestCSW(LiveServerTestCase):
    def setUp(self):
        self.script_name = '/registry/{}/csw'.format(catalog_test_slug)
        self.url = '{}{}'.format(self.live_server_url, self.script_name)
        self.username = 'admin'
        self.password = 'admin'
        self.client = Client()
        user = User.objects.create(username=self.username)
        user.set_password(self.password)
        user.save()
        self.client.login(username=self.username, password=self.password)

        settings.REGISTRY_PYCSW['server']['url'] = self.url

        Catalog.objects.get_or_create(
            name=catalog_test_slug
        )

        Layer.objects.all().delete()
        Service.objects.all().delete()

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
        with open(path, 'rb') as ff:
            payload = ff.read()
        content_type = "application/xml"

        res = self.client.post(self.url, data=payload, content_type=content_type)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Layer.objects.all().count(), 10)

    def test_csw(self):
        # test 2.0.2 Basic Service Profile

        self.csw = CatalogueServiceWeb(self.url, version='2.0.2', username=self.username, password=self.password)
        self.assertEqual(self.csw.version, '2.0.2')

        self.assertIn('2.0.2', self.csw.parameters['version'].values)
        self.assertIn('3.0.0', self.csw.parameters['version'].values)

        for op in self.csw.operations:
            for method in op.methods:
                self.assertEqual(self.csw.url, method['url'])

        self.assertTrue('Transaction' in [o.name for o in self.csw.operations])
        self.assertTrue('Harvest' in [o.name for o in self.csw.operations])

        get_records_op = self.csw.get_operation_by_name('GetRecords')
        self.assertIn('application/json', get_records_op.parameters['outputFormat']['values'])

        # test basic search, no predicates
        self.csw.getrecords2()
        self.assertEqual(Layer.objects.all().count(), self.csw.results['matches'])

        # test csw:AnyText
        anytext = PropertyIsLike('csw:AnyText', 'Brasilia')
        self.csw.getrecords2(constraints=[anytext])
        self.assertEqual(self.csw.results['matches'], 1)

        anytext = PropertyIsLike('csw:AnyText', 'roads')
        self.csw.getrecords2(constraints=[anytext])
        self.assertEqual(self.csw.results['matches'], 4)

        # test ogc:BBOX
        bbox = BBox(['-13', '-80', '15', '-30'])
        self.csw.getrecords2(constraints=[bbox])
        self.assertEqual(self.csw.results['matches'], 2)

        # test csw:AnyText OR ogc:BBOX
        self.csw.getrecords2(constraints=[anytext, bbox])
        self.assertEqual(self.csw.results['matches'], 5)

        # test csw:AnyText && ogc:BBOX
        self.csw.getrecords2(constraints=[[anytext, bbox]])
        self.assertEqual(self.csw.results['matches'], 1)

        # test that ElementSetName=full stores full metadata record as inserted
        self.csw.getrecords2(esn='full')
        self.assertIn('xmlns:registry="http://gis.harvard.edu/HHypermap/registry/0.1"', self.csw.response)

        # test JSON output
        # TODO: fix owslib.csw.CatalogueServiceWeb.getrecords2 to handle non-XML request/response
        with self.assertRaises(XMLSyntaxError):
            self.csw.getrecords2(constraints=[anytext, bbox], format='application/json')

        records_json = json.loads(self.csw.response)
        self.assertEqual(records_json['csw:GetRecordsResponse']['csw:SearchResults']['@numberOfRecordsMatched'], '5')

        # test 3.0.0 OpenSearch
        bsp = {
            'mode': 'opensearch',
            'service': 'CSW',
            'version': '3.0.0',
            'request': 'GetRecords',
            'typenames': 'csw:Record',
            'elementsetname': 'full',
            'outputformat': 'application/json'
        }

        # test basic search, no predicates
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '10')

        # test q
        bsp['q'] = 'Brasilia'
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '1')
        bsp.pop('q')

        # test bbox
        bsp['bbox'] = '-80,-13,-30,15'
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '2')
        bsp.pop('bbox')

        # test time
        bsp['time'] = '2014-09-23T12:04:31.102243+00:00/'
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '10')
        bsp.pop('time')

        # test q and bbox
        bsp['q'] = 'roads'
        bsp['bbox'] = '-80,-13,-30,15'
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '1')

        # test q and bbox and time
        bsp['time'] = '2014-09-23T12:04:31.102243+00:00/'
        res = json.loads(self.client.get(self.script_name, bsp).content)
        self.assertEqual(res['atom:feed']['os:totalResults'], '1')

    @classmethod
    def tearDownClass(cls):
        # Workaround for https://code.djangoproject.com/ticket/22414
        # Persistent connections not closed by LiveServerTestCase, preventing dropping test databases
        # https://github.com/cjerdonek/django/commit/b07fbca02688a0f8eb159f0dde132e7498aa40cc
        def close_sessions(conn):
            database_name = conn.settings_dict['NAME']
            close_sessions_query = """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '%s';
            """ % database_name
            with conn.cursor() as cursor:
                try:
                    cursor.execute(close_sessions_query)
                except OperationalError:
                    # We get kicked out after closing.
                    pass

        for alias in connections:
            connections[alias].close()
            close_sessions(connections[alias])

        print('TEST', settings.CONN_MAX_AGE)
        print "Forcefully closed database connections."
