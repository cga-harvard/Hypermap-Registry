from httmock import with_httmock
import pysolr

from django.conf import settings
from django.test import LiveServerTestCase as TestCase

from aggregator.models import Service, Layer
import aggregator.tests.mocks.wms
import aggregator.tests.mocks.warper
import aggregator.tests.mocks.worldmap
from aggregator.tasks import index_all_layers


@with_httmock(aggregator.tests.mocks.wms.resource_get)
def create_wms_service():
    service = Service(
        type='OGC_WMS',
        url='http://wms.example.com/ows?',
    )
    service.save()


@with_httmock(aggregator.tests.mocks.warper.resource_get)
def create_warper_service():
    service = Service(
        type='WARPER',
        url='http://warper.example.com/warper/maps',
    )
    service.save()


@with_httmock(aggregator.tests.mocks.worldmap.resource_get)
def create_wm_service():
    service = Service(
        type='WM',
    )
    service.save()


class SolrTest(TestCase):

    """
    Tests Solr integration.
    For now it is needed to manually create a solr core named 'hypermap_test'.
    Later we will programmatically create it and destroy it after testing.
    """

    @with_httmock(aggregator.tests.mocks.wms.resource_get)
    def setUp(self):
        solr_url = settings.SOLR_URL
        self.solr = pysolr.Solr(solr_url, timeout=60)
        # create a some services (WMS, WARPER, WM)
        # service_wms = Service(
        #     type='OGC_WMS',
        #     url='http://wms.example.com/ows?',
        # )
        # service_wms.save()
        create_wms_service()
        create_warper_service()
        create_wm_service()
        # index all
        index_all_layers()

    def tearDown(self):
        pass

    def test_solr_sync(self):
        nlayers = Layer.objects.all().count()

        results = self.solr.search(q='*:*')
        self.assertEqual(results.hits, nlayers)
