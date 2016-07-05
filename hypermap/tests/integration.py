from httmock import with_httmock
import pysolr
import time

from django.conf import settings
from django.test import LiveServerTestCase as TestCase

from owslib.csw import CatalogueServiceWeb

from hypermap.aggregator.models import Service, Layer
import hypermap.aggregator.tests.mocks.wms
import hypermap.aggregator.tests.mocks.warper
import hypermap.aggregator.tests.mocks.worldmap
from hypermap.aggregator.tasks import index_all_layers


@with_httmock(hypermap.aggregator.tests.mocks.wms.resource_get)
def create_wms_service():
    service = Service(
        type='OGC:WMS',
        url='http://wms.example.com/ows?',
    )
    service.save()


@with_httmock(hypermap.aggregator.tests.mocks.warper.resource_get)
def create_warper_service():
    service = Service(
        type='Hypermap:WARPER',
        url='http://warper.example.com/warper/maps',
    )
    service.save()


@with_httmock(hypermap.aggregator.tests.mocks.worldmap.resource_get)
def create_wm_service():
    service = Service(
        type='Hypermap:WorldMap',
    )
    service.save()


class SolrTest(TestCase):

    """
    Tests Solr integration.
    For now it is needed to manually create a solr core named 'hypermap_test'.
    Later we will programmatically create it and destroy it after testing.
    """

    @with_httmock(hypermap.aggregator.tests.mocks.wms.resource_get)
    def setUp(self):
        solr_url = settings.SEARCH_URL
        self.solr = pysolr.Solr(solr_url, timeout=60)
        create_wms_service()
        create_warper_service()
        create_wm_service()
        # index all
        index_all_layers()
        # some time sleep to commit docs
        time.sleep(10)

    def tearDown(self):
        pass

    def test_solr_sync(self):
        nlayers = Layer.objects.all().count()
        # layers indexed in solr must be same number in django db
        results = self.solr.search(q='*:*')
        self.assertEqual(results.hits, nlayers)
        # layers with invalid bbox don't have the bbox attribute in solr
        nlayers_valid_coordinates = sum(layer.has_valid_bbox() for layer in Layer.objects.all())
        results = self.solr.search(q='bbox:*')
        self.assertEqual(results.hits, nlayers_valid_coordinates)


class CSWTest(TestCase):
    """
    Test CSW endpoint
    """

    def setUp(self):
        """setup records and CSW"""

        self.csw = CatalogueServiceWeb(settings.REGISTRY_PYCSW['server']['url'])

    def tearDown(self):
        """shutdown endpoint and clean out records"""

        Service.objects.all().delete()

    def test_capabilities(self):
        """verify that HHypermap's CSW works properly"""

        # test that OGC:CSW URLs are identical to what is defined in settings
        for op in self.csw.operations:
            for method in op.methods:
                self.assertEqual(settings.REGISTRY_PYCSW['server']['url'], method['url'], 'Expected URL equality')

        # test that OGC:CSW 2.0.2 is supported
        self.assertEqual(self.csw.version, '2.0.2', 'Expected "2.0.2" as a supported version')

        # test that transactions are supported
        transaction = self.csw.get_operation_by_name('Transaction')
        harvest = self.csw.get_operation_by_name('Harvest')

        # test that HHypermap Service types are Harvestable
        for restype in ['http://www.opengis.net/wms', 'http://www.opengis.net/wmts/1.0',
                        'urn:x-esri:serviceType:ArcGIS:MapServer', 'urn:x-esri:serviceType:ArcGIS:ImageServer']:
            self.assertIn(restype, harvest.parameters['ResourceType']['values'])
            self.assertIn(restype, transaction.parameters['TransactionSchemas']['values'])
