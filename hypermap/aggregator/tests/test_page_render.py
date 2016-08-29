from django.test import TestCase
from django.core.urlresolvers import reverse

from django.db.models import signals

from hypermap.aggregator.models import Service, Layer, Catalog
from hypermap.aggregator.models import layer_post_save, service_post_save


SERVICE_NUMBER = 2
LAYER_PER_SERVICE_NUMBER = 2
TIMES_TO_CHECK = 1


class PageRendererTestCase(TestCase):

    def setUp(self):

        signals.post_save.disconnect(layer_post_save, sender=Layer)
        signals.post_save.disconnect(service_post_save, sender=Service)

        catalog, created = Catalog.objects.get_or_create(
            name="hypermap", slug="hypermap",
            url="search_api"
        )

        for s in range(0, SERVICE_NUMBER):
            service = Service(
                url='http://%s.fakeurl.com' % s,
                title='Title %s' % s,
                type='OGC:WMS',
                catalog=catalog
            )
            service.save()
            for l in range(0, LAYER_PER_SERVICE_NUMBER):
                layer = Layer(
                    name='Layer %s, from service %s' % (l, s),
                    bbox_x0=-179,
                    bbox_x1=179,
                    bbox_y0=-89,
                    bbox_y1=89,
                    service=service,
                    catalog=service.catalog
                )
                layer.save()
                service.layer_set.add(layer)
        for c in range(0, TIMES_TO_CHECK):
            for s in range(0, SERVICE_NUMBER):
                service = Service.objects.all()[s]
                service.check_available()
                for layer in service.layer_set.all():
                    layer.check_available()

    def tearDown(self):
        signals.post_save.connect(layer_post_save, sender=Layer)
        signals.post_save.connect(service_post_save, sender=Service)

    def test_pages_render(self):
        """
        Verify pages that do and do not require login and corresponding status
        codes
        """

        # anonymous can go to index page
        response = self.client.get(reverse('index'))
        self.assertEqual(200, response.status_code)

        # anonymous going to service_detail is authorized
        service = Service.objects.all()[0]
        response = self.client.get(
            reverse('service_detail', args=(service.catalog.slug, str(service.id),)))
        self.assertEqual(200, response.status_code)

        # anonymous going to layer_detail is authorized
        layer = Layer.objects.all()[0]
        response = self.client.get(
            reverse('layer_detail', args=(layer.catalog.slug, str(layer.id),)))
        self.assertEqual(200, response.status_code)
